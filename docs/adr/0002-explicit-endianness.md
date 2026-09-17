# ADR 0002: Encode multi-byte fields explicitly

- Status: accepted
- Date: 2026-09-16

## Context

Copying packed C++ structures onto the wire can depend on host byte order, padding, alignment, enum
representation, and compiler behavior. Untrusted lengths also make unchecked casts dangerous.

## Decision

Use fixed-width unsigned logical fields and explicit shift/mask functions for big-endian wire values.
Decode from `std::span<const std::byte>`, validate header length before reading fields, and copy only the
bounded payload into an owned vector. Never use `reinterpret_cast` to map a frame structure.

## Consequences

- Wire output is stable across MSVC, Clang, x86-64, and other host byte orders.
- Field handling is slightly more verbose but directly testable.
- The compiler cannot silently insert wire padding.
- Fuzzing reaches validation decisions without undefined unaligned structure reads.

