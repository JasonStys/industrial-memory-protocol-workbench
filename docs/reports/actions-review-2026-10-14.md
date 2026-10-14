# Actions maintenance review — 2026-10-14

Reviewed by Jason Stys. Failed run 38455320772 was a workflow configuration
failure, not a C++ test failure: CodeQL initialization was 4.38.3 while analysis
was 4.38.0. Both coordinated steps now use the official 4.38.3 commit. Dependabot
groups CodeQL updates and the repository gate rejects mixed or mutable versions.
Five independent regression tests cover matching, mixed, mutable, absent and
autobuild references. They pass locally; the policy and generated symbol index
also pass. Native C++, sanitizer, fuzz and CodeQL verification is performed by
the unchanged full CI gates, not inferred from the Python policy tests.

Historical run evidence is preserved in a private PC archive. This report does
not include account billing information, logs containing private data or keys.
The original failed run may no longer exist after an approved historical cleanup.
Accepted native source: 69feb6d052d20def34616a9355a345e3c88e9e10.
[CI 38639972382](https://github.com/JasonStys/industrial-memory-protocol-workbench/actions/runs/38639972382)
passed both Linux sanitizers/fuzzing and Windows MSVC lanes.
[CodeQL 38639972446](https://github.com/JasonStys/industrial-memory-protocol-workbench/actions/runs/38639972446)
passed at the same source. Generated Python bytecode is now ignored/excluded from
repository-policy enumeration; the five policy regressions and fresh symbol map
were rechecked after that maintenance-only adjustment. Final documentation commits
rerun the native gates. Approved cleanup can remove historical run URLs; metadata,
logs and artifacts remain in the private archive.

See [GitHub's grouped-update reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).
