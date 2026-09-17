# Testing strategy

## Objectives

Testing concentrates on parser boundaries, full-range authorization, correlation, retry semantics,
and recovery behavior. Trivial accessors and standard-library behavior are not duplicated.

## Test pyramid

| Layer | Scope | Current evidence |
| --- | --- | --- |
| Unit | CRC, byte order, frame semantics, hex parsing, memory range/access rules | deterministic C++ tests |
| Component | server request handling, write policy, client response validation | deterministic C++ tests |
| Integration | client → loopback transport → server → memory map | normal and faulted tests plus CLI demo |
| Property | generated valid frames, CRC mutations, arbitrary bounded inputs | 22,000 deterministic cases per run |
| Fuzz | decoder, accepted-frame round trip, server boundary | bounded libFuzzer campaign in Linux CI |
| Static/dynamic analysis | CodeQL, compiler warnings, ASan, UBSan | GitHub workflows |
| Performance | encode → handle → decode cycle | five-sample release benchmark |

## Deterministic suite

The dependency-free test executable currently contains 20 named tests. It covers:

- the standard CRC-32 check value;
- field byte order and exact frame round trips;
- truncated, trailing, corrupt, unsupported, and oversized frames;
- invalid opcode/flags/status/payload relationships;
- memory-map region edges and unsigned overflow candidates;
- read-only default, write opt-in, and allowlist boundaries;
- successful client read and metrics;
- transient read timeout with the same correlation ID;
- write timeout with no retry;
- wrong request ID and corrupt response rejection; and
- argument validation before transport use.

Run it directly for named results:

```bash
./build/imlp-tests
```

Run it through CTest for automation and JUnit output:

```bash
ctest --test-dir build --output-on-failure --output-junit reports/cpp-tests.xml
```

## Property cases

Every deterministic run uses fixed seeds and performs:

- 10,000 semantically valid frame encode/decode equality checks;
- 2,000 single-bit CRC trailer mutations that must be rejected; and
- 10,000 arbitrary byte-vector decode attempts. Any accepted vector must re-encode byte-for-byte.

Fixed seeds make local and CI failures reproducible. Coverage-guided fuzzing complements rather than
replaces these stable properties.

## Fuzzing

The libFuzzer target feeds bounded arbitrary data to `decode()` and `MemoryServer::handle()`. When a
frame is accepted, the target requires encode/decode equality. CI uses Clang's matching libFuzzer
runtime with ASan and UBSan:

```bash
cmake -S . -B build-fuzz -G Ninja -DCMAKE_CXX_COMPILER=clang++ \
  -DIMLP_BUILD_FUZZER=ON -DIMLP_ENABLE_SANITIZERS=ON
cmake --build build-fuzz --parallel --target imlp-codec-fuzzer
./build-fuzz/imlp-codec-fuzzer -runs=10000 -max_len=556 -seed=20260916
```

This is a smoke campaign, not evidence that all parser states are explored. Longer fuzz runs and
corpus retention belong in a scheduled or dedicated environment.

## Cross-platform CI

- Linux: Clang formatting, warnings-as-errors, ASan, UBSan, tests, 10,000 fuzz runs, demo, policy,
  symbol-index check, and release benchmark.
- Windows: current hosted MSVC, `/W4 /WX /permissive-`, release tests, demo, policy, and index check.
- CodeQL: compiled C/C++ database with `security-extended` queries on pushes, pull requests, and a
  weekly schedule.

All external actions use full 40-character commit SHAs and workflows declare minimal permissions.

## Coverage targets

There is no percentage-only merge target. Required behavior targets are:

- every decoder rejection category has a deterministic test or fuzz reachability;
- every memory access policy boundary has an exact edge test;
- every client retry decision has a direct assertion; and
- every public operation appears in an end-to-end loopback path.

Future line/branch coverage should identify untested error paths, not substitute for these behavioral
requirements.

## Known test gaps

- There is no real socket adapter, packet fragmentation, or concurrent-client test.
- The trace collector is intentionally unbounded; load tests do not model retention pressure.
- The fuzz smoke run is bounded and starts without a persistent corpus.
- The simulator does not test authentication, encryption, or real device behavior.

These are design-scope limits, not hidden passing claims. See [limitations.md](limitations.md).

