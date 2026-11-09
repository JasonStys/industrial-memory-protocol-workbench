/**
 * @file stream_decoder.cpp
 * @brief Implements bounded fragmented-stream diagnostics for synthetic IMLP/1 by Jason Stys.
 * @details Ring/member/function/variable locations are indexed in docs/generated/symbol-index.md.
 */
#include "imlp/stream_decoder.hpp"

#include <stdexcept>
#include <utility>

#include "imlp/codec.hpp"

namespace imlp {
std::vector<std::byte> StreamDecoder::prefix(const std::size_t count) const {
  std::vector<std::byte> bytes;
  bytes.reserve(count);
  for (std::size_t index = 0; index < count; ++index) {
    bytes.push_back(pending_[(head_ + index) % maximum_frame_size]);
  }
  return bytes;
}

void StreamDecoder::consume(const std::size_t count) noexcept {
  head_ = (head_ + count) % maximum_frame_size;
  used_ -= count;
  offset_ += count;
  expected_ = 0;
}

void StreamDecoder::issue(StreamBatch& result, const CodecError error, const std::size_t count) {
  if (!result.issues.empty() && result.issues.back().error == error &&
      result.issues.back().offset + result.issues.back().bytes == offset_) {
    result.issues.back().bytes += count;
  } else if (result.issues.size() < maximum_stream_issues) {
    result.issues.push_back({offset_, count, error});
  } else {
    ++result.omitted_issue_records;
    result.omitted_issue_bytes += count;
  }
  consume(count);
}

void StreamDecoder::drain(StreamBatch& result) {
  while (used_ != 0) {
    if (pending_[head_] != magic[0]) {
      issue(result, CodecError::bad_magic, 1);
      continue;
    }
    if (used_ == 1) return;
    if (pending_[(head_ + 1) % maximum_frame_size] != magic[1]) {
      issue(result, CodecError::bad_magic, 1);
      continue;
    }
    if (used_ < header_size) return;
    if (expected_ == 0) {
      const auto header = prefix(header_size);
      const auto checked = decode(header);
      if (checked.error != CodecError::truncated) {
        issue(result, checked.error, 1);
        continue;
      }
      const auto payload = (std::to_integer<std::size_t>(header[14]) << 8U) |
                           std::to_integer<std::size_t>(header[15]);
      expected_ = header_size + payload + checksum_size;
    }
    if (used_ < expected_) return;
    const auto bytes = prefix(expected_);
    auto decoded = decode(bytes);
    if (!decoded || !decoded.frame.has_value()) {
      issue(result, decoded.error, 1);
      continue;
    }
    const auto size = expected_;
    result.frames.push_back({offset_, size, std::move(*decoded.frame)});
    consume(size);
  }
}

StreamBatch StreamDecoder::feed(const std::span<const std::byte> input) {
  if (closed_ || input.size() > maximum_stream_chunk ||
      input.size() > maximum_stream_bytes - received_) {
    throw std::invalid_argument("closed or bounded synthetic stream input exceeded");
  }
  StreamBatch result;
  for (const auto byte : input) {
    pending_[(head_ + used_) % maximum_frame_size] = byte;
    ++used_;
    ++received_;
    drain(result);
  }
  result.pending_bytes = used_;
  return result;
}

StreamBatch StreamDecoder::finish() {
  if (closed_) throw std::logic_error("synthetic stream already finished");
  closed_ = true;
  StreamBatch result;
  if (used_ != 0) issue(result, CodecError::truncated, used_);
  return result;
}
}  // namespace imlp
