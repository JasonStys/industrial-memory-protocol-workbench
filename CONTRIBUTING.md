# Contributing

## Change workflow

1. Keep IMLP/1 synthetic and fully documented; do not add non-public protocol material.
2. Add or update a test before changing a boundary, retry, access, or status rule.
3. Run formatting and the validation workflow.
4. Regenerate the symbol index after source-line changes.
5. Update the protocol spec, fault catalog, limitations, and validation evidence when behavior changes.

## Local checks

```bash
clang-format -i include/imlp/*.hpp src/*.cpp apps/*.cpp tests/*.cpp tests/*.hpp fuzz/*.cpp
python3 scripts/generate_symbol_index.py
./scripts/validate.sh
```

Windows developers can use the commands in the README and then run:

```powershell
python scripts\generate_symbol_index.py
python scripts\check_repository.py
```

## Code expectations

- C++20, RAII ownership, fixed-width wire integers, and no raw owning pointers.
- Validate complete ranges before indexing or copying.
- Keep writes read-only by default and enforce policy below presentation code.
- Do not add implicit write retries.
- Public functions, classes, tests, scripts, and files require concise intent comments.
- File headers must reference the generated symbol index for exact declaration locations.
- Avoid claims such as secure, real-time, compatible, or production-ready without defined evidence.

## Pull requests

Explain the boundary being changed, failure behavior, tests added, resource implications, and any
documentation update. CI must pass on Linux and Windows, and CodeQL must complete without a new alert.

