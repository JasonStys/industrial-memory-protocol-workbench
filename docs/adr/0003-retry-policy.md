# ADR 0003: Retry reads, never retry writes implicitly

- Status: accepted
- Date: 2026-09-16

## Context

A timeout or disconnect does not reveal whether a peer applied a request. Retrying every operation can
duplicate a state-changing effect. Never retrying makes transient read failures unnecessarily brittle.

## Decision

Allow a configurable, bounded number of attempts for reads when the transport reports timeout,
disconnect, or not-connected. Reuse the same encoded frame and correlation ID. Give writes exactly one
transport attempt and return an explicit ambiguous failure when the response is lost.

## Consequences

- Side-effect-free reads recover from one transient failure by default.
- Packet traces associate retry attempts with one logical operation.
- Callers must reconcile write state before choosing to issue another write.
- A future protocol could safely retry writes only after defining and persisting idempotency semantics.

