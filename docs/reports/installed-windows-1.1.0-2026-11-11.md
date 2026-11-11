# Installed Windows 1.1.0 validation

By Jason Stys. 11 November 2026.

These observations describe the independently downloaded, published **1.1.0** application built from `a70fe14ab0f94ce21e4b6f271be551a8618f8ffa`. Earlier Office editions, failed-run evidence and releases remain unchanged.

## Purpose and practical improvements

Build and inspect synthetic memory-protocol frames, run ordered read and write sessions on one simulated memory server, and account for accepted frames, discarded bytes and incomplete input across arbitrary stream chunks.

The original C++20 codec, memory server, client and loopback transport remain the domain engine. The app adds editable sessions and streams, explicit write permission, real retry and fault evidence, exact frame exports, searchable retained history and completion-aware import handling.

## Observed validation

**Actual app and restart: Passed.** Ten actual executions passed; eight records remained after two explicit test deletions. Exact evidence and raw-frame exports, two normal exits and restart were verified.

**Original domain gates: Passed.** 198 Python tests plus 13 isolated Tcl cases, 24 C++ tests, 22000 properties, three CTest groups and five TypeScript tests passed; original sanitizers, fuzzing and benchmarks remain separate hosted gates.

**Distribution and security: Passed.** All five release files matched provider hashes and all 82 installed files stayed unchanged. Three main workflows and four actual raw CodeQL categories passed before publication.

## Illustrated use and implementation

The [four-page guide](windows-application-guide-1.1.0.docx) contains two actual installed-app screenshots, a worked user journey, an immutable source-code excerpt and operating limits. The [review manifest](windows-application-guide-1.1.0.json) binds exact Word, image, source and individually inspected page identities. Prepared cases are inputs inside the actual application, never separate demonstration apps.

## Installation and limits

Extract the complete checksummed Windows x64 archive and keep all original runtime notices. Launch IndustrialMemoryWorkbench.exe or the individual Desktop icon; Python 3.14.10, Tcl and Tk 9.0.4 and the fixed C++ engine are bundled.

The native owner window opens a separate local plaintext workspace. Use Help for the exact schemas and limits. Automated acceptance used separate synthetic profiles and does not prove a clean-machine installer transaction.

IMLP/1 is a synthetic protocol, with no commercial-device compatibility or physical I/O claim. CRC detects accidental corruption and is not authentication.

Write permission applies only to simulated memory. The simulated protocol has no hardware connections, external network transport, arbitrary submitted programs or production enforcement. The desktop browser uses an owned local HTTP service. Protect owner-local plaintext profiles and exports.

Individual shortcut targets were read-back verified. Actual installed-executable acceptance is separate from ordinary default-profile shortcut activation, which was not independently exercised. Only synthetic inputs and isolated outputs were used; normal user data and Docker were not opened or changed. This documentation commit requires its own original hosted checks and processed security analyses; prior runtime evidence does not certify later source changes.
