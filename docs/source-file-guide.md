# Complete maintained file guide

Generated from Git tracked and proposed public files; ignored private runtimes are outside publication scope. Exact definitions and Python parameters/variables are in the [symbol index](generated/symbol-index.md).

| File | Purpose |
| --- | --- |
| [`.clang-format`](../.clang-format) | Product configuration, dependency identity or repository publication metadata. |
| [`.clang-tidy`](../.clang-tidy) | Product configuration, dependency identity or repository publication metadata. |
| [`.gitattributes`](../.gitattributes) | Product configuration, dependency identity or repository publication metadata. |
| [`.github/dependabot.yml`](../.github/dependabot.yml) | Product configuration, dependency identity or repository publication metadata. |
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | Pinned workflow for ci; see current validation report. |
| [`.github/workflows/codeql.yml`](../.github/workflows/codeql.yml) | Pinned workflow for codeql; see current validation report. |
| [`.github/workflows/native.yml`](../.github/workflows/native.yml) | Pinned workflow for native; see current validation report. |
| [`.gitignore`](../.gitignore) | Product configuration, dependency identity or repository publication metadata. |
| [`CMakeLists.txt`](../CMakeLists.txt) | Builds the protocol library, command-line tools, tests, benchmark, and optional fuzz target. |
| [`CMakePresets.json`](../CMakePresets.json) | Product configuration, dependency identity or repository publication metadata. |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | Contributing |
| [`LICENSE`](../LICENSE) | Product configuration, dependency identity or repository publication metadata. |
| [`README.md`](../README.md) | Industrial Memory Protocol Workbench |
| [`SECURITY.md`](../SECURITY.md) | Security policy |
| [`apps/benchmark_main.cpp`](../apps/benchmark_main.cpp) | Measures repeated encode, server-handle, and decode cycles with stable |
| [`apps/cli_main.cpp`](../apps/cli_main.cpp) | Provides safe inspection, read, explicit-write, and fault-demo |
| [`apps/studio_main.cpp`](../apps/studio_main.cpp) | Runs bounded offline editable sessions, exact-frame reviews and stream inspection. |
| [`docs/adr/0001-synthetic-protocol.md`](../docs/adr/0001-synthetic-protocol.md) | ADR 0001: Use an original synthetic protocol |
| [`docs/adr/0002-explicit-endianness.md`](../docs/adr/0002-explicit-endianness.md) | ADR 0002: Encode multi-byte fields explicitly |
| [`docs/adr/0003-retry-policy.md`](../docs/adr/0003-retry-policy.md) | ADR 0003: Retry reads, never retry writes implicitly |
| [`docs/architecture.md`](../docs/architecture.md) | Architecture |
| [`docs/big-o.md`](../docs/big-o.md) | Complexity and resource bounds |
| [`docs/cli.md`](../docs/cli.md) | CLI guide |
| [`docs/fault-catalog.md`](../docs/fault-catalog.md) | Fault catalog |
| [`docs/file-reference.md`](../docs/file-reference.md) | File reference |
| [`docs/generated/symbol-index.md`](../docs/generated/symbol-index.md) | Source symbol index |
| [`docs/handbook.md`](../docs/handbook.md) | Industrial Memory Protocol Workbench handbook |
| [`docs/limitations.md`](../docs/limitations.md) | Known limitations |
| [`docs/native-application.md`](../docs/native-application.md) | Native application and evidence workflow |
| [`docs/protocol-spec.md`](../docs/protocol-spec.md) | IMLP/1 protocol specification |
| [`docs/reports/actions-review-2026-10-14.md`](../docs/reports/actions-review-2026-10-14.md) | Actions maintenance review — 2026-10-14 |
| [`docs/reports/documentation-refresh-2026-11-09.md`](../docs/reports/documentation-refresh-2026-11-09.md) | Documentation refresh — 2026-11-09 |
| [`docs/reports/maintenance-audit-2026-09-18.md`](../docs/reports/maintenance-audit-2026-09-18.md) | Maintenance audit — 2026-09-18 |
| [`docs/reports/native-application-2026-11-11.md`](../docs/reports/native-application-2026-11-11.md) | Native application validation 11 November 2026 |
| [`docs/reports/portfolio-sync-2026-10-14.md`](../docs/reports/portfolio-sync-2026-10-14.md) | Portfolio synchronization — 2026-10-14 |
| [`docs/reports/portfolio-sync-2026-10-22.md`](../docs/reports/portfolio-sync-2026-10-22.md) | Portfolio synchronization — 2026-10-22 |
| [`docs/reports/project-guide.docx`](../docs/reports/project-guide.docx) | Historical reviewed Word edition; its publication manifest retains its own source scope. |
| [`docs/reports/publications.json`](../docs/reports/publications.json) | Product configuration, dependency identity or repository publication metadata. |
| [`docs/reports/stream-2026-11-09.md`](../docs/reports/stream-2026-11-09.md) | Stream inspector validation â€” November 9, 2026 |
| [`docs/reports/validation-report.md`](../docs/reports/validation-report.md) | Validation report |
| [`docs/safety-and-security.md`](../docs/safety-and-security.md) | Safety and security model |
| [`docs/source-file-guide.md`](../docs/source-file-guide.md) | Complete maintained file guide |
| [`docs/sources.md`](../docs/sources.md) | Primary sources |
| [`docs/stream-inspection.md`](../docs/stream-inspection.md) | Fragmented stream inspection workflow |
| [`docs/testing.md`](../docs/testing.md) | Testing strategy |
| [`fuzz/codec_fuzzer.cpp`](../fuzz/codec_fuzzer.cpp) | Feeds arbitrary bounded bytes through the decoder, round trip, and |
| [`imlp_studio/__init__.py`](../imlp_studio/__init__.py) | Identifies Jason Stys's local educational native studio. |
| [`imlp_studio/desktop.py`](../imlp_studio/desktop.py) | Owns the native workspace chooser, browser and normally drained loopback application. |
| [`imlp_studio/domain.py`](../imlp_studio/domain.py) | Validate closed editable simulator requests and encode bounded native IPC by Jason Stys. |
| [`imlp_studio/engine.py`](../imlp_studio/engine.py) | Invoke only the fixed original C++ engines and verify source-bound evidence by Jason Stys. |
| [`imlp_studio/private_io.py`](../imlp_studio/private_io.py) | Read actual ordinary application resources with descriptor-bound byte limits. |
| [`imlp_studio/profile_paths.py`](../imlp_studio/profile_paths.py) | Admits Jason Stys's native workspace paths before mutation. |
| [`imlp_studio/resources.py`](../imlp_studio/resources.py) | Binds native application resources to one product/version/source before private writes. |
| [`imlp_studio/server.py`](../imlp_studio/server.py) | Serves the actual protocol editor and fixed engine API on one owned loopback listener. |
| [`imlp_studio/store.py`](../imlp_studio/store.py) | Retains reproducible input and actual C++ evidence in a private single-owner workspace. |
| [`include/imlp/client.hpp`](../include/imlp/client.hpp) | Declares the correlation-aware client, bounded read retry policy, and |
| [`include/imlp/codec.hpp`](../include/imlp/codec.hpp) | Declares bounded big-endian encoding, decoding, CRC-32, and |
| [`include/imlp/memory_map.hpp`](../include/imlp/memory_map.hpp) | Declares a bounded simulator memory map with explicit |
| [`include/imlp/server.hpp`](../include/imlp/server.hpp) | Declares the protocol simulator and its defense-in-depth write policy. |
| [`include/imlp/stream_decoder.hpp`](../include/imlp/stream_decoder.hpp) | Declares bounded synthetic stream reassembly and corruption-offset diagnostics by Jason |
| [`include/imlp/transport.hpp`](../include/imlp/transport.hpp) | Declares an injectable transport and deterministic loopback fault |
| [`include/imlp/types.hpp`](../include/imlp/types.hpp) | Defines fixed-width wire types, protocol limits, frames, and error |
| [`launcher.py`](../launcher.py) | Starts Jason Stys's complete native application. Locations: docs/generated/symbol-index.md.""" |
| [`licenses/MSVC-STL-LICENSE.txt`](../licenses/MSVC-STL-LICENSE.txt) | Original upstream component terms retained verbatim; not authored application code. |
| [`licenses/PYTHON.txt`](../licenses/PYTHON.txt) | Original upstream component terms retained verbatim; not authored application code. |
| [`licenses/TCL-9.0.4.txt`](../licenses/TCL-9.0.4.txt) | Original upstream component terms retained verbatim; not authored application code. |
| [`licenses/TK-9.0.4.txt`](../licenses/TK-9.0.4.txt) | Original upstream component terms retained verbatim; not authored application code. |
| [`licenses/TK-9.0.5-pre-33904f039f48ed64.txt`](../licenses/TK-9.0.5-pre-33904f039f48ed64.txt) | Original upstream component terms retained verbatim; not authored application code. |
| [`pyproject.toml`](../pyproject.toml) | Product configuration, dependency identity or repository publication metadata. |
| [`reports/performance.json`](../reports/performance.json) | Product configuration, dependency identity or repository publication metadata. |
| [`reports/repository-validation.json`](../reports/repository-validation.json) | Product configuration, dependency identity or repository publication metadata. |
| [`reports/test-summary.json`](../reports/test-summary.json) | Product configuration, dependency identity or repository publication metadata. |
| [`requirements-dev.in`](../requirements-dev.in) | Exact dependency input/hash lock for isolated runtime, test or packaging tools. |
| [`requirements-dev.lock`](../requirements-dev.lock) | Exact dependency input/hash lock for isolated runtime, test or packaging tools. |
| [`requirements-package.in`](../requirements-package.in) | Exact dependency input/hash lock for isolated runtime, test or packaging tools. |
| [`requirements-package.lock`](../requirements-package.lock) | Exact dependency input/hash lock for isolated runtime, test or packaging tools. |
| [`requirements.lock`](../requirements.lock) | Exact dependency input/hash lock for isolated runtime, test or packaging tools. |
| [`scripts/check_repository.py`](../scripts/check_repository.py) | Enforces public boundaries, source headers, required docs and immutable action pins. |
| [`scripts/generate_symbol_index.py`](../scripts/generate_symbol_index.py) | Generates reproducible source declaration links for file-header documentation. |
| [`scripts/publication_text.py`](../scripts/publication_text.py) | Jason Stys: inspect only named reviewed Office editions without hiding their XML. |
| [`scripts/test_workflow_policy.py`](../scripts/test_workflow_policy.py) | Regressions for mixed CodeQL versions that caused a real PR failure. |
| [`scripts/validate.sh`](../scripts/validate.sh) | Runs the portable configure, build, test, demo, index, and repository-policy checks. |
| [`src/client.cpp`](../src/client.cpp) | Implements bounded read retries, single-attempt writes, and response |
| [`src/codec.cpp`](../src/codec.cpp) | Implements defensive frame validation and explicit big-endian |
| [`src/memory_map.cpp`](../src/memory_map.cpp) | Implements overflow-safe range checks and simulator access controls. |
| [`src/server.cpp`](../src/server.cpp) | Implements the synthetic simulator's read, opt-in write, and error |
| [`src/stream_decoder.cpp`](../src/stream_decoder.cpp) | Implements bounded fragmented-stream diagnostics for synthetic IMLP/1 by Jason Stys. |
| [`src/transport.cpp`](../src/transport.cpp) | Implements bounded loopback exchanges, trace capture, and scripted |
| [`tests/conftest.py`](../tests/conftest.py) | Actual C++/SQLite/loopback fixtures with isolated workspaces by Jason Stys. |
| [`tests/runtime_notice_cases.py`](../tests/runtime_notice_cases.py) | Authored source with definitions and variables in the exact symbol index. |
| [`tests/test_client.cpp`](../tests/test_client.cpp) | Verifies retry, no-retry, correlation, malformed response, and |
| [`tests/test_codec.cpp`](../tests/test_codec.cpp) | Verifies CRC, byte order, frame semantics, corruption handling, and |
| [`tests/test_harness.hpp`](../tests/test_harness.hpp) | Supplies a dependency-free test registry and assertion helpers for the |
| [`tests/test_main.cpp`](../tests/test_main.cpp) | Runs the registered test suite and prints a compact deterministic |
| [`tests/test_memory.cpp`](../tests/test_memory.cpp) | Verifies memory-region boundaries, server write policy, and |
| [`tests/test_native_packaging.py`](../tests/test_native_packaging.py) | Independent version/source/dirty-policy contracts without freezing code by Jason Stys. |
| [`tests/test_native_resources.py`](../tests/test_native_resources.py) | Exact frozen identity/static-resource and actual growth refusals by Jason Stys. |
| [`tests/test_owner_window.py`](../tests/test_owner_window.py) | Authored source with definitions and variables in the exact symbol index. |
| [`tests/test_portable_archive.py`](../tests/test_portable_archive.py) | Authored source with definitions and variables in the exact symbol index. |
| [`tests/test_profile_paths.py`](../tests/test_profile_paths.py) | Reject real aliases/program trees before writes. Locations: docs/generated/symbol-index.md. |
| [`tests/test_properties.cpp`](../tests/test_properties.cpp) | Exercises thousands of generated frames, checksum mutations, and |
| [`tests/test_publication_text.py`](../tests/test_publication_text.py) | Jason Stys: actual Office ZIP fixtures retain text scanning and reject unknown content. |
| [`tests/test_repository_policy.py`](../tests/test_repository_policy.py) | Real Git/publication/index regressions preserve original public gates by Jason Stys. |
| [`tests/test_runtime_notices.py`](../tests/test_runtime_notices.py) | Authored source with definitions and variables in the exact symbol index. |
| [`tests/test_stream.cpp`](../tests/test_stream.cpp) | Tests independent fragmented/coalesced stream, corruption, EOF and resource-bound oracles |
| [`tests/test_stream_cli.py`](../tests/test_stream_cli.py) | Actual synthetic CLI with independent Python struct/CRC golden bytes. Created by Jason Stys. |
| [`tests/test_studio_boundaries.py`](../tests/test_studio_boundaries.py) | Independent malformed-child, resource, IPC and store contract negatives by Jason Stys. |
| [`tests/test_studio_cli.py`](../tests/test_studio_cli.py) | Independent real C++ studio IPC, IEEE-CRC and stateful simulator oracles by Jason Stys. |
| [`tests/test_studio_service.py`](../tests/test_studio_service.py) | Real original C++ session/codec/stream workflows with independent struct/CRC oracles. |
| [`tools/native_feature_smoke.mjs`](../tools/native_feature_smoke.mjs) | Actual editable compiled-app Chromium journeys with independent wire oracles by Jason Stys. |
| [`tools/package_app.py`](../tools/package_app.py) | Build and exercise the actual C++/TypeScript/Python Windows portable app by Jason Stys. |
| [`tools/portable_archive.py`](../tools/portable_archive.py) | Bounded portable archive creation and fresh extraction by Jason Stys. |
| [`tools/runtime_notices.py`](../tools/runtime_notices.py) | Collect real runtime license notices by Jason Stys, including DLL-embedded Tcl/Tk9 |
| [`tools/smoke_app.py`](../tools/smoke_app.py) | Launch only the supplied extracted native executable and check real UI/persistence. |
| [`tools/smoke_source.py`](../tools/smoke_source.py) | Explicitly exercise the source app with the same actual GUI/domain oracles. |
| [`web/package-lock.json`](../web/package-lock.json) | Product configuration, dependency identity or repository publication metadata. |
| [`web/package.json`](../web/package.json) | Product configuration, dependency identity or repository publication metadata. |
| [`web/public/index.html`](../web/public/index.html) | Genuine offline C++ protocol workbench by Jason Stys. Symbol locations: docs/generated/symbol-index.md. --> |
| [`web/scripts/build.mjs`](../web/scripts/build.mjs) | Authored source with definitions and variables in the exact symbol index. |
| [`web/scripts/check_browser_host.mjs`](../web/scripts/check_browser_host.mjs) | Authored source with definitions and variables in the exact symbol index. |
| [`web/scripts/clean.mjs`](../web/scripts/clean.mjs) | Authored source with definitions and variables in the exact symbol index. |
| [`web/src/app.ts`](../web/src/app.ts) | Editable original-engine sessions, byte review and durable evidence UI by Jason Stys. |
| [`web/src/model.ts`](../web/src/model.ts) | Bounded editable protocol input and exact interchange by Jason Stys. |
| [`web/src/styles.css`](../web/src/styles.css) | Authored source with definitions and variables in the exact symbol index. |
| [`web/tests/model.test.ts`](../web/tests/model.test.ts) | Independent UI interchange/byte/number boundary oracles by Jason Stys. |
| [`web/tsconfig.json`](../web/tsconfig.json) | Product configuration, dependency identity or repository publication metadata. |
