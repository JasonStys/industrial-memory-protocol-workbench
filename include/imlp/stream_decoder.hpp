/**
 * @file stream_decoder.hpp
 * @brief Declares bounded synthetic stream reassembly and corruption-offset diagnostics by Jason
 * Stys.
 * @details Owned ring bytes and offsets, frames, issues, and all member/function locations are
 * indexed in docs/generated/symbol-index.md. This decoder is a diagnostic tool, never a device
 * transport.
 */
#pragma once

#include <array>
#include <cstddef>
#include <span>
#include <vector>

#include "imlp/types.hpp"

namespace imlp {
inline constexpr std::size_t maximum_stream_chunk = 4096;
inline constexpr std::size_t maximum_stream_bytes = 65536;
inline constexpr std::size_t maximum_stream_issues = 256;

/** One owned complete frame with its exact absolute stream position and wire extent. */
struct StreamFrame {
  std::size_t offset{};
  std::size_t wire_bytes{};
  Frame frame{};
};

/** An exact discarded byte extent and fixed codec category, never a claimed authenticated boundary.
 */
struct StreamIssue {
  std::size_t offset{};
  std::size_t bytes{};
  CodecError error{CodecError::none};
};

/** One bounded feed result; omitted diagnostics retain record and byte counts, while valid frames
 * remain. */
struct StreamBatch {
  std::vector<StreamFrame> frames{};
  std::vector<StreamIssue> issues{};
  std::size_t omitted_issue_records{};
  std::size_t omitted_issue_bytes{};
  std::size_t pending_bytes{};
};

/** Reassemble fragments/coalesced frames using at most278 pending bytes; enforce a64KiB stream
 * lifetime. */
class StreamDecoder {
 public:
  /** Feed at most4096 bytes; invalid size/lifetime/closed calls reject before consuming input. */
  [[nodiscard]] StreamBatch feed(std::span<const std::byte> input);
  /** Close once, reporting any incomplete candidate at its exact offset; never guess it was valid.
   */
  [[nodiscard]] StreamBatch finish();
  /** Inspect bounded retained bytes without exposing a borrowed buffer lifetime. */
  [[nodiscard]] std::size_t pending_bytes() const noexcept { return used_; }

 private:
  /** Copy a bounded prefix from the ring for the unchanged exact-frame codec. */
  [[nodiscard]] std::vector<std::byte> prefix(std::size_t count) const;
  /** Remove accepted/discarded bytes in O(1), preserving absolute offset and resetting candidate
   * length. */
  void consume(std::size_t count) noexcept;
  /** Coalesce adjacent same-category discarded bytes, bounding diagnostics without hiding omitted
   * byte counts. */
  void issue(StreamBatch& result, CodecError error, std::size_t count);
  /** Process available candidates; validated header/length precede waiting for payload or checksum.
   */
  void drain(StreamBatch& result);

  std::array<std::byte, maximum_frame_size> pending_{};
  std::size_t head_{};
  std::size_t used_{};
  std::size_t expected_{};
  std::size_t offset_{};
  std::size_t received_{};
  bool closed_{};
};
}  // namespace imlp
