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
Final workflow links will be recorded after native verification.

See [GitHub's grouped-update reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).
