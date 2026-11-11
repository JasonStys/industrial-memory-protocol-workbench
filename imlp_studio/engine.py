"""@file engine.py
@brief Invoke only the fixed original C++ engines and verify source-bound evidence by Jason Stys.
@details The compiled child receives typed inert stdin, never submitted code or a host endpoint.
Python verifies wire/CRC/partition relationships independently.
Symbols: docs/generated/symbol-index.md.
"""

import hashlib
import json
import os
import struct
import subprocess
import zlib
from pathlib import Path

from imlp_studio import __version__
from imlp_studio.domain import canonical, control, fields, hexadecimal, integer, request
from imlp_studio.private_io import bounded

PRODUCT = "industrial-memory-protocol-workbench"
CODEC_ERRORS = {
    "none",
    "truncated",
    "bad_magic",
    "unsupported_version",
    "unsupported_opcode",
    "unsupported_flags",
    "nonzero_reserved",
    "payload_too_large",
    "length_mismatch",
    "checksum_mismatch",
    "invalid_semantics",
}
CLIENT_ERRORS = {
    "none",
    "invalid_argument",
    "connect_failed",
    "timeout",
    "disconnected",
    "encoding_failed",
    "malformed_response",
    "correlation_mismatch",
    "unexpected_response",
    "remote_error",
}


def require(value: object, message: str):
    """Validation remains active in optimized native builds."""
    if not value:
        raise ValueError(message)


def unique(pairs):
    """A repeated report key cannot overwrite the evidence used by another contract check."""
    value = {}
    for key, item in pairs:
        require(key not in value, "C++ report contains a repeated key")
        value[key] = item
    return value


def wire_frame(raw: bytes) -> dict:
    """Independently read the published wire layout and IEEE CRC without calling the C++ codec."""
    require(22 <= len(raw) <= 278, "Accepted frame has invalid extent")
    magic, version, opcode, flags, reserved, identity, address, size, status = struct.unpack(
        ">2sBBBBIIHH", raw[:18]
    )
    require(
        magic == b"IM" and version == 1 and reserved == 0 and len(raw) == size + 22,
        "Accepted frame fields/length differ",
    )
    require(zlib.crc32(raw[:-4]) == struct.unpack(">I", raw[-4:])[0], "Accepted frame CRC differs")
    return {
        "version": version,
        "opcode": opcode,
        "flags": flags,
        "request_id": identity,
        "address": address,
        "status": status,
        "payload_hex": raw[18:-4].hex(),
    }


def memory(value: object, length: int):
    """An unreadable range stays empty with its actual status, never invented zero bytes."""
    value = fields(value, {"status", "hex"}, "Affected memory")
    integer(value["status"], "Memory status", 0, 5)
    raw = hexadecimal(value["hex"], "Affected memory", 256)
    require(len(raw) == (length if value["status"] == 0 else 0), "Affected memory extent differs")


def recorded_frame(value: object, raw: bytes):
    """A boolean/float cannot pass as a wire integer through Python's permissive equality."""
    actual = wire_frame(raw)
    value = fields(value, set(actual), "Accepted frame fields")
    for name, maximum in {
        "version": 255,
        "opcode": 255,
        "flags": 255,
        "request_id": 0xFFFFFFFF,
        "address": 0xFFFFFFFF,
        "status": 65535,
    }.items():
        integer(value[name], name, 0, maximum)
    require(
        isinstance(value["payload_hex"], str) and value == actual, "Accepted frame evidence differs"
    )


