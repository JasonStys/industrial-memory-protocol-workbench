"""@file smoke_app.py
@brief Launch only the supplied extracted native executable and check real UI/persistence.

main/launch retain each actual owner until its normal quit and exit0; temporary synthetic
workspaces remain separate from software/user profiles. Exact locations: docs/code-index.md.
"""

import argparse
import hashlib
import json
import queue
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def require(value, message):
    """Acceptance is active under optimized Python and never silently retries a failed launch."""
    if not value:
        raise ValueError(message)


def launch_command(command: list[str], profile: Path):
    "Read owned ready/session records with a bounded deadline, never reuse/probe an old service."
    process = subprocess.Popen(
        [*command, "--no-window", "--no-browser", "--profile", str(profile)],
        cwd=profile.parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    records = queue.Queue(maxsize=3)

    def reader():
        try:
            for _ in range(2):
                line = process.stdout.readline(16385)
                require(0 < len(line) <= 16384, "Missing/oversized native readiness")
                records.put(json.loads(line), timeout=1)
        except (ValueError, OSError) as error:
            records.put(error, timeout=1)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 20
        ready = records.get(timeout=max(deadline - time.monotonic(), 0.001))
        require(
            isinstance(ready, dict) and ready.get("event") == "ready",
            "Native app did not become ready",
        )
        session = records.get(timeout=max(deadline - time.monotonic(), 0.001))
        require(
            isinstance(session, dict) and session.get("event") == "test-session",
            "Native test session missing",
        )
        return process, ready, session["capability"]
    except BaseException:
        process.kill()
        process.wait(timeout=5)
        raise


def launch(executable: Path, profile: Path):
    """Launch only the supplied extracted executable, never a source fallback."""
    return launch_command([str(executable)], profile)


def close_owned(process, ready: dict, token: str):
    """Failure cleanup requests this nonce-bound owner's normal Quit before waiting for its exit."""
    if process.poll() is not None:
        return
    try:
        with httpx.Client(
            base_url=ready["url"],
            trust_env=False,
            timeout=5,
            headers={"X-IMLP-Capability": token, "Origin": ready["url"]},
        ) as client:
            health = client.get("/health").json()
            require(
                health["nonce"] == ready["nonce"] and health["engine"] == ready["engine"],
                "Refuse to stop a listener that does not match this actual owner",
            )
            require(
                client.post("/api/quit", json={"quit": True}).status_code == 200,
                "Owned failure cleanup Quit was refused",
            )
    except httpx.ConnectError:
        # A successful GUI Quit may already have closed the socket while draining handlers.
        require(process.wait(timeout=20) == 0, "Already-closing owner did not exit normally")
    else:
        require(process.wait(timeout=20) == 0, "Owned failure cleanup did not exit normally")


def main():
    "Actual browser editing/export/import followed by a second native launch proves saved history."
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    metadata = json.loads((executable.parent / "RELEASE.json").read_text(encoding="utf-8"))
    source = metadata["sourceCommit"]
    require(
        metadata["version"] == "1.1.0"
        and metadata["product"] == "industrial-memory-protocol-workbench",
        "Wrong native product",
    )
    vendor = executable.parent / "_internal/licenses/cpp/MSVC-STL-LICENSE.txt"
    require(
        hashlib.sha256(vendor.read_bytes()).hexdigest() == metadata["msvcStlNoticeSha256"],
        "Extracted original C++ terms differ",
    )
    for name, expected in [
        ("python314.dll", metadata["pythonRuntimeSha256"]),
        ("engine/imlp-studio.exe", metadata["engineSha256"]),
    ]:
        require(
            hashlib.sha256((executable.parent / "_internal" / name).read_bytes()).hexdigest()
            == expected,
            "Extracted native resource differs",
        )
    args.output.mkdir(parents=True, exist_ok=False)
    processes = []
    workspace = tempfile.TemporaryDirectory(prefix="imlp-native-workspace-", delete=False)
    with workspace as temporary:
        # Canonicalize only this freshly created harness directory (macOS /var may be an OS alias).
        # Production workspace admission continues to reject supplied alias paths unchanged.
        profile = Path(temporary).resolve(strict=True) / "workspace"
        try:
            process, ready, token = launch(executable, profile)
            processes.append((process, ready, token))
            with httpx.Client(
                base_url=ready["url"],
                trust_env=False,
                timeout=5,
                headers={"X-IMLP-Capability": token, "Origin": ready["url"]},
            ) as client:
                health = client.get("/health").json()
                require(
                    health["nonce"] == ready["nonce"]
                    and health["engine"]["sourceCommit"] == source,
                    "Owned source/nonce mismatch",
                )
            url = ready["url"] + "/#native=" + token
            subprocess.run(
                [
                    "node",
                    str(ROOT / "tools/native_feature_smoke.mjs"),
                    url,
                    str(args.output),
                    source,
                ],
                cwd=temporary,
                check=True,
                timeout=90,
            )
            require(process.wait(timeout=20) == 0, "First native owner did not exit normally")
            process2, ready2, token2 = launch(executable, profile)
            processes.append((process2, ready2, token2))
            require(ready2["nonce"] != ready["nonce"], "Restart reused the old instance")
            with httpx.Client(
                base_url=ready2["url"],
                trust_env=False,
                timeout=5,
                headers={"X-IMLP-Capability": token2, "Origin": ready2["url"]},
            ) as client:
                history = client.get("/api/history").json()
                require(
                    history["total"] == 8,
                    "Actual native restart did not retain exactly eight completed experiments",
                )
                require(
                    sorted(item["kind"] for item in history["items"])
                    == [
                        "compose",
                        "compose",
                        "inspect",
                        "session",
                        "session",
                        "session",
                        "session",
                        "stream",
                    ],
                    "Unexpected retained experiment kinds",
                )
                require(
                    client.get("/api/history", headers={"X-IMLP-Capability": token}).status_code
                    == 403,
                    "Old capability survived native restart",
                )
                require(
                    client.post("/api/quit", json={"quit": True}).status_code == 200,
                    "Normal owned Quit failed",
                )
            require(process2.wait(timeout=20) == 0, "Restarted native owner did not exit normally")
            receipt = {
                "passed": True,
                "version": "1.1.0",
                "sourceCommit": source,
                "sourceDirty": metadata["sourceDirty"],
                "engineSha256": metadata["engineSha256"],
                "msvcStlNoticeSha256": metadata["msvcStlNoticeSha256"],
                "pythonRuntimeSha256": metadata["pythonRuntimeSha256"],
                "normalExits": [0, 0],
                "retainedRecords": 8,
                "actualExtractedExecutable": str(executable),
                "browser": "Chromium",
                "profile": "isolated synthetic temporary workspace",
                "limits": [
                    (
                        "Portable launch/unpack acceptance; no OS installer"
                        " transaction or clean-machine claim"
                    ),
                    (
                        "Automated launches use --no-window --no-browser;"
                        " manual default-browser opener is unverified"
                    ),
                    (
                        "Synthetic IMLP/1 simulator only; no device/network integration, "
                        "commercial compatibility or physical I/O. CRC is not authentication."
                    ),
                ],
                "screenshots": {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in args.output.glob("*.png")
                },
            }
            (args.output / "native-acceptance.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
            )
        finally:
            for process, owned_ready, owned_token in processes:
                close_owned(process, owned_ready, owned_token)
                process.stdout.close()
                process.stderr.close()
            if all(process.poll() is not None for process, _, _ in processes):
                workspace.cleanup()


if __name__ == "__main__":
    main()
