/**
 * @file test_properties.cpp
 * @brief Exercises thousands of generated frames, checksum mutations, and
 * arbitrary byte sequences.
 * @details Property test function locations are indexed in
 * docs/generated/symbol-index.md.
 */

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <vector>

#include "imlp/codec.hpp"
#include "test_harness.hpp"

namespace {

/** Produce deterministic pseudo-random values without external test
 * dependencies. */
[[nodiscard]] std::uint64_t next_random(std::uint64_t& state) noexcept {
  state ^= state << 13U;
  state ^= state >> 7U;
  state ^= state << 17U;
  return state;
}

/** Generate one semantically valid frame for the selected operation kind. */
[[nodiscard]] imlp::Frame generated_frame(std::uint64_t& state, const std::size_t index) {
  imlp::Frame frame{
      .request_id = static_cast<std::uint32_t>(next_random(state)),
      .address = static_cast<std::uint32_t>(next_random(state)),
  };
  const std::size_t kind = index % 5U;
  if (kind == 0U) {
    frame.opcode = imlp::Opcode::read_request;
    const auto length = static_cast<std::uint16_t>(next_random(state) % 256U + 1U);
    frame.payload = {static_cast<std::byte>((length >> 8U) & 0xFFU),
                     static_cast<std::byte>(length & 0xFFU)};
    return frame;
  }
  if (kind == 1U) {
    frame.opcode = imlp::Opcode::write_request;
    const std::size_t length = static_cast<std::size_t>(next_random(state) % 256U + 1U);
    frame.payload.resize(length);
  } else if (kind == 2U) {
    frame.opcode = imlp::Opcode::data_response;
    frame.flags = imlp::response_flag;
    frame.payload.resize(static_cast<std::size_t>(next_random(state) % 257U));
  } else if (kind == 3U) {
    frame.opcode = imlp::Opcode::write_acknowledgement;
    frame.flags = imlp::response_flag;
  } else {
    frame.opcode = imlp::Opcode::error_response;
    frame.flags = imlp::response_flag;
    frame.status = static_cast<imlp::Status>(next_random(state) % 5U + 1U);
    frame.payload.resize(static_cast<std::size_t>(next_random(state) % 64U));
  }
  for (std::byte& byte : frame.payload) {
    byte = static_cast<std::byte>(next_random(state) & 0xFFU);
  }
  return frame;
}

IMLP_TEST(generated_valid_frames_round_trip_exactly) {
  std::uint64_t state = 0xC0FFEE1234567890ULL;
  for (std::size_t index = 0; index < 10'000U; ++index) {
    const imlp::Frame frame = generated_frame(state, index);
    const imlp::EncodeResult encoded = imlp::encode(frame);
    IMLP_EXPECT(encoded);
    const imlp::DecodeResult decoded = imlp::decode(encoded.bytes);
    IMLP_EXPECT(decoded);
    IMLP_EXPECT_EQ(*decoded.frame, frame);
  }
}

IMLP_TEST(checksum_mutation_is_always_detected) {
  std::uint64_t state = 0x1234ABCD9876EF01ULL;
  for (std::size_t index = 0; index < 2'000U; ++index) {
    const imlp::Frame frame = generated_frame(state, index);
    imlp::EncodeResult encoded = imlp::encode(frame);
    IMLP_EXPECT(encoded);
    encoded.bytes.back() ^= std::byte{0x01};
    IMLP_EXPECT_EQ(imlp::decode(encoded.bytes).error, imlp::CodecError::checksum_mismatch);
  }
}

IMLP_TEST(arbitrary_bounded_input_never_produces_an_unstable_frame) {
  std::uint64_t state = 0x0BADF00D5EEDFACEULL;
  for (std::size_t iteration = 0; iteration < 10'000U; ++iteration) {
    const std::size_t length =
        static_cast<std::size_t>(next_random(state) % (imlp::maximum_frame_size * 2U));
    std::vector<std::byte> bytes(length);
    for (std::byte& byte : bytes) byte = static_cast<std::byte>(next_random(state) & 0xFFU);
    const imlp::DecodeResult decoded = imlp::decode(bytes);
    if (decoded && decoded.frame.has_value()) {
      const imlp::EncodeResult encoded = imlp::encode(*decoded.frame);
      IMLP_EXPECT(encoded);
      IMLP_EXPECT_EQ(encoded.bytes, bytes);
    }
  }
}

}  // namespace
