# Industrial Memory Protocol Workbench handbook

By Jason Stys.

Reassemble fragmented/coalesced frames in a bounded ring with corruption, discarded-byte and EOF offsets plus read-only JSON inspection.

Models realistic stream transport boundaries instead of assuming one read equals one complete message.

## Read the documentation

| Edition | Audience and contents |
| --- | --- |
| [project-guide.docx](reports/project-guide.docx) | User and developer guide: purpose, current usage, design, boundaries and source references. |

The editable Markdown remains the maintenance source. The Word files are readable editions, and the workbook is an evidence index rather than a test runner. See [publication identities and review](reports/publications.json) and the [documentation refresh record](reports/documentation-refresh-2026-11-09.md).

## Current usage and help

[README quick start](../README.md) is the entry point. Use the project-specific guides below before changing inputs, operating modes or deployment assumptions.

### Design and contracts

- [adr/0001 synthetic protocol](adr/0001-synthetic-protocol.md)
- [adr/0002 explicit endianness](adr/0002-explicit-endianness.md)
- [adr/0003 retry policy](adr/0003-retry-policy.md)
- [architecture](architecture.md)

### Security and validation

- [safety and security](safety-and-security.md)
- [testing](testing.md)

## Historical results and reproduction

The reviewed source is [`d4a8492365890c588b846b092d8dd6a691212118`](https://github.com/JasonStys/industrial-memory-protocol-workbench/tree/d4a8492365890c588b846b092d8dd6a691212118). The observed functional workflow baseline is `d4a8492365890c588b846b092d8dd6a691212118`; those observations are recorded at `2026-11-10T05:25:40.628667+00:00`. They do not certify an unrun later revision.

- [Detailed recorded validation](reports/stream-2026-11-09.md)
- [Current Actions](https://github.com/JasonStys/industrial-memory-protocol-workbench/actions) records later integration checks separately.
- Preserve dated measurements and follow the existing testing guide to reproduce them; a test-source inventory alone does not establish execution.

## Practical boundaries

- Synthetic diagnostic stream inspection, not physical or network device transport.
- CRC and recovered frame boundaries are not authentication. Plausible incomplete candidates can remain pending until EOF reports truncation.
- Existing client/server and write opt-in boundaries remain; recovery does not authorize writes to a device.

## Maintaining these editions

Update the editable usage/design/test documents first. Rebuild and visually review every Word page and workbook tab before replacing an edition; verify the exact binary digests and evidence source in publications.json. Keep account data, logs with secrets, installed-app state and private test stores out of documentation. Source and release assets retain their existing security and licensing boundaries.
