/**
 * @file test_stream.cpp
 * @brief Tests independent fragmented/coalesced stream, corruption, EOF and resource-bound oracles
 * by Jason Stys.
 * @details Test and variable locations are indexed in docs/generated/symbol-index.md.
 */
#include <algorithm>
#include <array>
#include <stdexcept>
#include <vector>

#include "imlp/codec.hpp"
#include "imlp/stream_decoder.hpp"
#include "test_harness.hpp"

namespace {
/** Build a maximum-size valid frame containing embedded magic that must remain ordinary payload. */
imlp::Frame maximum_frame() {
  imlp::Frame frame{.opcode = imlp::Opcode::write_request, .request_id = 42, .address = 256};
  for (std::size_t index = 0; index < imlp::maximum_payload_size; ++index) {
    frame.payload.push_back(index % 2 == 0 ? std::byte{0x49} : std::byte{0x4D});
  }
  return frame;
}

IMLP_TEST(stream_all_split_positions_and_byte_feeds_preserve_exact_frames) {
  const auto logical = maximum_frame();
  const auto wire = imlp::encode(logical).bytes;
  for (std::size_t split = 0; split <= wire.size(); ++split) {
    imlp::StreamDecoder decoder;
    const auto first = decoder.feed(std::span(wire).first(split));
    const auto second = decoder.feed(std::span(wire).subspan(split));
    IMLP_EXPECT_EQ(first.frames.size() + second.frames.size(), 1U);
    const auto& frame = first.frames.empty() ? second.frames[0] : first.frames[0];
    IMLP_EXPECT_EQ(frame.frame, logical);
    IMLP_EXPECT_EQ(frame.offset, 0U);
    IMLP_EXPECT_EQ(frame.wire_bytes, wire.size());
    IMLP_EXPECT(first.issues.empty() && second.issues.empty());
    IMLP_EXPECT(decoder.finish().issues.empty());
  }
  imlp::StreamDecoder decoder;
  std::size_t accepted = 0;
  for (const auto byte : wire) {
    const std::array single{byte};
    const auto batch = decoder.feed(single);
    accepted += batch.frames.size();
    IMLP_EXPECT(decoder.pending_bytes() < imlp::maximum_frame_size);
  }
  IMLP_EXPECT_EQ(accepted, 1U);
  IMLP_EXPECT(decoder.finish().issues.empty());
}

IMLP_TEST(stream_coalesced_frames_junk_and_crc_recovery_have_exact_offsets) {
  const auto wire = imlp::encode(imlp::Frame{.payload = {std::byte{0}, std::byte{8}}}).bytes;
  auto bad = wire;
  bad.back() ^= std::byte{1};
  std::vector<std::byte> stream{std::byte{0x49}, std::byte{0x49}, std::byte{0}};
  stream.insert(stream.end(), bad.begin(), bad.end());
  stream.insert(stream.end(), wire.begin(), wire.end());
  stream.insert(stream.end(), wire.begin(), wire.end());
  imlp::StreamDecoder decoder;
  const auto batch = decoder.feed(stream);
  IMLP_EXPECT_EQ(batch.frames.size(), 2U);
  IMLP_EXPECT_EQ(batch.frames[0].offset, 3U + wire.size());
  IMLP_EXPECT_EQ(batch.frames[1].offset, 3U + 2U * wire.size());
  IMLP_EXPECT(std::any_of(batch.issues.begin(), batch.issues.end(), [](const auto& issue) {
    return issue.error == imlp::CodecError::checksum_mismatch && issue.offset == 3;
  }));
  IMLP_EXPECT(decoder.finish().issues.empty());
}

IMLP_TEST(stream_malformed_length_recovers_but_incomplete_eof_never_invents_a_frame) {
  const auto wire = imlp::encode(imlp::Frame{.payload = {std::byte{0}, std::byte{8}}}).bytes;
  auto overlong = wire;
  overlong[14] = std::byte{0xFF};
  overlong.insert(overlong.end(), wire.begin(), wire.end());
  imlp::StreamDecoder decoder;
  const auto batch = decoder.feed(overlong);
  IMLP_EXPECT_EQ(batch.frames.size(), 1U);
  IMLP_EXPECT_EQ(batch.frames[0].offset, wire.size());
  IMLP_EXPECT_EQ(batch.issues[0].error, imlp::CodecError::payload_too_large);
  static_cast<void>(decoder.feed(std::span(wire).first(10)));
  const auto eof = decoder.finish();
  IMLP_EXPECT_EQ(eof.issues.size(), 1U);
  IMLP_EXPECT_EQ(eof.issues[0].offset, overlong.size());
  IMLP_EXPECT_EQ(eof.issues[0].bytes, 10U);
  IMLP_EXPECT_EQ(eof.issues[0].error, imlp::CodecError::truncated);
}

IMLP_TEST(
    stream_diagnostic_and_lifetime_limits_retain_accounting_and_do_not_consume_rejected_input) {
  auto wire = imlp::encode(imlp::Frame{.payload = {std::byte{0}, std::byte{8}}}).bytes;
  wire.back() ^= std::byte{1};
  std::vector<std::byte> corrupt;
  for (std::size_t index = 0; index < 170; ++index) {
    corrupt.insert(corrupt.end(), wire.begin(), wire.end());
  }
  imlp::StreamDecoder decoder;
  const auto batch = decoder.feed(corrupt);
  IMLP_EXPECT(batch.frames.empty());
  IMLP_EXPECT(batch.issues.size() <= imlp::maximum_stream_issues);
  IMLP_EXPECT(batch.omitted_issue_records > 0);
  std::size_t accounted = batch.omitted_issue_bytes;
  for (const auto& issue : batch.issues) accounted += issue.bytes;
  IMLP_EXPECT_EQ(accounted + decoder.pending_bytes(), corrupt.size());
  const std::vector too_large(imlp::maximum_stream_chunk + 1, std::byte{0});
  bool rejected = false;
  try {
    static_cast<void>(decoder.feed(too_large));
  } catch (const std::invalid_argument&) {
    rejected = true;
  }
  IMLP_EXPECT(rejected);
  IMLP_EXPECT_EQ(decoder.pending_bytes(), batch.pending_bytes);
  static_cast<void>(decoder.finish());
  rejected = false;
  try {
    static_cast<void>(decoder.feed({}));
  } catch (const std::invalid_argument&) {
    rejected = true;
  }
  IMLP_EXPECT(rejected);
  imlp::StreamDecoder finite;
  const std::vector zeros(imlp::maximum_stream_chunk, std::byte{0});
  for (std::size_t index = 0; index < 16; ++index) static_cast<void>(finite.feed(zeros));
  rejected = false;
  try {
    const std::array extra{std::byte{0}};
    static_cast<void>(finite.feed(extra));
  } catch (const std::invalid_argument&) {
    rejected = true;
  }
  IMLP_EXPECT(rejected);
}
}  // namespace
