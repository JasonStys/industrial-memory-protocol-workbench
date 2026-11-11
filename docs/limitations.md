# Known limitations

## Deliberate scope limits

- IMLP/1 is synthetic and has no commercial protocol compatibility.
- The transport is in-process; there is no TCP, UDP, serial, or fieldbus adapter.
- The exact codec accepts one complete frame; the separate bounded stream decoder handles
  fragmented/coalesced input and diagnostic recovery without authenticating sender or boundaries.
- The simulator has one client, one thread, and one fixed 4 KiB address space.
- There is no encryption, authentication, authorization identity, replay protection, or key model.
- CRC-32 detects accidental corruption only.
- Trace retention is unbounded until the caller invokes `clear_trace()`.
- Error text is English and not localized.
- The benchmark measures an in-process encode/handle/decode path, not network latency.
- CI fuzzing is a bounded smoke campaign without a retained evolving corpus.
- The native GUI's C++ session is one fresh simulated server per run, not a live persistent device.
  Within a session, ordered operations share its memory and queued faults; separate runs do not.
- Native packaging currently targets Windows x64. Three-OS source tests do not establish Linux/macOS
  package delivery. Portable extraction/launch is not an installer transaction or clean-machine test.
- Local workspaces are plaintext for one trusted OS account, not encrypted multi-user databases.
  Directory admission refuses ordinary aliases but does not defeat a concurrent malicious OS owner.

## Why these limits are useful

The repository keeps the parser, policy, and retry decisions visible. Adding sockets, concurrency,
cryptography, and device compatibility at once would increase code while making the important
boundary invariants harder to inspect. Each omitted capability also has a clear extension seam.

## Responsible extension path

Before adding real communications:

1. define a licensed public protocol contract and compliance test vectors;
2. extend the existing bounded stream decoder with transport-specific deadlines and tests;
3. choose authenticated transport and peer identity requirements;
4. define per-operation authorization and immutable audit events;
5. bound trace retention and offline queues;
6. test concurrency, shutdown, reconnect storms, and partial I/O;
7. separate hardware tests from simulator CI; and
8. require engineering review before enabling any physical write.

## Claims intentionally not made

This project is not described as production-ready, safety-certified, secure, real-time, or compatible
with a device family. The repository demonstrates specific tested properties listed in
[testing.md](testing.md) and [validation-report.md](reports/validation-report.md).
