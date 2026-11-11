"""@file test_studio_cli.py
@brief Independent real C++ studio IPC, IEEE-CRC and stateful simulator oracles by Jason Stys.
@details CMake passes its actual executable. No application encoder, mock process, live device
or network endpoint supplies expected values. Locations: docs/generated/symbol-index.md.
"""

import json
import struct
import subprocess
import sys
import unittest
import zlib
from pathlib import Path

BINARY = Path(sys.argv.pop(1)).resolve(strict=True)
MAGIC = b"IMLPS1\n"


def invoke(raw):
    """Use the real fixed CMake target; preserve binary stdin including DOS EOF and CR/LF."""
    return subprocess.run(
        [str(BINARY), "run"], input=raw, capture_output=True, timeout=5, check=False
    )


def observed(raw):
    """Require clean execution and an independently computed exact input-envelope CRC."""
    result = invoke(raw)
    if result.returncode or result.stderr:
        raise AssertionError((result.returncode, result.stderr))
    value = json.loads(result.stdout)
    if value["input_crc32"] != zlib.crc32(raw):
        raise AssertionError("Native report did not consume the exact binary control input")
    return value


def session(operations, enabled=False, begin=0x100, end=0x7FF, attempts=2):
    """Encode the published bridge layout independently with Python's big-endian struct."""
    raw = (
        MAGIC + b"\x01" + struct.pack(">BIIBH", int(enabled), begin, end, attempts, len(operations))
    )
    for verb, address, payload, faults, deadline in operations:
        length = payload if verb == 1 else len(payload)
        raw += struct.pack(">BIHHB", verb, address, length, deadline, len(faults)) + bytes(faults)
        if verb == 2:
            raw += payload
    return raw


def wire(opcode=1, payload=b"\0\x01", request_id=37, address=64, flags=0):
    """Build original IMLP/1 bytes from the public wire specification, not the product codec."""
    raw = (
        struct.pack(">2sBBBBIIHH", b"IM", 1, opcode, flags, 0, request_id, address, len(payload), 0)
        + payload
    )
    return raw + struct.pack(">I", zlib.crc32(raw))


def stream(chunks):
    """Encode arbitrary actual fragments; no accepted-frame data is reused as expectation."""
    return (
        MAGIC
        + b"\x02"
        + struct.pack(">H", len(chunks))
        + b"".join(struct.pack(">H", len(chunk)) + chunk for chunk in chunks)
    )


