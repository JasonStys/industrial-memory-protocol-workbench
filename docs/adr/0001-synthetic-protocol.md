# ADR 0001: Use an original synthetic protocol

- Status: accepted
- Date: 2026-09-16

## Context

The project needs realistic framing, byte-order, memory-map, timeout, permission, and parser problems
without redistributing protected material or implying compatibility with a commercial product.

## Decision

Define IMLP/1 specifically for this repository. Publish the complete small specification, test vector,
memory regions, and unsupported-capability statement. Do not use vendor identifiers, packet formats,
SDK code, manuals, or logos.

## Consequences

- Every byte and invariant can be documented and tested publicly.
- The project demonstrates protocol-engineering methods, not reverse engineering.
- It cannot be used to communicate with existing equipment.
- Any future adapter must live behind a separately licensed, documented interface and must not weaken
  the simulator's safe defaults.

