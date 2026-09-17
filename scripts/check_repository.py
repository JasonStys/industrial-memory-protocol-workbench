"""
@file check_repository.py
@brief Enforces public-repository boundaries, source headers, required docs, and immutable action pins.
@details Function and variable locations are indexed in docs/generated/symbol-index.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIRECTORIES = {".git", ".cache", ".idea", ".vscode", "build", "out"}
CODE_EXTENSIONS = {".cpp", ".hpp", ".py", ".sh"}
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


def discover_files() -> list[Path]:
    """Return repository files while excluding generated build and VCS directories."""
    discovered: list[Path] = []
    for path in REPOSITORY_ROOT.rglob("*"):
        relative = path.relative_to(REPOSITORY_ROOT)
        if any(part in SKIPPED_DIRECTORIES or part.startswith("build-") for part in relative.parts):
            continue
        if path.is_file():
            discovered.append(path)
    return sorted(discovered)


def is_code_file(path: Path) -> bool:
    """Identify human-maintained implementation and script files that require headers."""
    return path.suffix in CODE_EXTENSIONS or path.name == "CMakeLists.txt"


def validate() -> tuple[list[str], dict[str, object]]:
    """Run stable policy checks and return failures plus a machine-readable summary."""
    failures: list[str] = []
    files = discover_files()
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
        text = path.read_text(encoding="utf-8", errors="replace")
        if PROTECTED_REFERENCE in text.casefold():
            failures.append(f"protected employer reference found: {relative}")
        if is_code_file(path):
            source_files += 1
            if "@file" not in "\n".join(text.splitlines()[:8]):
                failures.append(f"missing source header: {relative}")
        if relative.startswith(".github/workflows/") and path.suffix in {".yml", ".yaml"}:
            workflow_files += 1
            for reference in ACTION_PATTERN.findall(text):
                if not FULL_SHA_PATTERN.fullmatch(reference):
                    failures.append(f"action is not pinned to a full SHA in {relative}: {reference}")

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
        f"{summary['files_checked']} files, {summary['source_files_with_required_headers']} source headers, "
        f"{summary['required_documentation_files']} required docs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

