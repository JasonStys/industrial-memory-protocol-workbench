"""@file test_publication_text.py
@brief Jason Stys: actual Office ZIP fixtures retain text scanning and reject unknown content.

Symbols: docs/generated/symbol-index.md.
These tests verify documentation input handling, not application-runtime behavior.
"""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from scripts.publication_text import MAX_MEMBER_BYTES, public_text


def edition(root: Path, name: str, main: str, text: bytes = b"<document>public</document>") -> Path:
    """Create an isolated actual ZIP containing declared XML and a relationship."""
    path = root / "docs" / "reports" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", b"<Types/>")
        package.writestr(main, text)
        package.writestr("_rels/.rels", b"<Relationship>review-secret-marker</Relationship>")
    return path


@pytest.mark.parametrize(
    "name,main",
    [
        ("project-guide.docx", "word/document.xml"),
        ("validation-review.docx", "word/document.xml"),
        ("validation-evidence.xlsx", "xl/workbook.xml"),
    ],
)
def test_named_office_xml_remains_visible(tmp_path: Path, name: str, main: str) -> None:
    """Every allowed edition exposes main text and relationships to existing scans."""
    text = public_text(edition(tmp_path, name, main), tmp_path)
    assert "public" in text and "review-secret-marker" in text


def test_unknown_binary_is_not_an_exclusion(tmp_path: Path) -> None:
    """A different Office filename still receives strict ordinary UTF-8 handling."""
    path = edition(tmp_path, "unknown.docx", "word/document.xml")
    with pytest.raises(UnicodeDecodeError):
        public_text(path, tmp_path)


def test_missing_document_root_is_rejected(tmp_path: Path) -> None:
    """A workbook renamed as Word cannot pass the declared edition contract."""
    with pytest.raises(ValueError, match="root is missing"):
        public_text(edition(tmp_path, "project-guide.docx", "xl/workbook.xml"), tmp_path)


def test_invalid_zip_is_rejected(tmp_path: Path) -> None:
    """The exact allowed filename does not make arbitrary bytes acceptable."""
    path = tmp_path / "docs/reports/project-guide.docx"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not an Office ZIP")
    with pytest.raises(ValueError, match="Invalid reviewed"):
        public_text(path, tmp_path)


def test_invalid_utf8_xml_is_rejected(tmp_path: Path) -> None:
    """Text decoding errors cannot be hidden by replacement characters."""
    with pytest.raises(UnicodeDecodeError):
        public_text(
            edition(tmp_path, "project-guide.docx", "word/document.xml", b"\xff"),
            tmp_path,
        )


def test_expansion_budget_is_active(tmp_path: Path) -> None:
    """A genuinely compressed oversized XML member is refused before expansion."""
    path = edition(
        tmp_path,
        "project-guide.docx",
        "word/document.xml",
        b"x" * (MAX_MEMBER_BYTES + 1),
    )
    with pytest.raises(ValueError, match="Unsupported reviewed"):
        public_text(path, tmp_path)
