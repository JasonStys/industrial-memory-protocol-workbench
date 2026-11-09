"""
@file test_stream_cli.py
@brief Exercises the actual synthetic CLI with independent Python struct/CRC golden bytes. Created by Jason Stys.
@details Exact test/helper/variable locations are indexed in docs/generated/symbol-index.md.
"""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import unittest
import zlib
from pathlib import Path

BINARY = Path(sys.argv.pop(1)).resolve(strict=True)


def wire() -> bytes:
    """Encode a published-format read request independently of the product codec/CLI encoder."""
    data = struct.pack(">2sBBBBIIHH", b"IM", 1, 1, 0, 0, 7, 64, 2, 0) + b"\0\1"
    return data + struct.pack(">I", zlib.crc32(data))


def invoke(*chunks: str) -> subprocess.CompletedProcess[str]:
    """Run only CMake's trusted synthetic CLI target; no target address/device/source/plugin is accepted."""
    return subprocess.run(
        [str(BINARY), "stream-inspect", *chunks], text=True, capture_output=True, timeout=5, check=False
    )


class StreamCliTests(unittest.TestCase):
    """Actual process/status/JSON contracts distinguish valid streams, corruption, EOF and invalid input."""

    def test_fragment_and_coalesced_golden(self) -> None:
        """The independent golden frame decodes at exact offsets across fragmented and combined chunks."""
        data = wire()
        completed = invoke(data[:1].hex(), (data[1:] + data).hex())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual([row["offset"] for row in result["frames"]], [0, len(data)])
        self.assertEqual(result["frames"][0]["request_id"], 7)
        self.assertEqual(result["frames"][0]["payload_bytes"], 2)
        self.assertEqual(result["issues"], [])

    def test_corruption_recovery_and_partial_eof(self) -> None:
        """CRC corruption is reported, not accepted; a following valid frame and truncated EOF stay distinct."""
        data = wire()
        bad = data[:-1] + bytes([data[-1] ^ 1])
        result = json.loads(invoke((b"\0" + bad + data + b"IM").hex()).stdout)
        self.assertEqual([row["offset"] for row in result["frames"]], [1 + len(data)])
        self.assertTrue(any(row["error"] == "checksum_mismatch" for row in result["issues"]))
        self.assertEqual(result["issues"][-1], {"offset": 1 + 2 * len(data), "discarded_bytes": 2, "error": "truncated"})

    def test_invalid_inputs_fail_before_output(self) -> None:
        """Invalid/oversized/too-many chunks do not emit a misleading partial JSON review."""
        for chunks in (("0",), ("gg",), ("00" * 279,), tuple("00" for _ in range(257))):
            result = invoke(*chunks)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