def validate_report(value: dict, report: object, raw_input: bytes, source: str) -> dict:
    """Reject malformed, misbound or contradictory child output before saving any evidence."""
    base = {"bridge_version", "product", "version", "source_commit", "input_crc32", "kind"}
    extra = {
        "session": {"initial_readable_hex", "operations", "final_readable_hex", "metrics", "trace"},
        "stream": {
            "input_bytes",
            "frames",
            "issues",
            "omitted_issue_records",
            "omitted_issue_bytes",
            "pending_bytes",
        },
        "inspect": {"accepted", "error", "hex", "frame"},
        "compose": {"accepted", "error", "hex", "frame"},
    }
    kind = value["kind"]
    report = fields(report, base | extra[kind], "C++ evidence")
    require(
        type(report["bridge_version"]) is int and report["bridge_version"] == 1,
        "Native bridge version differs",
    )
    require(
        report["product"] == PRODUCT
        and report["version"] == __version__
        and report["source_commit"] == source,
        "Native source/product identity differs",
    )
    require(
        type(report["input_crc32"]) is int
        and report["input_crc32"] == zlib.crc32(raw_input)
        and report["kind"] == kind,
        "Exact native control input differs",
    )
    if kind == "session":
        for key in ["initial_readable_hex", "final_readable_hex"]:
            require(
                len(hexadecimal(report[key], "Readable memory map", 2048)) == 2048,
                "Whole readable map extent differs",
            )
        operations = report["operations"]
        require(
            isinstance(operations, list) and len(operations) == len(value["operations"]),
            "Native operation count differs",
        )
        trace = report["trace"]
        require(
            isinstance(trace, list) and len(trace) <= 384 and len(trace) % 2 == 0,
            "Native trace count differs",
        )
        for index, row in enumerate(trace):
            fields(row, {"sequence", "direction", "outcome", "hex"}, "Trace record")
            require(
                type(row["sequence"]) is int and row["sequence"] == index + 1,
                "Trace sequence differs",
            )
            require(
                row["direction"] == ("client_to_server" if index % 2 == 0 else "server_to_client"),
                "Trace direction differs",
            )
            require(
                isinstance(row["outcome"], str) and len(row["outcome"]) <= 256,
                "Unbounded trace detail",
            )
            data = hexadecimal(row["hex"], "Trace bytes", 278)
            if index % 2 == 0:
                wire_frame(data)
        previous = 0
        attempts = 0
        retries = 0
        for index, (operation, row) in enumerate(zip(value["operations"], operations, strict=True)):
            fields(
                row,
                {
                    "index",
                    "verb",
                    "request_id",
                    "attempts",
                    "client_error",
                    "remote_status",
                    "data_hex",
                    "detail",
                    "trace_begin",
                    "trace_end",
                    "before",
                    "after",
                },
                "Operation result",
            )
            require(
                type(row["index"]) is int
                and row["index"] == index
                and row["verb"] == operation["verb"]
                and type(row["request_id"]) is int
                and row["request_id"] == index + 1,
                "Operation identity differs",
            )
            integer(
                row["attempts"],
                "Actual attempts",
                0,
                value["read_attempts"] if operation["verb"] == "read" else 1,
            )
            require(
                isinstance(row["client_error"], str) and row["client_error"] in CLIENT_ERRORS,
                "Unknown client outcome",
            )
            integer(row["remote_status"], "Remote status", 0, 5)
            require(
                isinstance(row["detail"], str) and len(row["detail"]) <= 512,
                "Unbounded operation detail",
            )
            integer(row["trace_begin"], "Trace beginning", 0, len(trace))
            integer(row["trace_end"], "Trace end", row["trace_begin"], len(trace))
            require(
                row["trace_begin"] == previous
                and row["trace_end"] - previous == row["attempts"] * 2,
                "Operation/trace partition differs",
            )
            length = (
                operation["length"]
                if operation["verb"] == "read"
                else len(hexadecimal(operation["payload_hex"], "Payload", 256))
            )
            for key in ["before", "after"]:
                memory(row[key], length)
            for sent in trace[row["trace_begin"] : row["trace_end"] : 2]:
                frame = wire_frame(bytes.fromhex(sent["hex"]))
                payload = (
                    struct.pack(">H", length).hex()
                    if operation["verb"] == "read"
                    else operation["payload_hex"].lower()
                )
                require(
                    frame
                    == {
                        "version": 1,
                        "opcode": 1 if operation["verb"] == "read" else 2,
                        "flags": 0,
                        "request_id": index + 1,
                        "address": operation["address"],
                        "status": 0,
                        "payload_hex": payload,
                    },
                    "Actual request wire differs from submitted operation",
                )
            data = hexadecimal(row["data_hex"], "Operation result", 256)
            if row["client_error"] == "none":
                require(
                    row["remote_status"] == 0
                    and row["attempts"] > 0
                    and len(data) == (length if operation["verb"] == "read" else 0),
                    "Successful operation contradicts actual bytes/status",
                )
            if operation["verb"] == "read":
                require(
                    row["before"] == row["after"], "A read unexpectedly changed simulator memory"
                )
            previous = row["trace_end"]
            attempts += row["attempts"]
            retries += max(row["attempts"] - 1, 0)
        require(previous == len(trace), "Unassigned native trace records")
        metrics = fields(
            report["metrics"],
            {
                "operations",
                "transport_attempts",
                "reconnects",
                "retries",
                "timeouts",
                "protocol_errors",
            },
            "Client metrics",
        )
        for key, item in metrics.items():
            integer(item, key, 0, 192)
        require(
            metrics["operations"] == len(operations)
            and metrics["transport_attempts"] == attempts
            and metrics["retries"] == retries,
            "Actual client counters contradict recorded attempts",
        )
    elif kind == "stream":
        raw = b"".join(bytes.fromhex(item) for item in value["chunks_hex"])
        require(
            type(report["input_bytes"]) is int
            and report["input_bytes"] == len(raw)
            and type(report["pending_bytes"]) is int
            and report["pending_bytes"] == 0,
            "Stream consumption differs",
        )
        require(
            isinstance(report["frames"], list)
            and len(report["frames"]) <= 2978
            and isinstance(report["issues"], list)
            and len(report["issues"]) <= 256,
            "Stream record count differs",
        )
        ranges = []
        known = 0
        for row in report["frames"]:
            fields(row, {"offset", "wire_bytes", "hex", "frame"}, "Stream frame")
            integer(row["offset"], "Frame offset", 0, len(raw))
            integer(row["wire_bytes"], "Frame extent", 22, 278)
            actual = hexadecimal(row["hex"], "Stream frame", 278)
            end = row["offset"] + row["wire_bytes"]
            require(
                end <= len(raw)
                and len(actual) == row["wire_bytes"]
                and raw[row["offset"] : end] == actual,
                "Stream frame is not the accepted exact original slice",
            )
            recorded_frame(row["frame"], actual)
            ranges.append((row["offset"], end))
            known += len(actual)
        for row in report["issues"]:
            fields(row, {"offset", "bytes", "error"}, "Stream issue")
            integer(row["offset"], "Issue offset", 0, len(raw))
            integer(row["bytes"], "Issue extent", 1, len(raw))
            require(
                isinstance(row["error"], str)
                and row["error"] in CODEC_ERRORS - {"none"}
                and row["offset"] + row["bytes"] <= len(raw),
                "Stream issue bounds/category differ",
            )
            ranges.append((row["offset"], row["offset"] + row["bytes"]))
            known += row["bytes"]
        ranges.sort()
        require(
            all(
                previous[1] <= current[0]
                for previous, current in zip(ranges, ranges[1:], strict=False)
            ),
            "Known stream extents overlap",
        )
        integer(report["omitted_issue_records"], "Omitted issue count", 0, 65536)
        integer(report["omitted_issue_bytes"], "Omitted issue bytes", 0, 65536)
        require(
            known + report["omitted_issue_bytes"] == len(raw),
            "Stream byte accounting is incomplete",
        )
    else:
        require(
            type(report["accepted"]) is bool
            and isinstance(report["error"], str)
            and report["error"] in CODEC_ERRORS,
            "Frame outcome differs",
        )
        raw = hexadecimal(report["hex"], "Exact frame result", 278)
        if kind == "inspect":
            require(
                raw == bytes.fromhex(value["frame_hex"]),
                "Inspection did not retain submitted bytes",
            )
        if report["accepted"]:
            require(report["error"] == "none", "Accepted frame reports an error")
            recorded_frame(report["frame"], raw)
            if kind == "compose":
                require(
                    report["frame"]
                    == {
                        key: value[key].lower() if key == "payload_hex" else value[key]
                        for key in [
                            "version",
                            "opcode",
                            "flags",
                            "request_id",
                            "address",
                            "status",
                            "payload_hex",
                        ]
                    },
                    "Composed frame differs from requested fields",
                )
        else:
            require(
                report["error"] != "none"
                and report["frame"] is None
                and (kind == "inspect" or raw == b""),
                "Blocked frame contains false accepted/partial evidence",
            )
    return report


