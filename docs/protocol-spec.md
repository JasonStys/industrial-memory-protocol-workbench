# IMLP/1 protocol specification

## Status

IMLP/1 is an original protocol created only for this repository. It is not an implementation of a
commercial protocol. Version 1 uses complete request/response frames over an abstract transport.

## Wire format

All multi-byte integers use big-endian byte order. The maximum payload is 256 bytes; the maximum
complete frame is 278 bytes.

| Offset | Width | Field | Validation |
| ---: | ---: | --- | --- |
| 0 | 2 | Magic | ASCII `IM` (`49 4d`) |
| 2 | 1 | Version | Exactly `01` |
| 3 | 1 | Opcode | One assigned opcode below |
| 4 | 1 | Flags | Bit 0 means response; all other bits zero |
| 5 | 1 | Reserved | Zero |
| 6 | 4 | Request ID | Unsigned correlation value |
| 10 | 4 | Address | Unsigned byte address |
| 14 | 2 | Payload length | 0–256; must match exact frame size |
| 16 | 2 | Status | Zero on requests and successful responses |
| 18 | N | Payload | Operation-specific, at most 256 bytes |
| 18+N | 4 | CRC-32 | IEEE CRC-32 over every preceding frame byte |

The decoder rejects trailing bytes. A stream transport adapter must frame bytes before invoking this
decoder; concatenated frames are not accepted as one frame.

## Opcodes

| Value | Name | Direction | Payload | Status |
| ---: | --- | --- | --- | --- |
| `0x01` | Read request | client → server | two-byte requested length, 1–256 | `ok` |
| `0x02` | Write request | client → server | bytes to write, 1–256 | `ok` |
| `0x81` | Data response | server → client | requested bytes | `ok` |
| `0x82` | Write acknowledgement | server → client | empty | `ok` |
| `0xff` | Error response | server → client | bounded diagnostic text | nonzero |

Response opcodes require flag bit 0. Request opcodes prohibit it. The codec enforces these
relationships on encoding and decoding.

## Status values

| Value | Name | Meaning |
| ---: | --- | --- |
| 0 | `ok` | Operation completed. |
| 1 | `bad_request` | Valid framing but unsupported request semantics. |
| 2 | `out_of_range` | Range does not fit the fixed memory map or payload limit. |
| 3 | `write_disabled` | Server write capability was not explicitly enabled. |
| 4 | `access_denied` | Address policy prohibits the requested range. |
| 5 | `internal_error` | The simulator could not form a safe response. |

## Address model

| Range | Access | Example purpose |
| --- | --- | --- |
| `0x0000–0x00ff` | Read-only | Synthetic identity and version bytes |
| `0x0100–0x07ff` | Read/write | Synthetic registers |
| `0x0800–0x0fff` | Denied | Reserved region used to verify access control |

The memory map is byte addressed. The full requested interval must have one allowed operation; writes
cannot partly apply across a boundary.

## Validation order

The decoder checks:

1. minimum header length;
2. magic and version;
3. assigned opcode, flags, and reserved byte;
4. payload length ceiling;
5. exact complete-frame length;
6. CRC-32;
7. opcode/flags/status/payload semantics.

This order prevents an untrusted length from being used as an index or allocation size before its
upper bound and the available bytes are known.

## Correlation and retries

Responses echo both request ID and address. The client rejects either mismatch. A read retry reuses
the same encoded request and correlation ID. A write has one transport attempt; callers must resolve
an ambiguous outcome explicitly before deciding whether another write is safe.

## Test vector

This read requests four bytes at address `0x00000100` with request ID 1:

```text
494d010100000000000100000100000200000004a0cf9ffd
```

```text
magic=494d version=01 opcode=01 flags=00 reserved=00
request_id=00000001 address=00000100 length=0002 status=0000
payload=0004 crc32=a0cf9ffd
```

Reproduce it with:

```bash
imlp-cli encode-read 0x100 4
imlp-cli inspect 494d010100000000000100000100000200000004a0cf9ffd
```

## Security note

CRC-32 detects common accidental corruption. It provides no authenticity, confidentiality, replay
protection, or resistance to intentional modification. A real deployment requires an authenticated
transport and an application-level authorization design.

