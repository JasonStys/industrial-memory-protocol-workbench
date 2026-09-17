# Safety and security model

## Scope

This repository is a simulator and parser exercise. It does not control equipment, provide a network
service, implement secure transport, or claim suitability for safety functions. Its safety value is
the explicit placement and testing of boundaries that a real design would need.

## Assets and trust assumptions

Assets are memory-map integrity, operation intent, diagnostic accuracy, and predictable resource use.
Frame bytes, addresses, lengths, deadlines, and transport results are untrusted. The in-process
transport is trusted only to exercise the same client/server interfaces deterministically.

## Controls

| Risk | Control | Evidence |
| --- | --- | --- |
| Oversized payload | 256-byte ceiling before allocation or payload indexing | unit and property tests; fuzz target |
| Integer wrap in range calculation | subtraction-based fit check; wider allowlist arithmetic | boundary tests; sanitizer CI |
| Partial write across policy boundary | validate the entire interval before copying | cross-region write test |
| Accidental write enablement | server defaults read-only | default-write rejection test |
| CLI-only safety bypass | write capability and allowlist enforced in server | direct server tests |
| Duplicate/ambiguous write after timeout | no implicit write retry | client policy test |
| Wrong response association | request ID and address must match | injected wrong-ID test |
| Corrupted response | CRC-32 and exact-length validation | mutation tests and fault demo |
| Parser memory defect | spans, owned vectors, ASan, UBSan, libFuzzer | Linux CI |
| Workflow supply-chain drift | external actions pinned to full commit SHAs | repository policy check |

## Defense-in-depth write path

A simulated write succeeds only when:

1. the caller supplies the CLI's exact `--allow-writes` opt-in;
2. the server policy sets `writes_enabled`;
3. the full interval is inside the server allowlist;
4. the full interval is inside the memory map's read/write region;
5. payload and frame limits pass; and
6. CRC and request semantics pass.

The first condition is usability protection. Conditions 2–4 are authorization controls in the lower
layers and remain effective if a different frontend calls the library.

## Error handling

Errors stay separated by layer:

- `CodecError` describes untrusted-frame rejection.
- `TransportError` describes connection, timeout, and disconnect outcomes.
- `ClientError` describes local validation, response correlation, and remote rejection.
- `Status` describes server application results.

Malformed input is never reflected into an encoded error response because the request ID and address
are not yet trusted. Valid requests receive bounded, stable diagnostics without paths or process data.

## What CRC does not do

CRC-32 is not a message authentication code. An attacker can alter bytes and calculate a new CRC.
Future real transports would need mutually authenticated encryption, peer identity, authorization,
replay handling, and auditable key lifecycle. None is simulated here to avoid presenting a toy design
as an operational security control.

## Operational technology boundary

Industrial systems prioritize availability and predictable behavior alongside security. This lab
therefore uses bounded frames, bounded read attempts, single-attempt writes, explicit failure
categories, and deterministic fault injection. Connecting similar code to equipment would still
require a hazard analysis, vendor documentation, network architecture review, change control, and
site-specific engineering approval.

## Reporting vulnerabilities

Follow the private reporting process in [SECURITY.md](../SECURITY.md). Do not include device
credentials, customer data, or non-public protocol material in a report.

