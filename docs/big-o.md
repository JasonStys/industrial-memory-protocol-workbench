# Complexity and resource bounds

Let `n` be payload length, where `0 ≤ n ≤ 256`; `m` be memory operation length, where
`1 ≤ m ≤ 256`; and `t` be the number of retained trace records.

| Operation | Time | Additional space | Bound or rationale |
| --- | --- | --- | --- |
| CRC-32 | O(n) | O(1) | Eight bit steps per byte |
| Encode frame | O(n) | O(n) | One owned output vector, at most 278 bytes |
| Decode frame | O(n) | O(n) | CRC scan plus owned payload, at most 256 bytes |
| Hex encode/decode | O(n) | O(n) | Two text characters per byte |
| Memory read | O(m) | O(m) | Validate region then copy returned bytes |
| Memory write | O(m) | O(1) | Validate region then copy into fixed array |
| Server handle | O(n) | O(n) | Decode, policy check, memory operation, encode |
| Client read/write | O(a·n) | O(n) | `a` is bounded read attempts; writes fix `a=1` |
| Fault dequeue | O(1) | O(1) | `std::deque` front/pop-front |
| Trace append | amortized O(n) | O(t·n) | Each record owns frame bytes; caller may clear trace |

## Data-structure choices

- `std::array<std::byte, 4096>` makes simulator capacity explicit and avoids memory growth.
- `std::vector<std::byte>` represents variable wire payloads with contiguous storage required by
  spans and CRC scans.
- `std::span<const std::byte>` makes non-owning input length explicit without pointer/length drift.
- `std::deque<TransportFault>` supports O(1) scripted fault consumption from the front.
- `std::optional<Frame>` distinguishes no frame from a default-constructed frame.
- `enum class` prevents implicit mixing of opcodes, statuses, and error categories.

## Overflow strategy

Memory range validation checks `length <= capacity - start` only after `start < capacity`; it does not
evaluate an untrusted `address + length`. The server allowlist performs subtraction in `uint64_t` and
compares the length after verifying that the address is within the inclusive bounds.

## Bounded versus unbounded state

Wire frames, memory, retry attempts, and the fault queue's per-operation consumption are bounded by
configuration or protocol constants. The educational trace vector grows until `clear_trace()` is
called. A long-running adapter should replace it with a bounded ring buffer or streaming sink and an
observable dropped-record counter.

