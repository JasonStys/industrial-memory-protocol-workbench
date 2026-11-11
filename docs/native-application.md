# Native application and evidence workflow

Created by Jason Stys. This is the genuine offline GUI for the original IMLP/1 C++ client/server,
codec and stream decoder. It neither connects to industrial equipment nor executes supplied code.
The current portable packaging recipe targets Windows x64, with final patched Python 3.14.10 or
later 3.14 and a static-CRT MSVC engine. Source tests also exercise Linux and macOS.

## Use the full application

Keep the complete extracted `IndustrialMemoryWorkbench` folder together. Launch
`IndustrialMemoryWorkbench.exe`, choose an empty external workspace or this application's existing
workspace, then press **Open application**. The owner opens one new loopback listener on an
ephemeral port and launches your browser. It never attaches to an existing service. The random
session capability is removed from the URL and retained only in that browser tab's session storage.

Choose one of four workflows and edit its actual parameters:

1. **Session:** explicitly enable simulated writes if needed, set the inclusive write allowlist,
   set read attempts and edit the ordered operations. Addresses accept decimal or `0x` notation.
   The operation helper appends a read/write with an optional fault; the JSON editor also supports
   up to three faults per operation. The original server still enforces its own map permissions.
2. **Inspect:** type exact hexadecimal bytes or import a raw frame, including a malformed one.
   A completed blocked review is retained as blocked, never as an accepted frame.
3. **Compose:** edit version, opcode, flags, request ID, address, status and payload. The original
   codec decides whether those fields make a valid frame. Accepted frames can be downloaded.
4. **Stream:** supply ordered hexadecimal chunks or a raw file. Imported bytes are split into exact
   4096-byte chunks; you may edit those boundaries before running. An empty file becomes `[""]`.

Run the engine, inspect the result table and expand memory/trace or complete JSON. Download input
for repeatable experiments and full evidence for review. Search literal titles, filter workflow,
page in groups of 25 and reopen saved records. Imported evidence is input only: its result is rerun
through the actual engine, not trusted. Explicit deletion removes only the chosen saved record.

Keep the native owner open while work is active. **Exit owned application** or the native **Exit**
requests normal shutdown; the owner stays alive and holds its workspace lock until all HTTP handlers
and fixed C++ children have completed. It never converts a timeout into successful shutdown.
Browser-tab closure alone does not exit the application. Back up the stopped external workspace.

## Interpret uncertain results

A write is attempted once. A corrupted/truncated/wrong-ID acknowledgement may follow a completed
simulated write. The application labels that run for review; compare actual before/after bytes and
a subsequent read, rather than assuming an error prevented a mutation. Read retries reuse the same
logical request ID. Unconsumed queued faults carry to later operations; the trace makes this visible.

Stream offsets are zero-based offsets into concatenated exact input. Valid frame bytes, listed
discard extents and omitted-issue byte totals account for all input at EOF. Resynchronization is
diagnostic: a CRC-valid candidate is not proof of an authentic sender or message boundary.

## Boundaries and privacy

One trusted OS owner holds a plaintext workspace; there are no application accounts, tenant roles
or encryption against someone controlling that same account. Pre-mutation admission rejects
directory aliases, installation-root workspaces, and linked/replaced marker, lock or SQLite members.
It is not a race-proof namespace against a concurrent malicious same-account writer.

The HTTP boundary requires exact owned Host, random capability and mutation Origin; it refuses
cross-site requests, ambiguous/compressed/chunked bodies, duplicate JSON keys, non-finite values and
nesting beyond 64. It binds loopback only, with no CORS or external assets. It has eight connection
slots and four engine slots; excess work is refused instead of queued indefinitely.

Typed JSON and independent C++ IPC checks permit no shell, plugin, host endpoint or path parameter.
Each C++ child has a 15-second execution deadline and an 8 MiB result limit; source/version/digest,
input fingerprint, wire CRC and byte accounting are checked before saving. CRC is not authentication.
The engine itself is fixed trusted packaged code, not an untrusted executable supplied by a user.

The workspace holds at most 1000 records / 100 MiB. Capacity refusals preserve earlier history;
export and explicitly delete records instead of silent pruning. Application files remain immutable.

## Build and use a source checkout

Use Python 3.14.10+, Node 24, CMake 3.25+ and a C++20 compiler. Install development dependencies from
the exact hash locks into a dedicated environment, not a shared or global Python environment.

```powershell
python -m pip install --require-hashes -r requirements-dev.lock -r requirements-package.lock
npm --prefix web ci --ignore-scripts
npm --prefix web test
cmake -S . -B .runtime/cpp-app -A x64
cmake --build .runtime/cpp-app --config Release --parallel
ctest --test-dir .runtime/cpp-app -C Release --output-on-failure
python launcher.py
```

On Linux/macOS, omit `-A x64` and set `-DCMAKE_BUILD_TYPE=Release`. The source engine identity is
explicitly `development`. Build a clean Windows portable candidate with
`python -m tools.package_app --output-root .runtime/native-new`. The builder compiles a fresh
source-bound static-CRT C++ image, freezes the full GUI, preserves original vendor terms, safely
extracts its ZIP and runs the actual executable's editable GUI/restart acceptance before writing
its checksum. Existing output paths and dirty CI sources are refused. An explicit local
`--allow-dirty` candidate is labelled and is never accepted in CI.

Automated package acceptance uses `--no-window --no-browser` with a fresh synthetic workspace;
it proves the packaged browser/API/engine workflow, not a manual default-browser opener or OS
installer transaction. Separate real Tk tests exercise owner controls and completion-based shutdown.
