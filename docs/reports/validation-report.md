# Validation report

## Scope

This report records repeatable evidence for the synthetic simulator, codec, client, CLI, and repository
automation. It does not make hardware compatibility, network security, or safety-certification claims.

## Local environment

- Date: 2026-09-16
- OS: Windows
- Compiler: Microsoft C/C++ 19.51
- Language mode: C++20
- Build policy: `/W4 /WX /permissive- /Zc:__cplusplus /utf-8`
- Build type for correctness tests: Debug
- Build type for benchmark: Release

## Results

| Check | Result |
| --- | --- |
| Configure and warnings-as-errors build | Passed |
| CTest | 1/1 test executable passed |
| Named deterministic tests | 20/20 passed |
| Valid generated frame round trips | 10,000/10,000 passed |
| CRC mutation rejections | 2,000/2,000 passed |
| Arbitrary bounded inputs | 10,000 completed; every accepted frame re-encoded exactly |
| Read-only default demo | Passed; write returned `write_disabled` |
| Timeout recovery demo | Passed; read succeeded on attempt 2 |
| Corrupt response demo | Passed; client returned `checksum_mismatch` |
| Explicit write/readback demo | Passed |
| Release benchmark | Median 770,033.974 encode/handle/decode operations per second |
| Local clang-tidy selected checks | Passed with warnings treated as errors |
| Generated source symbol index | Generated and checked for exact line links |
| Repository policy | Required before commit and in Linux/Windows CI |
| Linux ASan/UBSan and bounded libFuzzer | Enforced by public CI |
| Windows MSVC | Enforced by public CI |
| CodeQL `security-extended` | Enforced by public CodeQL workflow |

The public CI badges and run history are the source of truth for remote platform results on each
commit. CI artifacts retain JUnit, repository-policy JSON, and a fresh release benchmark for 14 days.

## Test inventory

The named test list is produced by `imlp-tests` and grouped into:

- six client/retry/correlation tests;
- six codec/CRC/hex tests;
- five memory/server/access-policy tests; and
- three deterministic property tests.

## Performance method

`imlp-benchmark` runs five samples of 50,000 in-process read cycles. Each cycle constructs a frame,
encodes it, routes it through `MemoryServer`, decodes the response, and updates a checksum so work is
observable. The report uses the median sample. It excludes sockets, operating-system scheduling,
encryption, and physical-device latency.

The checked-in numeric result is in `reports/performance.json`. Performance is descriptive, not a
real-time guarantee or CI pass threshold.

## Residual limitations

The important remaining gaps are real stream transport, partial I/O, concurrency, authenticated
transport, bounded long-running trace retention, persistent fuzz corpora, and hardware-specific test
vectors. See [limitations.md](../limitations.md).