class StudioTests(unittest.TestCase):
    """Validate real state, retry ambiguity, original frames and closed-control boundaries."""

    def test_identity_is_separate_from_the_original_wire_protocol(self):
        result = subprocess.run(
            [str(BINARY), "version"], capture_output=True, timeout=5, check=True
        )
        value = json.loads(result.stdout)
        self.assertEqual(value["product"], "industrial-memory-protocol-workbench")
        self.assertEqual(value["version"], "1.1.0")
        self.assertEqual(value["bridge_version"], 1)
        self.assertRegex(value["source_commit"], r"^(development|[a-f0-9]{40})$")

    def test_full_binary_write_then_read_is_one_real_server_session(self):
        payload = bytes(range(256))
        result = observed(
            session([(2, 0x100, payload, [], 100), (1, 0x100, 256, [], 100)], enabled=True)
        )
        first, second = result["operations"]
        self.assertEqual([row["request_id"] for row in result["operations"]], [1, 2])
        self.assertEqual(first["client_error"], "none")
        self.assertEqual(first["before"]["hex"], "00" * 256)
        self.assertEqual(first["after"]["hex"], payload.hex())
        self.assertEqual(second["data_hex"], payload.hex())
        self.assertEqual(result["final_readable_hex"][0x100 * 2 : 0x200 * 2], payload.hex())
        request = bytes.fromhex(result["trace"][0]["hex"])
        self.assertEqual(request, wire(2, payload, 1, 0x100))
        self.assertEqual(result["metrics"]["operations"], 2)
        self.assertEqual(result["metrics"]["transport_attempts"], 2)

    def test_three_independent_write_boundaries_do_not_mutate_denied_memory(self):
        disabled = observed(session([(2, 0x100, b"\x19", [], 100)]))
        self.assertEqual(disabled["operations"][0]["remote_status"], 3)
        self.assertEqual(disabled["initial_readable_hex"], disabled["final_readable_hex"])
        narrow = observed(session([(2, 0x104, b"\x19", [], 100)], enabled=True, end=0x103))
        self.assertEqual(narrow["operations"][0]["remote_status"], 4)
        self.assertEqual(narrow["initial_readable_hex"], narrow["final_readable_hex"])
        fixed = observed(
            session([(2, 0, b"\x19", [], 100), (1, 0x800, 1, [], 100)], enabled=True, begin=0)
        )
        self.assertEqual([row["remote_status"] for row in fixed["operations"]], [4, 4])
        self.assertEqual(fixed["initial_readable_hex"], fixed["final_readable_hex"])

    def test_read_retry_keeps_id_and_fault_queue_can_cross_operation_boundary(self):
        result = observed(session([(1, 64, 1, [1], 100), (1, 64, 1, [], 100)]))
        self.assertEqual([row["attempts"] for row in result["operations"]], [2, 1])
        sent = [
            bytes.fromhex(row["hex"])
            for row in result["trace"]
            if row["direction"] == "client_to_server"
        ]
        self.assertEqual(sent, [wire(request_id=1), wire(request_id=1), wire(request_id=2)])
        self.assertEqual(result["metrics"]["retries"], 1)
        carried = observed(
            session([(1, 64, 1, [1, 1, 1], 100), (2, 0x100, b"\x19", [], 100)], enabled=True)
        )
        self.assertEqual(
            [row["client_error"] for row in carried["operations"]], ["timeout", "timeout"]
        )
        self.assertEqual(carried["operations"][1]["attempts"], 1)
        self.assertEqual(carried["initial_readable_hex"], carried["final_readable_hex"])

    def test_failed_write_ack_is_not_claimed_to_have_prevented_side_effect(self):
        result = observed(
            session([(2, 0x100, b"\x1a\r\n", [4], 100), (1, 0x100, 3, [], 100)], enabled=True)
        )
        write, read = result["operations"]
        self.assertEqual(write["client_error"], "malformed_response")
        self.assertEqual(write["attempts"], 1)
        self.assertEqual(write["before"]["hex"], "000000")
        self.assertEqual(write["after"]["hex"], "1a0d0a")
        self.assertEqual(read["data_hex"], "1a0d0a")
        self.assertEqual(result["metrics"]["retries"], 0)
        self.assertEqual(result["metrics"]["protocol_errors"], 1)

    def test_stream_offsets_corruption_and_partial_eof_partition_all_bytes(self):
        good = wire()
        bad = good[:-1] + bytes([good[-1] ^ 1])
        raw = b"\0" + bad + good + b"IM"
        result = observed(stream([raw[:1], raw[1:11], raw[11:]]))
        self.assertEqual([row["offset"] for row in result["frames"]], [1 + len(good)])
        self.assertEqual(bytes.fromhex(result["frames"][0]["hex"]), good)
        self.assertTrue(any(row["error"] == "checksum_mismatch" for row in result["issues"]))
        self.assertEqual(
            result["issues"][-1], {"offset": len(raw) - 2, "bytes": 2, "error": "truncated"}
        )
        self.assertEqual(
            sum(row["wire_bytes"] for row in result["frames"])
            + sum(row["bytes"] for row in result["issues"])
            + result["omitted_issue_bytes"],
            len(raw),
        )
        self.assertEqual(result["pending_bytes"], 0)
        empty = observed(stream([b""]))
        self.assertEqual((empty["input_bytes"], empty["frames"], empty["issues"]), (0, [], []))

    def test_actual_compose_and_inspect_distinguish_invalid_frame_from_bad_ipc(self):
        payload = bytes(range(256))
        raw = (
            MAGIC + b"\x04" + struct.pack(">BBBIIHH", 1, 2, 0, 37, 0x100, 0, len(payload)) + payload
        )
        composed = observed(raw)
        self.assertTrue(composed["accepted"])
        self.assertEqual(bytes.fromhex(composed["hex"]), wire(2, payload, 37, 0x100))
        encoded = bytes.fromhex(composed["hex"])
        inspected = observed(MAGIC + b"\x03" + struct.pack(">H", len(encoded)) + encoded)
        self.assertEqual(inspected["frame"], composed["frame"])
        damaged = encoded[:-1] + bytes([encoded[-1] ^ 1])
        blocked = observed(MAGIC + b"\x03" + struct.pack(">H", len(damaged)) + damaged)
        self.assertEqual(
            (blocked["accepted"], blocked["error"], blocked["frame"]),
            (False, "checksum_mismatch", None),
        )
        for malformed in [b"", b"wrong", raw + b"\0", MAGIC + b"\xff", stream([b"x" * 4097])]:
            with self.subTest(bytes=len(malformed)):
                refused = invoke(malformed)
                self.assertEqual(refused.returncode, 2)
                self.assertEqual(refused.stdout, b"")
                self.assertIn(b"invalid", refused.stderr)


if __name__ == "__main__":
    unittest.main()