def report_status(value: dict, report: dict) -> str:
    """A rejected acknowledgement never means a write was certainly prevented."""
    if value["kind"] == "session":
        return (
            "review"
            if any(item["client_error"] != "none" for item in report["operations"])
            else "completed"
        )
    if value["kind"] == "stream":
        return (
            "review"
            if report["issues"] or report["omitted_issue_records"] or not report["frames"]
            else "completed"
        )
    return "completed" if report["accepted"] else "blocked"


class Engine:
    """Bind a single owned C++ binary, typed stdin and finite execution before any history write."""

    def __init__(self, executable: Path, source: str, expected: str):
        self.executable = executable.absolute()
        require(
            hashlib.sha256(bounded(self.executable, 32 * 1024 * 1024)).hexdigest() == expected,
            "Actual C++ engine digest differs",
        )
        self.environment = {
            key: item
            for key, item in os.environ.items()
            if key.upper()
            in {
                "SYSTEMROOT",
                "WINDIR",
                "SYSTEMDRIVE",
                "TEMP",
                "TMP",
                "HOME",
                "USERPROFILE",
                "LOCALAPPDATA",
                "APPDATA",
                "LANG",
                "LC_ALL",
            }
        }
        self.environment["PATH"] = (
            os.pathsep.join(
                [str(Path(os.environ["SYSTEMROOT"]) / "System32"), os.environ["SYSTEMROOT"]]
            )
            if os.name == "nt"
            else "/usr/bin:/bin"
        )
        try:
            raw = subprocess.check_output(
                [str(self.executable), "version"], env=self.environment, timeout=5
            )
            require(len(raw) <= 16 * 1024, "Unbounded C++ identity")
            actual = json.loads(raw, object_pairs_hook=unique)
            require(
                isinstance(actual, dict)
                and type(actual.get("bridge_version")) is int
                and actual
                == {
                    "bridge_version": 1,
                    "product": PRODUCT,
                    "version": __version__,
                    "source_commit": source,
                },
                "Compiled C++ source/version differs",
            )
        except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as error:
            raise ValueError("Actual C++ engine identity is unavailable") from error
        self.identity = {
            "sourceCommit": source,
            "sha256": expected,
            "version": __version__,
            "language": "C++20",
        }

    def run(self, submitted: object) -> dict:
        """Run a complete actual simulation; malformed/timeout/nonzero results are never saved."""
        value = request(submitted)
        raw = control(value)
        try:
            result = subprocess.run(
                [str(self.executable), "run"],
                input=raw,
                capture_output=True,
                env=self.environment,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ValueError(
                "Actual C++ operation exceeded its finite execution deadline"
            ) from error
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError("The actual C++ engine is unavailable; no run was saved") from error
        require(
            result.returncode == 0 and not result.stderr and len(result.stdout) <= 8 * 1024 * 1024,
            "Actual C++ execution did not produce a complete bounded result",
        )
        try:
            report = json.loads(
                result.stdout.decode("utf-8", errors="strict"),
                object_pairs_hook=unique,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite C++ result")),
            )
        except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
            raise ValueError("Actual C++ output is malformed") from error
        report = validate_report(value, report, raw, self.identity["sourceCommit"])
        # This application annotation is derived after validation, not a claimed C++ wire field.
        report["status"] = report_status(value, report)
        report["input_sha256"] = hashlib.sha256(canonical(value)).hexdigest()
        return report
