# CLI guide

## Safety boundary

Every command operates only on an in-process synthetic simulator. There is no hostname, port, serial
device, physical I/O, or credential option.

## Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | Command completed or the multi-scenario demo finished. |
| 1 | Usage error or unknown command. |
| 2 | Invalid numeric/hex input or missing write opt-in. |
| 3 | Frame encoding or decoding failed. |
| 4 | Simulated client operation failed. |

## Inspect a frame

```bash
imlp-cli inspect 494d010100000000000100000100000200000004a0cf9ffd
```

Output:

```text
version=1 opcode=0x1 flags=0 request_id=1 address=256 status=ok payload=0004
```

Odd-length hex, non-hex characters, oversized input, checksum errors, and trailing bytes fail rather
than being partially consumed.

## Generate a read test vector

```bash
imlp-cli encode-read 0x100 4
```

Addresses and lengths accept decimal or lowercase `0x` prefixes. The parser consumes the complete
argument and rejects signs, whitespace suffixes, and overflow.

## Read simulator memory

```bash
imlp-cli read 0 16
```

The result line separates client error, remote status, attempts, diagnostic, and data. Trace lines
show exact request and response frames.

## Write simulator memory

This fails because explicit opt-in is missing:

```bash
imlp-cli write 0x100 deadbeef
```

This creates a write-enabled simulator for that process and asks the server to validate the range:

```bash
imlp-cli write 0x100 deadbeef --allow-writes
```

Changing the flag does not bypass the server allowlist or the memory map. `0x0000` remains read-only,
and `0x0800` remains denied.

## Run the fault demonstration

```bash
imlp-cli demo
```

The demo includes read-only rejection, read retry after timeout, response corruption, and an
explicitly enabled write/readback. See [fault-catalog.md](fault-catalog.md) for expected behavior.

