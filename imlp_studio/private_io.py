"""@file private_io.py
@brief Read actual ordinary application resources with descriptor-bound byte limits.
@details No arbitrary user path enters this reader. Source/resource identities remain separate
from OS-owner access controls. Symbols: docs/generated/symbol-index.md.
"""

import os
import stat
from pathlib import Path


def bounded(path: Path, limit: int) -> bytes:
    """Check/read the same nonblocking ordinary descriptor, including changed-size refusal."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or not 0 <= before.st_size <= limit
        ):
            raise ValueError("Application resource is not a bounded single-link ordinary file")
        remaining = min(before.st_size + 1, limit + 1)
        blocks = []
        while remaining:
            part = os.read(descriptor, min(remaining, 64 * 1024))
            if not part:
                break
            blocks.append(part)
            remaining -= len(part)
        raw = b"".join(blocks)
        after = os.fstat(descriptor)
        if (
            len(raw) != before.st_size
            or after.st_size != before.st_size
            or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise ValueError("Application resource changed while reading")
        return raw
    finally:
        os.close(descriptor)
