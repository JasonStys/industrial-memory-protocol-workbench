# File reference

## Root configuration

| File | Responsibility |
| --- | --- |
| `CMakeLists.txt` | Defines library, CLI, benchmark, tests, fuzz target, warnings, and instrumentation. |
| `CMakePresets.json` | Provides repeatable debug, release, and validation presets. |
| `.clang-format` | Enforces the C++ formatting contract. |
| `.clang-tidy` | Selects high-signal local static-analysis checks. |
| `.gitignore` | Excludes local build and analysis output. |
| `LICENSE` | MIT license text. |
| `CONTRIBUTING.md` | Change workflow, test expectations, and documentation rules. |
| `SECURITY.md` | Private vulnerability reporting and scope guidance. |

## Public library

| File | Responsibility |
| --- | --- |
| `include/imlp/types.hpp` | Protocol constants, fixed-width enums, frame, and codec result types. |
| `include/imlp/codec.hpp` | Codec, CRC-32, and hexadecimal conversion API. |
| `include/imlp/memory_map.hpp` | Fixed memory map and access-region contract. |
| `include/imlp/server.hpp` | Simulator policy, observable event, and request handler API. |
| `include/imlp/transport.hpp` | Transport interface, fault types, trace model, and loopback adapter. |
| `include/imlp/client.hpp` | Client errors, options, metrics, results, and operations. |

## Implementations and applications

| File | Responsibility |
| --- | --- |
| `src/codec.cpp` | Explicit endian conversion, semantic validation, CRC, and hex implementation. |
| `src/memory_map.cpp` | Overflow-safe range checks, initial identity data, reads, and writes. |
| `src/server.cpp` | Request dispatch, write policy, memory access, and bounded responses. |
| `src/transport.cpp` | Connection state, fault consumption, response mutation, and packet trace. |
| `src/client.cpp` | Request IDs, read retry, single write attempt, metrics, and correlation checks. |
| `apps/cli_main.cpp` | Inspector, test-vector generator, simulator operations, and demonstration. |
| `apps/benchmark_main.cpp` | Five-sample in-process protocol throughput measurement. |
| `fuzz/codec_fuzzer.cpp` | Decoder/server fuzz entry point and accepted-frame round-trip invariant. |

## Tests

| File | Responsibility |
| --- | --- |
| `tests/test_harness.hpp` | Dependency-free registry and assertions. |
| `tests/test_main.cpp` | Test runner and deterministic summary. |
| `tests/test_codec.cpp` | Wire format, CRC, malformed frame, semantic, and hex tests. |
| `tests/test_memory.cpp` | Address regions, range safety, write policy, and server tests. |
| `tests/test_client.cpp` | Retry, no-retry, fault, correlation, and argument tests. |
| `tests/test_properties.cpp` | Generated-frame, mutation, and arbitrary-input properties. |

## Automation

| File | Responsibility |
| --- | --- |
| `scripts/validate.sh` | Portable configure/build/test/demo/policy workflow. |
| `scripts/check_repository.py` | Required docs, headers, protected references, and action-pin policy. |
| `scripts/generate_symbol_index.py` | Exact declaration-line index generation and freshness check. |
| `.github/workflows/ci.yml` | Linux sanitizers/fuzzing and Windows MSVC validation. |
| `.github/workflows/codeql.yml` | Compiled C++ CodeQL analysis. |
| `.github/dependabot.yml` | Weekly GitHub Actions update proposals. |

## Documentation and evidence

| File | Responsibility |
| --- | --- |
| `README.md` | Portfolio entry point, quickstart, capability summary, evidence, and repository map. |
| `docs/architecture.md` | Components, data flow, trust boundaries, state, and resource ownership. |
| `docs/protocol-spec.md` | Complete original wire format, opcodes, statuses, regions, and test vector. |
| `docs/cli.md` | Commands, examples, safety boundary, and exit codes. |
| `docs/fault-catalog.md` | Injected failure behavior, retry expectations, and trace interpretation. |
| `docs/testing.md` | Test pyramid, cases, fuzz command, CI matrix, targets, and gaps. |
| `docs/safety-and-security.md` | Assets, controls, write-defense layers, and non-claims. |
| `docs/big-o.md` | Time/space costs, data-structure choices, and bounded/unbounded state. |
| `docs/limitations.md` | Deliberate exclusions, responsible extension path, and claim boundaries. |
| `docs/sources.md` | Official C++, build, fuzzing, security, and automation references. |
| `docs/adr/0001-synthetic-protocol.md` | Decision to use an original educational protocol. |
| `docs/adr/0002-explicit-endianness.md` | Decision to avoid packed host structures on the wire. |
| `docs/adr/0003-retry-policy.md` | Decision to retry reads but never writes implicitly. |
| `docs/generated/symbol-index.md` | Generated exact line links for source declarations and tests. |
| `docs/reports/validation-report.md` | Human-readable environment, results, method, and residual gaps. |
| `reports/test-summary.json` | Machine-readable deterministic/property/demo result counts. |
| `reports/performance.json` | Machine-readable local release benchmark and scope note. |
| `reports/repository-validation.json` | Machine-readable documentation/header/action-pin policy result. |
