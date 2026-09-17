# Primary sources

These sources informed coding, testing, security, and CI choices. They do not define IMLP/1; that
protocol is original to this repository.

## C++ and build engineering

- [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines) — static type
  safety, resource safety, bounds, interfaces, and error-handling principles.
- [CMake command-line documentation](https://cmake.org/cmake/help/latest/manual/cmake.1.html) — configure,
  build, test, and workflow-preset behavior.
- [CTest documentation](https://cmake.org/cmake/help/latest/manual/ctest.1.html) — portable test execution
  and JUnit reporting.

## Parser and fuzz testing

- [LLVM libFuzzer documentation](https://llvm.org/docs/LibFuzzer.html) — matching Clang runtime,
  coverage-guided fuzz entry point, corpus behavior, and sanitizer combinations.
- [Clang AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html) — dynamic memory-error
  detection.
- [Clang UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html) —
  undefined-behavior checks.
- [SEI CERT INT08-C](https://wiki.sei.cmu.edu/confluence/x/QtcxBQ) — verifying integer values and
  avoiding overflow-dependent validation.
- [RFC 1952](https://www.rfc-editor.org/rfc/rfc1952) — documented CRC-32 polynomial and reference
  algorithm used for the corruption-detection check value.

## Security and automation

- [NIST SP 800-82 Rev. 3](https://csrc.nist.gov/pubs/sp/800/82/r3/final) — operational technology
  security guidance that accounts for performance, reliability, and safety requirements.
- [GitHub CodeQL for compiled languages](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-for-compiled-languages) — C/C++ database build modes and analysis.
- [GitHub Actions security guidance](https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats) — least privilege and immutable action references.

Sources were reviewed on 2026-09-16. The workflow pins action implementations to full commit SHAs,
while this list uses stable documentation URLs so readers can check current guidance.

