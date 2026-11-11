"""@file test_native_resources.py
@brief Exact frozen identity/static-resource and actual growth refusals by Jason Stys.
@details Metadata fixtures isolate admission; the full package consumer separately runs real bytes.
"""

import hashlib
import json
import os
import sys

import pytest

from imlp_studio import resources
from imlp_studio.private_io import bounded


def test_actual_same_inode_growth_is_refused_on_the_opened_resource(tmp_path, monkeypatch):
    path = tmp_path / "growing-resource"
    path.write_bytes(b"abcd")
    writer = os.open(path, os.O_WRONLY | os.O_APPEND | getattr(os, "O_BINARY", 0))
    original_read = os.read
    grown = False

    def grow(descriptor, count):
        nonlocal grown
        if not grown:
            os.write(writer, b"x")
            grown = True
        return original_read(descriptor, count)

    try:
        monkeypatch.setattr(os, "read", grow)
        with pytest.raises(ValueError, match="changed"):
            bounded(path, 4)
    finally:
        os.close(writer)


def packaged_context(tmp_path, monkeypatch, engine):
    root = tmp_path / "native"
    (root / "imlp_studio").mkdir(parents=True)
    monkeypatch.setattr(resources, "__file__", str(root / "imlp_studio/resources.py"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(resources, "Engine", lambda *args: engine)
    metadata = {
        "product": "industrial-memory-protocol-workbench",
        "version": "1.1.0",
        "sourceCommit": "a" * 40,
        "pythonVersion": resources.platform.python_version(),
        "engineSha256": engine.identity["sha256"],
        "assets": {},
    }
    for name in resources.ASSETS:
        path = root / "web" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = ("Independent static fixture " + name).encode()
        path.write_bytes(raw)
        metadata["assets"][name] = hashlib.sha256(raw).hexdigest()
    return root, metadata


@pytest.mark.parametrize(
    "field,value",
    [
        ("product", "other"),
        ("version", "1.0.0"),
        ("sourceCommit", "a" * 39),
        ("sourceCommit", None),
        ("pythonVersion", "3.14.6"),
        ("assets", {}),
    ],
)
def test_frozen_product_source_and_inventory_refused_before_any_profile(
    tmp_path, monkeypatch, engine, field, value
):
    root, metadata = packaged_context(tmp_path, monkeypatch, engine)
    metadata[field] = value
    (root / "RELEASE.json").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        resources.load_resources()
    assert not (tmp_path / "profile").exists()


def test_frozen_asset_digest_and_patch_floor_cannot_be_waived(tmp_path, monkeypatch, engine):
    root, metadata = packaged_context(tmp_path, monkeypatch, engine)
    (root / "RELEASE.json").write_text(json.dumps(metadata), encoding="utf-8")
    assert resources.load_resources()[2] == metadata
    (root / "web/assets/app.js").write_bytes(b"changed inert bytes")
    with pytest.raises(ValueError, match="digest"):
        resources.load_resources()
    monkeypatch.setattr(sys, "version_info", (3, 14, 6))
    with pytest.raises(ValueError, match="patched Python"):
        resources.load_resources()
