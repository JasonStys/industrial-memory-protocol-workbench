"""@file test_repository_policy.py
@brief Real Git/publication/index regressions preserve original public gates by Jason Stys.
@details Ignored private data and proposed public source are different boundaries, not broad skips.
"""

import ast
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from scripts import check_repository as policy
from scripts import generate_symbol_index as index
from scripts.publication_text import public_text


def test_real_git_tracked_and_proposed_scope_preserves_ignored_private_boundary(
    tmp_path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    (root / ".gitignore").write_text(".runtime/\n", encoding="utf-8")
    (root / "original.cpp").write_text("// @file original.cpp\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    (root / ".runtime").mkdir()
    private = root / ".runtime/private.py"
    private.write_text("not public\n", encoding="utf-8")
    proposed = root / "new.ts"
    proposed.write_text("/** @file new.ts */\n", encoding="utf-8")
    assert [p.relative_to(root).as_posix() for p in policy.discover_files(root)] == [
        ".gitignore",
        "new.ts",
        "original.cpp",
    ]
    subprocess.run(["git", "-C", str(root), "add", "-f", str(private)], check=True)
    assert private in policy.discover_files(root)
    assert policy.is_code_file(proposed)
    for suffix in ["py", "ts", "mjs", "css", "html"]:
        assert policy.is_code_file(root / ("authored." + suffix))
    monkeypatch.setattr(policy, "REPOSITORY_ROOT", root)
    monkeypatch.setattr(policy, "REQUIRED_DOCS", set())
    proposed.write_text("const missingHeader = 1;\n", encoding="utf-8")
    private.write_text('"""@file private.py\n' + "op" + "to 22" + '\n"""\n', encoding="utf-8")
    failures, summary = policy.validate()
    assert "missing source header: new.ts" in failures
    assert "protected employer reference found: .runtime/private.py" in failures
    assert summary["status"] == "failed"


def test_ast_and_lexical_declarations_bind_actual_one_based_lines():
    source = '"""Fixture."""\nclass Owner:\n    def open(self, value):\n        state = value\n'
    assert index.python_symbols(source) == [
        ("class: Owner", 2),
        ("function: open", 3),
        ("parameter: self", 3),
        ("parameter: value", 3),
        ("variable: state", 4),
    ]
    assert index.browser_symbols(
        "/** Fixture. */\nconst bound = 4;\nexport function run() {}\n"
    ) == [("const: bound", 2), ("function: run", 3)]
    assert index.symbols_for("class Client {};\nIMLP_TEST(expected_wire) {}\n") == [
        ("Client", 1),
        ("expected_wire", 2),
    ]


def test_old_grammar_refuses_before_index_can_be_generated(monkeypatch):
    def unsupported(*args, **kwargs):
        raise SyntaxError("Actual old interpreter grammar fixture")

    monkeypatch.setattr(ast, "parse", unsupported)
    with pytest.raises(ValueError, match="Python3.14"):
        index.require_current_parser()


@pytest.mark.parametrize("member", ["word/vbaProject.bin", "word/embeddings/oleObject1.bin"])
def test_actual_office_macro_or_embedded_object_is_refused(tmp_path, member):
    path = tmp_path / "docs/reports/project-guide.docx"
    path.parent.mkdir(parents=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document>public</document>")
        archive.writestr(member, b"inert unsupported member")
    with pytest.raises(ValueError, match="Unsupported"):
        public_text(path, tmp_path)


def test_original_main_comparable_cpp_codeql_configuration_is_retained():
    """Lexical identity regression; actionlint separately parses real workflow semantics."""
    source = (policy.REPOSITORY_ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
    original, added = source.split("\n  analyze:\n", 1)[1].split("\n  applications:\n", 1)
    for field in ("strategy:", "matrix:", "environment:", "category:"):
        assert field not in original
    for field in (
        "languages: c-cpp",
        "build-mode: manual",
        "queries: security-extended",
        "upload-database: false",
        "wait-for-processing: true",
        "cmake --build",
    ):
        assert field in original
    assert "language: [python, javascript-typescript, actions]" in added
    assert "build-mode: none" in added and "queries: security-extended" in added
    assert "continue-on-error" not in source and "paths-ignore" not in source
    quality = (policy.REPOSITORY_ROOT / ".github/workflows/native.yml").read_text(encoding="utf-8")
    compound = quality.split("- name: Source style and exact symbol locations\n", 1)[1].split(
        "      - run:", 1
    )[0]
    assert "shell: bash" in compound and "set -euo pipefail" in compound
    original_ci = (policy.REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for block in original_ci.split("- name: Check repository policy\n")[1:]:
        gate = block.split("      - name:", 1)[0]
        assert "shell: bash" in gate and "set -euo pipefail" in gate
