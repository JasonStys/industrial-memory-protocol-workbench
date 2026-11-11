"""@file package_app.py
@brief Build and exercise the actual C++/TypeScript/Python Windows portable app by Jason Stys.
@details Source and vendor identities are checked before publishing any local checksum. No remote
release, installer, shortcut or user workspace is changed. Symbols: docs/generated/symbol-index.md.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

if __package__:
    from .portable_archive import archive_metadata, create_archive, extract_archive, require
    from .runtime_notices import collect
else:
    from portable_archive import archive_metadata, create_archive, extract_archive, require
    from runtime_notices import collect

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = "industrial-memory-protocol-workbench"
APPLICATION = "IndustrialMemoryWorkbench"
STL_SHA256 = "1fc6b6db121d4555d8f661937d7f6013693cd8fd67495d5e5d98c1d18fb83eda"


def digest(path: Path) -> str:
    """Hash actual original/collected files without a full-memory binary copy."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def configuration(root: Path = ROOT) -> str:
    """Native product versions agree; the original wire version stays independent."""
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    web = json.loads((root / "web/package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "web/package-lock.json").read_text(encoding="utf-8"))
    version = project["version"]
    require(
        project["name"] == PRODUCT and re.fullmatch(r"\d+\.\d+\.\d+", version),
        "Product/version mismatch",
    )
    require(
        version == web["version"] == lock["version"] == lock["packages"][""]["version"],
        "Product versions disagree",
    )
    require(
        re.search(
            r"\bVERSION\s+" + re.escape(version) + r"\b",
            (root / "CMakeLists.txt").read_text(encoding="utf-8"),
        ),
        "CMake version differs",
    )
    require(
        f'__version__ = "{version}"'
        in (root / "imlp_studio/__init__.py").read_text(encoding="utf-8"),
        "Runtime version differs",
    )
    require(
        f"Version {version}" in (root / "web/public/index.html").read_text(encoding="utf-8"),
        "UI version differs",
    )
    return version


def source_metadata(version: str, allow_dirty=False) -> dict:
    """CI cannot bless local dirty candidates or package a checkout other than its exact source."""
    command = ["git", "-c", "safe.directory=" + ROOT.as_posix(), "-C", str(ROOT)]
    source = subprocess.check_output([*command, "rev-parse", "HEAD"], text=True).strip()
    changed = subprocess.check_output(
        [*command, "status", "--porcelain", "--untracked-files=all"], text=True
    )
    require(re.fullmatch(r"[a-f0-9]{40}", source), "Full immutable source required")
    require(
        not allow_dirty or os.environ.get("GITHUB_ACTIONS") != "true",
        "Dirty override forbidden in CI",
    )
    require(not changed or allow_dirty, "Clean source required; label local candidates explicitly")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        require(os.environ.get("GITHUB_SHA") == source, "CI checkout/source mismatch")
    return {
        "product": PRODUCT,
        "version": version,
        "sourceCommit": source,
        "sourceDirty": bool(changed),
        "platform": platform.system().lower(),
        "machine": platform.machine().lower(),
        "pythonVersion": platform.python_version(),
    }


def main(argv=None):
    """Build a new static-CRT C++ engine, freeze actual assets, extract and run the complete app."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--allow-dirty", action="store_true", help="Explicit local candidate; forbidden in CI"
    )
    args = parser.parse_args(argv)
    require(
        sys.platform == "win32"
        and sys.version_info[:2] == (3, 14)
        and sys.version_info[:3] >= (3, 14, 10)
        and sys.version_info.releaselevel == "final",
        "This reviewed package recipe requires patched final Windows Python3.14.10 or later3.14",
    )
    output = args.output_root.absolute()
    require(
        not output.exists() and output.parent.resolve() == output.parent,
        "Choose a new canonical output folder",
    )
    version = configuration()
    source = source_metadata(version, args.allow_dirty)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "tests/test_runtime_notices.py"),
            "--capture=sys",
            "-q",
        ],
        cwd=ROOT,
        check=True,
        timeout=45,
    )
    versions, notices = collect(ROOT)
    vendor = ROOT / "licenses/MSVC-STL-LICENSE.txt"
    require(digest(vendor) == STL_SHA256, "Actual original MSVC STL notice differs")
    from imlp_studio.resources import ASSETS

    web = ROOT / "web/dist"
    require(all((web / name).is_file() for name in ASSETS), "Build actual TypeScript UI first")
    require(
        sum((web / name).stat().st_size for name in ASSETS) <= 90000,
        "Offline UI exceeds its90kB budget",
    )
    output.mkdir()
    cpp = output / "cpp"
    cmake = shutil.which("cmake")
    require(cmake is not None, "The build environment needs actual CMake/MSVC")
    locator = (
        Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    )
    instance = subprocess.check_output(
        [
            str(locator),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ],
        timeout=15,
        text=True,
    ).strip()
    require(
        instance and Path(instance).is_dir(),
        "A stable installed MSVC build environment is required",
    )
    subprocess.run(
        [
            cmake,
            "-S",
            str(ROOT),
            "-B",
            str(cpp),
            "-A",
            "x64",
            "-DCMAKE_GENERATOR_INSTANCE=" + instance,
            "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded",
            f"-DIMLP_SOURCE_SHA={source['sourceCommit']}",
            f"-DPython3_EXECUTABLE={sys.executable}",
        ],
        cwd=ROOT,
        check=True,
        timeout=120,
    )
    subprocess.run(
        [cmake, "--build", str(cpp), "--config", "Release", "--parallel"],
        cwd=ROOT,
        check=True,
        timeout=180,
    )
    ctest = str(Path(cmake).with_name("ctest.exe"))
    subprocess.run(
        [ctest, "--test-dir", str(cpp), "-C", "Release", "--output-on-failure"],
        check=True,
        timeout=60,
    )
    engine = cpp / "Release/imlp-studio.exe"
    identity = json.loads(subprocess.check_output([str(engine), "version"], timeout=5))
    require(
        identity
        == {
            "bridge_version": 1,
            "product": PRODUCT,
            "version": version,
            "source_commit": source["sourceCommit"],
        },
        "Actual compiled C++ source differs",
    )
    metadata = {
        **source,
        **versions,
        "engineSha256": digest(engine),
        "msvcStlNoticeSha256": STL_SHA256,
        "pythonRuntimeSha256": digest(Path(sys.base_prefix) / "python314.dll"),
        "assets": {name: digest(web / name) for name in ASSETS},
    }
    generated = output / "metadata"
    generated.mkdir()
    identity_file = generated / "RELEASE.json"
    identity_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    notice_file = generated / "RUNTIME_NOTICES.txt"
    notice_file.write_bytes(
        notices
        + b"\n\nMicrosoft C++ Standard Library / Apache2.0 WITH LLVM-exception\n"
        + vendor.read_bytes()
    )
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--console",
        "--name",
        APPLICATION,
        "--distpath",
        str(output / "build"),
        "--workpath",
        str(output / "pyinstaller"),
        "--specpath",
        str(output),
    ]
    for path, destination in [
        (web, "web"),
        (engine, "engine"),
        (identity_file, "."),
        (notice_file, "licenses"),
        (vendor, "licenses/cpp"),
        (ROOT / "LICENSE", "licenses/project"),
        (ROOT / "licenses/PYTHON.txt", "licenses/python"),
    ]:
        command += ["--add-data", str(path) + ":" + destination]
    command += [str(ROOT / "launcher.py")]
    subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYINSTALLER_CONFIG_DIR": str(ROOT / ".runtime/pyinstaller-cache")},
        check=True,
        timeout=600,
    )
    require(source_metadata(version, args.allow_dirty) == source, "Source changed while packaging")
    bundle = output / "build" / APPLICATION
    require(
        digest(bundle / "_internal/engine/imlp-studio.exe") == metadata["engineSha256"],
        "Collected C++ differs",
    )
    require(
        digest(bundle / "_internal/python314.dll") == metadata["pythonRuntimeSha256"],
        "Collected patched Python differs",
    )
    require(
        digest(bundle / "_internal/licenses/cpp/MSVC-STL-LICENSE.txt") == STL_SHA256,
        "Collected original C++ terms differ",
    )
    shutil.copyfile(identity_file, bundle / "RELEASE.json")
    archive = output / f"{PRODUCT}-v{version}-windows-{source['machine']}.zip"
    create_archive(bundle, archive)
    require(archive_metadata(archive, APPLICATION) == metadata, "Archive metadata mismatch")
    with tempfile.TemporaryDirectory(prefix="imlp-extracted-") as temporary:
        extracted = extract_archive(archive, Path(temporary) / "unpacked", APPLICATION)
        require(
            digest(extracted / "_internal/licenses/cpp/MSVC-STL-LICENSE.txt") == STL_SHA256,
            "Extracted original C++ terms differ",
        )
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/smoke_app.py"),
                str(extracted / (APPLICATION + ".exe")),
                "--output",
                str(output / "acceptance"),
            ],
            cwd=temporary,
            check=True,
            timeout=180,
        )
    with archive.with_name(archive.name + ".sha256").open(
        "x", encoding="utf-8", newline="\n"
    ) as stream:
        stream.write(f"{digest(archive)}  {archive.name}\n")
    print(
        json.dumps(
            {"archive": archive.name, "sha256": digest(archive), "source": source, "accepted": True}
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
