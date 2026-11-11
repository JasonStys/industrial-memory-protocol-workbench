"""@file domain.py
@brief Validate closed editable simulator requests and encode bounded native IPC by Jason Stys.
@details Python owns typed user input, not protocol decisions. C++ independently checks the
control envelope before calling original engines. Symbols: docs/generated/symbol-index.md.
"""

import json
import re
import struct

MAGIC = b"IMLPS1\n"
FAULTS = {
    "timeout": 1,
    "disconnect": 2,
    "truncate_response": 3,
    "corrupt_response": 4,
    "wrong_request_id": 5,
}


def canonical(value: object) -> bytes:
    """A cryptographic input fingerprint describes these protocol bytes, not file whitespace."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError("Provide bounded finite JSON input") from error


def fields(value: object, expected: set[str], label: str) -> dict:
    """Reject hidden/unsigned configuration keys instead of silently removing them."""
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(label + " needs exactly these fields: " + ", ".join(sorted(expected)))
    return value


def integer(value: object, label: str, lower: int, upper: int) -> int:
    """Booleans/floats/negative/oversized values are not valid fixed-width integers."""
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{label} must be an integer from {lower} to {upper}")
    return value


def hexadecimal(value: object, label: str, maximum: int) -> bytes:
    """Preserve all exact bytes; a source string is contiguous even-length hexadecimal."""
    if (
        not isinstance(value, str)
        or len(value) > maximum * 2
        or len(value) % 2
        or re.fullmatch(r"[a-fA-F0-9]*", value) is None
    ):
        raise ValueError(
            f"{label} needs even-length contiguous hexadecimal, at most {maximum} bytes"
        )
    return bytes.fromhex(value)


def request(value: object) -> dict:
    """Validate typed input; deliberate original-codec/client refusals remain evidence."""
    if not isinstance(value, dict):
        raise ValueError("Provide a complete simulator input object")
    kind = value.get("kind")
    if not isinstance(kind, str) or kind not in {"session", "stream", "inspect", "compose"}:
        raise ValueError("Choose session, stream, inspect or compose")
    if len(canonical(value)) > 256 * 1024:
        raise ValueError("Input exceeds 256 KiB")
    if kind == "session":
        fields(
            value,
            {
                "kind",
                "writes_enabled",
                "write_allow_begin",
                "write_allow_end",
                "read_attempts",
                "operations",
            },
            "Session",
        )
        if type(value["writes_enabled"]) is not bool:
            raise ValueError("Simulated writes_enabled must be explicitly true or false")
        begin = integer(value["write_allow_begin"], "Allowlist beginning", 0, 0xFFFFFFFF)
        end = integer(value["write_allow_end"], "Allowlist end", 0, 0xFFFFFFFF)
        if begin > end:
            raise ValueError("Allowlist beginning must not exceed its end")
        integer(value["read_attempts"], "Read attempts", 1, 3)
        operations = value["operations"]
        if not isinstance(operations, list) or not 1 <= len(operations) <= 64:
            raise ValueError("A session needs 1–64 ordered operations")
        for operation in operations:
            if not isinstance(operation, dict) or operation.get("verb") not in ("read", "write"):
                raise ValueError("Each operation must choose read or write")
            extra = "length" if operation["verb"] == "read" else "payload_hex"
            fields(operation, {"verb", "address", extra, "deadline_ms", "faults"}, "Operation")
            integer(operation["address"], "Address", 0, 0xFFFFFFFF)
            integer(operation["deadline_ms"], "Simulated deadline", 0, 1000)
            faults = operation["faults"]
            if (
                not isinstance(faults, list)
                or len(faults) > 3
                or any(not isinstance(item, str) or item not in FAULTS for item in faults)
            ):
                raise ValueError("Choose at most three declared loopback faults per operation")
            if extra == "length":
                integer(operation[extra], "Read length", 0, 256)
            else:
                hexadecimal(operation[extra], "Write payload", 256)
    elif kind == "stream":
        fields(value, {"kind", "chunks_hex"}, "Stream")
        chunks = value["chunks_hex"]
        if not isinstance(chunks, list) or not 1 <= len(chunks) <= 256:
            raise ValueError(
                "A stream needs 1–256 chunks (one empty chunk represents an empty stream)"
            )
        if sum(len(hexadecimal(chunk, "Stream chunk", 4096)) for chunk in chunks) > 65536:
            raise ValueError("Stream exceeds 64 KiB total")
    elif kind == "inspect":
        fields(value, {"kind", "frame_hex"}, "Exact-frame inspection")
        hexadecimal(value["frame_hex"], "Exact frame", 278)
    else:
        fields(
            value,
            {
                "kind",
                "version",
                "opcode",
                "flags",
                "request_id",
                "address",
                "status",
                "payload_hex",
            },
            "Frame composition",
        )
        for key in ["version", "opcode", "flags"]:
            integer(value[key], key, 0, 255)
        for key in ["request_id", "address"]:
            integer(value[key], key, 0, 0xFFFFFFFF)
        integer(value["status"], "Status", 0, 65535)
        hexadecimal(value["payload_hex"], "Frame payload", 256)
    return json.loads(canonical(value))


def control(value: dict) -> bytes:
    """Encode fixed typed fields only; no host path, plugin, command or remote address exists."""
    value = request(value)
    kind = value["kind"]
    if kind == "session":
        raw = (
            MAGIC
            + b"\x01"
            + struct.pack(
                ">BIIBH",
                int(value["writes_enabled"]),
                value["write_allow_begin"],
                value["write_allow_end"],
                value["read_attempts"],
                len(value["operations"]),
            )
        )
        for operation in value["operations"]:
            write = operation["verb"] == "write"
            payload = hexadecimal(operation["payload_hex"], "Payload", 256) if write else b""
            length = len(payload) if write else operation["length"]
            raw += struct.pack(
                ">BIHHB",
                2 if write else 1,
                operation["address"],
                length,
                operation["deadline_ms"],
                len(operation["faults"]),
            )
            raw += bytes(FAULTS[item] for item in operation["faults"]) + payload
        return raw
    if kind == "stream":
        chunks = [hexadecimal(item, "Chunk", 4096) for item in value["chunks_hex"]]
        return (
            MAGIC
            + b"\x02"
            + struct.pack(">H", len(chunks))
            + b"".join(struct.pack(">H", len(item)) + item for item in chunks)
        )
    if kind == "inspect":
        raw = hexadecimal(value["frame_hex"], "Frame", 278)
        return MAGIC + b"\x03" + struct.pack(">H", len(raw)) + raw
    payload = hexadecimal(value["payload_hex"], "Payload", 256)
    return (
        MAGIC
        + b"\x04"
        + struct.pack(
            ">BBBIIHH",
            value["version"],
            value["opcode"],
            value["flags"],
            value["request_id"],
            value["address"],
            value["status"],
            len(payload),
        )
        + payload
    )
