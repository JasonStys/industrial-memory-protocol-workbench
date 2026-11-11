"""@file resources.py
@brief Binds native application resources to one product/version/source before private writes.

load_resources preloads a closed set of static assets and validates the actual C++ identity.
Variables are fixed paths/media types and packaged byte budgets. See docs/generated/symbol-index.md.
"""

import hashlib
import json
import platform
import re
import sys
from pathlib import Path

from imlp_studio import __version__
from imlp_studio.engine import Engine
from imlp_studio.private_io import bounded

ASSETS = {
    "index.html": "text/html; charset=utf-8",
    "assets/app.js": "text/javascript; charset=utf-8",
    "assets/model.js": "text/javascript; charset=utf-8",
    "assets/styles.css": "text/css; charset=utf-8",
}


def load_resources() -> tuple[Engine, dict[str, tuple[str, bytes]], dict]:
    "Frozen apps require exact metadata; source development never masquerades as a packaged source."
    root = Path(__file__).resolve().parent.parent
    frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        if sys.version_info[:3] < (3, 14, 10):
            raise ValueError("This native application requires patched Python 3.14.10 or later")
        metadata = json.loads(bounded(root / "RELEASE.json", 16 * 1024))
        if (
            metadata.get("product") != "industrial-memory-protocol-workbench"
            or metadata.get("version") != __version__
            or metadata.get("pythonVersion") != platform.python_version()
            or not isinstance(metadata.get("sourceCommit"), str)
            or re.fullmatch(r"[a-f0-9]{40}", metadata["sourceCommit"]) is None
            or not isinstance(metadata.get("assets"), dict)
            or set(metadata["assets"]) != set(ASSETS)
        ):
            raise ValueError("Native product/version/source/static inventory does not match")
        executable = (
            root / "engine" / ("imlp-studio.exe" if sys.platform == "win32" else "imlp-studio")
        )
        expected = metadata["engineSha256"]
        web = root / "web"
    else:
        executable = root / ".runtime/cpp-app"
        executable = (
            executable / "Release/imlp-studio.exe"
            if sys.platform == "win32"
            else executable / "imlp-studio"
        )
        expected = hashlib.sha256(bounded(executable, 32 * 1024 * 1024)).hexdigest()
        metadata = {
            "product": "industrial-memory-protocol-workbench",
            "version": __version__,
            "sourceCommit": "development",
        }
        web = root / "web" / "dist"
    engine = Engine(executable, metadata["sourceCommit"], expected)
    assets = {}
    for name, content_type in ASSETS.items():
        raw = bounded(web / name, 2 * 1024 * 1024)
        if frozen and hashlib.sha256(raw).hexdigest() != metadata["assets"][name]:
            raise ValueError("Native UI resource digest mismatch")
        assets["/" + name] = content_type, raw
    assets["/"] = assets["/index.html"]
    return engine, assets, metadata
