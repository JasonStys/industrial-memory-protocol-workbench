"""@file test_native_packaging.py
@brief Independent version/source/dirty-policy contracts without freezing code by Jason Stys.
@details Full extracted native acceptance is a separate mandatory workflow, not mocked here.
"""

import json
from pathlib import Path

import pytest

from tools import package_app


def configuration_tree(root: Path):
    (root / "imlp_studio").mkdir(parents=True)
    (root / "web/public").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname="industrial-memory-protocol-workbench"\nversion="1.1.0"\n',
        encoding="utf-8",
    )
    (root / "CMakeLists.txt").write_text("project(imlp VERSION 1.1.0)", encoding="utf-8")
    (root / "imlp_studio/__init__.py").write_text('__version__ = "1.1.0"\n', encoding="utf-8")
    (root / "web/package.json").write_text(json.dumps({"version": "1.1.0"}), encoding="utf-8")
    (root / "web/package-lock.json").write_text(
        json.dumps({"version": "1.1.0", "packages": {"": {"version": "1.1.0"}}}), encoding="utf-8"
    )
    (root / "web/public/index.html").write_text("Version 1.1.0", encoding="utf-8")


@pytest.mark.parametrize(
    "surface",
    [
        "CMakeLists.txt",
        "imlp_studio/__init__.py",
        "web/package.json",
        "web/package-lock.json",
        "web/public/index.html",
    ],
)
def test_any_version_surface_drift_refuses_packaging(tmp_path, surface):
    configuration_tree(tmp_path)
    assert package_app.configuration(tmp_path) == "1.1.0"
    path = tmp_path / surface
    path.write_text(path.read_text(encoding="utf-8").replace("1.1.0", "1.0.0"), encoding="utf-8")
    with pytest.raises(ValueError):
        package_app.configuration(tmp_path)


def test_dirty_override_is_never_accepted_in_ci(monkeypatch):
    def git(arguments, **kwargs):
        return "a" * 40 + "\n" if "rev-parse" in arguments else " M authored.py\n"

    monkeypatch.setattr(package_app.subprocess, "check_output", git)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(ValueError, match="Clean source"):
        package_app.source_metadata("1.1.0")
    assert package_app.source_metadata("1.1.0", True)["sourceDirty"]
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(ValueError, match="forbidden"):
        package_app.source_metadata("1.1.0", True)


def test_exact_clean_ci_checkout_binding_and_full_source_are_required(monkeypatch):
    def git(arguments, **kwargs):
        return "a" * 40 + "\n" if "rev-parse" in arguments else ""

    monkeypatch.setattr(package_app.subprocess, "check_output", git)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    with pytest.raises(ValueError, match="mismatch"):
        package_app.source_metadata("1.1.0")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    assert not package_app.source_metadata("1.1.0")["sourceDirty"]
    monkeypatch.setattr(package_app.subprocess, "check_output", lambda *args, **kwargs: "short\n")
    with pytest.raises(ValueError, match="immutable source"):
        package_app.source_metadata("1.1.0")


def test_exact_real_static_asset_inventory_and_budget():
    from imlp_studio.resources import ASSETS

    root = Path(__file__).resolve().parents[1]
    paths = [root / "web/dist" / name for name in ASSETS]
    assert set(ASSETS) == {"index.html", "assets/app.js", "assets/model.js", "assets/styles.css"}
    assert all(path.is_file() for path in paths)
    assert sum(path.stat().st_size for path in paths) <= 90000
