# Known limitations

## Deliberate scope limits

- IMLP/1 is synthetic and has no commercial protocol compatibility.
- The transport is in-process; there is no TCP, UDP, serial, or fieldbus adapter.
- The codec accepts one exact complete frame, not fragmented or concatenated stream input.
- The simulator has one client, one thread, and one fixed 4 KiB address space.
- There is no encryption, authentication, authorization identity, replay protection, or key model.
- CRC-32 detects accidental corruption only.
- Trace retention is unbounded until the caller invokes `clear_trace()`.
- Error text is English and not localized.
- The benchmark measures an in-process encode/handle/decode path, not network latency.
- CI fuzzing is a bounded smoke campaign without a retained evolving corpus.

## Why these limits are useful

The repository keeps the parser, policy, and retry decisions visible. Adding sockets, concurrency,
cryptography, and device compatibility at once would increase code while making the important
boundary invariants harder to inspect. Each omitted capability also has a clear extension seam.

## Responsible extension path

Before adding real communications:

1. define a licensed public protocol contract and compliance test vectors;
2. add a bounded stream reassembler with fragmentation and timeout tests;
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

