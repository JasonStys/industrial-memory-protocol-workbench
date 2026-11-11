# Native application validation 11 November 2026

Author: Jason Stys. This report covers the new source candidate for the real version 1.1.0
Windows desktop application. Historical Word editions and earlier benchmark/security reports
retain their own source baselines. Hosted exact-head and later full-main checks are separate
from the local observations below and must pass before distribution.

## Practical change and rationale

The original project had independently testable C++ protocol engines and per-invocation CLI tools.
The new desktop app exposes those same engines through actual editable sessions, exact-frame and
fragmented-stream workflows, supported binary/JSON imports, result views, durable local history,
search and complete exports. It creates no real device adapter or substitute demo executable.

One C++ server now persists across ordered operations within one run, allowing a useful failure
investigation: a corrupted write response is rejected, but the simulator's memory did change and a
later read returns those exact bytes. The app labels this as review rather than inventing a failed
write/no-effect claim. Read retries keep the logical ID; writes remain single-attempt.

## Local source observations

| Check                     | Observed result                                                                                      | Scope                                                                                |
| ------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Original C++ engine tests | 24 passed; 22,000 deterministic property cases retained                                              | Actual MSVC warnings-as-errors build                                                 |
| CTest integration         | 3 targets passed                                                                                     | Original test binary, original stream CLI, new 7-case actual studio IPC suite        |
| Original benchmark        | Five samples; median 59.904 ms for50,000 operations                                                  | Local in-process observation, not network latency or comparative performance claim   |
| Native Python             | 197 parent tests passed; 95.35% combined whole-package coverage                                      | Includes real HTTP/C++/SQLite/Tk and malformed-output negatives; 90% floor unchanged |
| Tcl notice fixture        | 13 real cases in a fresh interpreter                                                                 | Mandatory wrapper propagates failure; not 13 extra parent tests                      |
| TypeScript                | 5 tests passed                                                                                       | Independent byte/numeric/UTF-8 and interchange bounds                                |
| Actual browser            | Source and first labelled local frozen candidate passed editable imports/exports and normal shutdown | Exact outcome assertions, not just root/assets HTTP probes                           |
| Native resources          | Actual Python3.14.10 DLL and original MSVC STL/runtime notices retained                              | Source/version/digest identity and safe ZIP extraction                               |

The first frozen candidate was explicitly `sourceDirty:true`, for local preflight only. It is not
an immutable published release or installed application. A clean committed build and exact-head
hosted checks remain required. The native consumer also now adds a selected-record deletion and
oversized binary refusal; final accepted counts are recorded by the corresponding current run,
not inferred from the earlier candidate.

## First hosted observations and corrections

The first PR source `f8f9a0094969305baaf233c258a2ade4bb369598` compiled under Linux but its original
clang-tidy gate flagged an optional dereference after an indirectly derived accepted flag. The
bridge now explicitly checks `has_value()` in the decode branch before checked access. Original
valid, CRC-corrupt and truncated actual-CLI/IPC oracles remain unchanged; no warning was suppressed.

All four first processed CodeQL analyses had zero raw results, errors and warnings, but the PR
aggregate was neutral because converting the original C++ job into a matrix removed its previous
main-comparable environment/category. The workflow now retains the original nonmatrix `analyze`
C++ manual build and default category, adding the other three languages in a separate job. A
configuration-identity regression and actual actionlint validation protect that distinction; a
neutral comparison warning is not reported as successful full-main clearance.

The prior clean local source built ZIP SHA256
`96ab9ee1c66e42ed7f0681becd92c99546a8331fba4267e8459c97ec67181a59` and completed actual extracted
GUI, eight retained records, selected deletion, oversized-file refusal and two normal exits.
That immutable local observation remains distinct from later corrected source and its hosted gates.

The corrected local source suite passed 198 parent tests with the same95.35% combined coverage and
the unchanged90% floor. One intermediate run exposed a Tk-variable deallocator warning during a
later Windows subprocess-I/O collection. The owner fixture now releases its actual Tcl variables
on their creating thread after its assertions. Unraisable-finalizer warnings are treated as errors;
the subsequent complete198-test run passed without a warning. No warning filter or case was skipped.

## Independent numerical and negative oracles

Python `struct` and `zlib.crc32` construct the expected wire layout independently of product codecs;
the native browser suite uses its own IEEE-CRC loop and explicit field offsets. Expected write/read
payload `1a0d0a007fff` includes DOS EOF, CR/LF, NUL and high bytes. Actual stdin is set to binary on
Windows, so these bytes cannot be silently truncated or translated.

Tests retain real before/after memory and inspect read retry IDs, fault carryover, permission gates,
unknown fields/commands, noninteger/negative/overflow arguments, malformed/odd/oversized hex,
corrupt/truncated frames, stream offsets, partial EOF and complete byte accounting. Forged result
imports rerun actual input instead of adopting their success labels. Malformed/timeout/nonzero
children and full-history refusals cannot create success records or silently prune old evidence.

Actual filesystem tests cover junction/symlink ancestors, frozen installation roots, fixed marker/
lock/SQLite hardlinks and replacement identity. Owned close tests hold a real operation and verify
that the listener/workspace remain owned until completion. Unknown workspaces and future database
schemas are refused without reset or migration. Real Git fixtures keep ignored private runtime
data outside publication while still checking proposed files and force-tracked ignored files.
Named historical Office editions remain bounded XML/relationship inputs to the original text scan;
unknown binary files, macros and embedded objects are refused rather than broadly skipped.

## Workflow and distribution boundaries

Original Linux ASan/UBSan, clang-tidy,10,000-run libFuzzer,22,000 property cases and benchmark lanes
remain. New three-OS native-source lanes build actual C++, then execute Python/Tk/SQLite/HTTP tests
and the unchanged90% floor. Windows packaging drives the extracted executable and validates a real
second launch/history. No default full-binary artifact upload is introduced.

CodeQL retains a real manual compiled C/C++ build and adds supported Python, JavaScript/TypeScript
and Actions `security-extended` lanes with coordinated immutable pins, read-only checkout and
job-only security upload permission. No query exclusions, suppressions, ignored failures, privileged
PR triggers or live controls were added. PR scans are diff-informed; a successful PR is not a claim
of full-main zero results. Actual processed analyses and original workflow results must be checked.

The package is an unsigned portable Windows x64 folder, not an OS installer. Automation uses
`--no-window --no-browser`; separate source Tk tests cover real owner controls. Manual frozen
default-browser opening and clean-machine installation remain unverified unless separately recorded.
No Linux/macOS distributable, industrial compatibility, physical I/O, malicious same-account race
defense, encrypted workspace or absence of all future defects is claimed.
