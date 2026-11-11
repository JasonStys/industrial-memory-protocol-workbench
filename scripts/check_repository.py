"""
@file check_repository.py
@brief Enforces public boundaries, source headers, required docs and immutable action pins.
@details Function and variable locations are indexed in docs/generated/symbol-index.md.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

if __package__:
    from .publication_text import public_text
else:
    from publication_text import public_text

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CODE_EXTENSIONS = {".cpp", ".hpp", ".py", ".sh", ".ts", ".mjs", ".js", ".css", ".html"}
REQUIRED_DOCS = {
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/architecture.md",
    "docs/big-o.md",
    "docs/cli.md",
    "docs/fault-catalog.md",
    "docs/protocol-spec.md",
    "docs/safety-and-security.md",
    "docs/testing.md",
    "docs/limitations.md",
    "docs/sources.md",
    "docs/generated/symbol-index.md",
    "docs/reports/validation-report.md",
}
PROTECTED_REFERENCE = "".join(("op", "to", " 22"))
ACTION_PATTERN = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
CODEQL_PATTERN = re.compile(r"uses:\s*github/codeql-action/(?:init|analyze|autobuild)@([^\s#]+)")


def consistent_codeql_versions(source: str) -> bool:
    """Require all coordinated CodeQL steps to use one immutable commit."""
    versions = CODEQL_PATTERN.findall(source)
    return len(set(versions)) <= 1 and all(FULL_SHA_PATTERN.fullmatch(v) for v in versions)


def discover_files(root: Path = REPOSITORY_ROOT) -> list[Path]:
    """Check tracked plus proposed public files, including force-tracked ignored paths."""
    result = subprocess.run(
        [
            "git",
            "-c",
            "safe.directory=" + root.as_posix(),
            "-C",
            str(root),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        check=True,
        capture_output=True,
    )
    discovered = []
    for name in sorted(set(result.stdout.decode("utf-8").split("\0")) - {""}):
        relative = Path(name)
        if relative.is_absolute() or any(part in {"..", ".git"} for part in relative.parts):
            raise ValueError("Invalid deliverable path")
        path = root / relative
        if path.is_symlink() or path.is_junction() or not path.is_file():
            raise ValueError("Deliverable is not an ordinary file: " + name)
        discovered.append(path)
    return discovered


def is_code_file(path: Path) -> bool:
    """Identify human-maintained implementation and script files that require headers."""
    return path.suffix in CODE_EXTENSIONS or path.name == "CMakeLists.txt"


def validate() -> tuple[list[str], dict[str, object]]:
    """Run stable policy checks and return failures plus a machine-readable summary."""
    failures: list[str] = []
    files = discover_files(REPOSITORY_ROOT)
    relative_files = {path.relative_to(REPOSITORY_ROOT).as_posix() for path in files}

    for required in sorted(REQUIRED_DOCS):
        if required not in relative_files:
            failures.append(f"missing required documentation: {required}")

    source_files = 0
    markdown_files = 0
    workflow_files = 0
    for path in files:
        relative = path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.suffix == ".md":
            markdown_files += 1
        text = public_text(path, REPOSITORY_ROOT)
        if PROTECTED_REFERENCE in text.casefold():
            failures.append(f"protected employer reference found: {relative}")
        if is_code_file(path):
            source_files += 1
            if "@file" not in "\n".join(text.splitlines()[:8]):
                failures.append(f"missing source header: {relative}")
        if relative.startswith(".github/workflows/") and path.suffix in {".yml", ".yaml"}:
            workflow_files += 1
            if not consistent_codeql_versions(text):
                failures.append(f"CodeQL steps have inconsistent or mutable versions: {relative}")
            for reference in ACTION_PATTERN.findall(text):
                if not FULL_SHA_PATTERN.fullmatch(reference):
                    failures.append(
                        f"action is not pinned to a full SHA in {relative}: {reference}"
                    )

    summary: dict[str, object] = {
        "status": "passed" if not failures else "failed",
        "files_checked": len(files),
        "source_files_with_required_headers": source_files,
        "markdown_files": markdown_files,
        "workflow_files_with_immutable_action_pins": workflow_files,
        "required_documentation_files": len(REQUIRED_DOCS),
        "failures": failures,
    }
    return failures, summary


def main() -> int:
    """Write the JSON report and return a CI-compatible exit status."""
    failures, summary = validate()
    output = REPOSITORY_ROOT / "reports" / "repository-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print(
        "Repository policy passed: "
        f"{summary['files_checked']} files, "
        f"{summary['source_files_with_required_headers']} source headers, "
        f"{summary['required_documentation_files']} required docs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
