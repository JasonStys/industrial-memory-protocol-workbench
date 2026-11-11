"""@file publication_text.py
@brief Jason Stys: inspect only named reviewed Office editions without hiding their XML.

Symbols: docs/generated/symbol-index.md.
Unknown binary files retain strict UTF-8 failure. No Office content is executed.
"""

import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

EDITION_ROOTS = {
    "docs/reports/windows-application-guide-1.1.0.docx": "word/document.xml",
    "docs/reports/project-guide.docx": "word/document.xml",
    "docs/reports/validation-review.docx": "word/document.xml",
    "docs/reports/validation-evidence.xlsx": "xl/workbook.xml",
}
MAX_PACKAGE_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_MEMBERS = 256


def public_text(path: Path, root: Path) -> str:
    """Read source UTF-8 or bounded XML from an exact named, macro-free Office path."""
    relative = path.relative_to(root).as_posix()
    if relative not in EDITION_ROOTS:
        return path.read_text(encoding="utf-8")
    try:
        with path.open("rb") as source:
            if os.fstat(source.fileno()).st_size > MAX_PACKAGE_BYTES:
                raise ValueError("Reviewed Office package exceeds its byte budget")
            with ZipFile(source) as package:
                members = package.infolist()
                names = [member.filename for member in members]
                if not members or len(members) > MAX_MEMBERS or len(names) != len(set(names)):
                    raise ValueError("Reviewed Office member count or identity is invalid")
                if EDITION_ROOTS[relative] not in names or "[Content_Types].xml" not in names:
                    raise ValueError("Reviewed Office document root is missing")
                if sum(member.file_size for member in members) > MAX_EXPANDED_BYTES:
                    raise ValueError("Reviewed Office expanded size exceeds its budget")
                result = []
                for member in members:
                    if (
                        member.file_size > MAX_MEMBER_BYTES
                        or member.flag_bits & 1
                        or member.compress_type not in {ZIP_STORED, ZIP_DEFLATED}
                        or "vbaproject" in member.filename.lower()
                        or "/embeddings/" in member.filename.lower()
                    ):
                        raise ValueError("Unsupported reviewed Office member")
                    if member.filename.endswith((".xml", ".rels")):
                        with package.open(member) as stream:
                            payload = stream.read(MAX_MEMBER_BYTES + 1)
                        if len(payload) > MAX_MEMBER_BYTES or len(payload) != member.file_size:
                            raise ValueError("Reviewed Office XML exceeds its declared budget")
                        result.append(payload.decode("utf-8", errors="strict"))
                return "\n".join(result)
    except BadZipFile as error:
        raise ValueError("Invalid reviewed Office package") from error
