# Fragmented stream inspection workflow

Created by Jason Stys. Synthetic IMLP/1 only; no commercial protocol compatibility, socket, physical I/O or active write path is added.

1. Build the usual C++20 targets. CMake testing also locates Python3 for the independent CLI wire oracle.
2. Obtain a synthetic vector with `imlp-cli encode-read 64 1`, or construct an independently reviewed IMLP/1 byte stream.
3. Split its hex text at byte boundaries. Run `imlp-cli stream-inspect 49 <remaining-hex>` to test a magic prefix split. Multiple complete frames may share a chunk as long as the strict existing CLI chunk cap278bytes is respected.
4. Redirect stdout to a **new private file** if retaining metadata evidence. Output includes schema/author, input bytes, complete frame offset/extent/request/opcode/payload-length, discarded extents/error categories and omitted diagnostic totals. Payload contents are not exported.
5. Review corruption and truncation before interpreting recovered candidates. The diagnostic inspector does not dispatch frames to the simulator/server or modify its default exact-frame/write policy.

The reusable library accepts at most4096bytes per feed and64KiB over one decoder lifetime. Its fixed ring retains at most278pendingbytes. `finish()` closes once and reports incomplete pending bytes at their exact absolute offset. Calls exceeding caps or feeding a closed stream reject before consumption; create a new decoder for a new logical stream. Outputs own their frame values, so later feeds cannot invalidate borrowed spans.

Corrupt candidates discard one byte and search again, with adjacent same-category discarded ranges coalesced. This is controlled forensic resynchronization, not authenticated framing. Magic and CRC can occur inside arbitrary data. A plausible incomplete declared length waits for more data; EOF reports it as truncated instead of inventing a recovery behind it. Diagnostic caps preserve explicit omitted record/byte counts, and complete frames remain independent. This tool is not a hostile-code sandbox or a network capture implementation.
