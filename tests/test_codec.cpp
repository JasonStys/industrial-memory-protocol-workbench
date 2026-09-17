/**
 * @file test_codec.cpp
 * @brief Verifies CRC, byte order, frame semantics, corruption handling, and
 * hex conversion.
 * @details Test function locations are indexed in
 * docs/generated/symbol-index.md.
 */

#include <cstddef>
#include <cstdint>
#include <string_view>
#include <vector>

#include "imlp/codec.hpp"
#include "test_harness.hpp"

namespace {

/** Convert ASCII to bytes without depending on character signedness. */
[[nodiscard]] std::vector<std::byte> ascii_bytes(const std::string_view text) {
  std::vector<std::byte> bytes;
  bytes.reserve(text.size());
  for (const char value : text) {
    bytes.push_back(static_cast<std::byte>(static_cast<unsigned char>(value)));
  }
  return bytes;
}

IMLP_TEST(crc32_matches_published_check_value) {
  const auto bytes = ascii_bytes("123456789");
  IMLP_EXPECT_EQ(imlp::crc32(bytes), 0xCBF43926U);
}

IMLP_TEST(read_request_round_trips_with_big_endian_fields) {
  const imlp::Frame frame{
      .opcode = imlp::Opcode::read_request,
      .request_id = 0x10203040U,
      .address = 0x50607080U,
      .payload = {std::byte{0x00}, std::byte{0x20}},
  };
  const imlp::EncodeResult encoded = imlp::encode(frame);
  IMLP_EXPECT(encoded);
  IMLP_EXPECT_EQ(encoded.bytes[6], std::byte{0x10});
  IMLP_EXPECT_EQ(encoded.bytes[9], std::byte{0x40});
  IMLP_EXPECT_EQ(encoded.bytes[10], std::byte{0x50});
  IMLP_EXPECT_EQ(encoded.bytes[13], std::byte{0x80});
  const imlp::DecodeResult decoded = imlp::decode(encoded.bytes);
  IMLP_EXPECT(decoded);
  IMLP_EXPECT_EQ(*decoded.frame, frame);
}

IMLP_TEST(codec_rejects_truncation_trailing_bytes_and_corruption) {
  const imlp::Frame frame{
      .opcode = imlp::Opcode::write_request,
      .request_id = 7,
      .address = 0x0100U,
      .payload = {std::byte{0xAA}, std::byte{0x55}},
  };
  const imlp::EncodeResult encoded = imlp::encode(frame);
  IMLP_EXPECT(encoded);

  auto truncated = encoded.bytes;
  truncated.pop_back();
  IMLP_EXPECT_EQ(imlp::decode(truncated).error, imlp::CodecError::truncated);

  auto trailing = encoded.bytes;
  trailing.push_back(std::byte{0});
  IMLP_EXPECT_EQ(imlp::decode(trailing).error, imlp::CodecError::length_mismatch);

  auto corrupted = encoded.bytes;
  corrupted.back() ^= std::byte{0x01};
  IMLP_EXPECT_EQ(imlp::decode(corrupted).error, imlp::CodecError::checksum_mismatch);
}

IMLP_TEST(codec_rejects_untrusted_header_fields_before_indexing_payload) {
  const imlp::Frame frame{
      .opcode = imlp::Opcode::read_request,
      .request_id = 1,
      .payload = {std::byte{0}, std::byte{1}},
  };
  const imlp::EncodeResult encoded = imlp::encode(frame);
  IMLP_EXPECT(encoded);

  auto bad_magic = encoded.bytes;
  bad_magic[0] = std::byte{0};
  IMLP_EXPECT_EQ(imlp::decode(bad_magic).error, imlp::CodecError::bad_magic);

  auto bad_reserved = encoded.bytes;
  bad_reserved[5] = std::byte{1};
  IMLP_EXPECT_EQ(imlp::decode(bad_reserved).error, imlp::CodecError::nonzero_reserved);

  auto oversized = encoded.bytes;
  oversized[14] = std::byte{0x01};
  oversized[15] = std::byte{0x01};
  IMLP_EXPECT_EQ(imlp::decode(oversized).error, imlp::CodecError::payload_too_large);
}

IMLP_TEST(encoder_rejects_semantically_invalid_frames) {
  imlp::Frame read{
      .opcode = imlp::Opcode::read_request,
      .payload = {std::byte{1}},
  };
  IMLP_EXPECT_EQ(imlp::encode(read).error, imlp::CodecError::invalid_semantics);

  imlp::Frame response{
      .opcode = imlp::Opcode::data_response,
      .flags = 0,
      .payload = {std::byte{1}},
  };
  IMLP_EXPECT_EQ(imlp::encode(response).error, imlp::CodecError::invalid_semantics);

  imlp::Frame oversized{
      .opcode = imlp::Opcode::write_request,
      .payload = std::vector<std::byte>(imlp::maximum_payload_size + 1U),
  };
  IMLP_EXPECT_EQ(imlp::encode(oversized).error, imlp::CodecError::payload_too_large);
}

IMLP_TEST(hex_conversion_is_exact_and_bounded) {
  const std::vector<std::byte> expected{std::byte{0x00}, std::byte{0xA5}, std::byte{0xFF}};
  IMLP_EXPECT_EQ(imlp::bytes_to_hex(expected), std::string("00a5ff"));
  IMLP_EXPECT_EQ(*imlp::bytes_from_hex("00A5ff"), expected);
  IMLP_EXPECT(!imlp::bytes_from_hex("0").has_value());
  IMLP_EXPECT(!imlp::bytes_from_hex("zz").has_value());
  IMLP_EXPECT(
      !imlp::bytes_from_hex(std::string(imlp::maximum_frame_size * 2U + 2U, '0')).has_value());
}

}  // namespace
