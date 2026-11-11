"""@file conftest.py
@brief Actual C++/SQLite/loopback fixtures with isolated workspaces by Jason Stys.
@details Standalone CTest CLI contracts remain executed by CMake, not pytest argv collection.
"""

import hashlib
import sys
from pathlib import Path

import httpx
import pytest

from imlp_studio.engine import Engine
from imlp_studio.server import Host
from imlp_studio.store import Profile

collect_ignore = ["test_studio_cli.py", "test_stream_cli.py", "runtime_notice_cases.py"]
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine():
    path = ROOT / ".runtime/cpp-app"
    path = path / ("Release/imlp-studio.exe" if sys.platform == "win32" else "imlp-studio")
    return Engine(path, "development", hashlib.sha256(path.read_bytes()).hexdigest())


@pytest.fixture
def live(tmp_path, engine):
    profile = Profile(tmp_path / "workspace")
    host = Host(profile, engine, {"/": ("text/html", b"<h1>Inert local asset</h1>")})
    host.start()
    try:
        with httpx.Client(
            base_url=host.origin,
            trust_env=False,
            timeout=20,
            headers={"X-IMLP-Capability": host.capability, "Origin": host.origin},
        ) as client:
            yield host, client
    finally:
        host.close()
