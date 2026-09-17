/**
 * @file types.hpp
 * @brief Defines fixed-width wire types, protocol limits, frames, and error
 * categories.
 * @details Exact declarations and line locations are generated in
 * docs/generated/symbol-index.md.
 */

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace imlp {

inline constexpr std::array<std::byte, 2> magic{std::byte{0x49}, std::byte{0x4D}};
inline constexpr std::uint8_t protocol_version = 1;
inline constexpr std::uint8_t response_flag = 0x01;
inline constexpr std::size_t header_size = 18;
inline constexpr std::size_t checksum_size = 4;
inline constexpr std::size_t maximum_payload_size = 256;
inline constexpr std::size_t maximum_frame_size =
    header_size + maximum_payload_size + checksum_size;

/** Identifies request and response operations on the synthetic wire protocol.
 */
enum class Opcode : std::uint8_t {
  read_request = 0x01,
  write_request = 0x02,
  data_response = 0x81,
  write_acknowledgement = 0x82,
  error_response = 0xFF,
};

/** Carries application-level results without overloading transport failures. */
enum class Status : std::uint16_t {
  ok = 0,
  bad_request = 1,
  out_of_range = 2,
  write_disabled = 3,
  access_denied = 4,
  internal_error = 5,
};

/** Describes why untrusted bytes could not be accepted as a frame. */
enum class CodecError {
  none,
  truncated,
  bad_magic,
  unsupported_version,
  unsupported_opcode,
  unsupported_flags,
  nonzero_reserved,
  payload_too_large,
  length_mismatch,
  checksum_mismatch,
  invalid_semantics,
};

/** Represents the validated logical fields of one IMLP/1 frame. */
struct Frame {
  std::uint8_t version{protocol_version};
  Opcode opcode{Opcode::read_request};
  std::uint8_t flags{0};
  std::uint32_t request_id{0};
  std::uint32_t address{0};
  Status status{Status::ok};
  std::vector<std::byte> payload{};

  bool operator==(const Frame&) const = default;
};

/** Returns bytes or a precise encoding error; callers never receive partial
 * frames. */
struct EncodeResult {
  std::vector<std::byte> bytes{};
  CodecError error{CodecError::none};

  [[nodiscard]] explicit operator bool() const noexcept { return error == CodecError::none; }
};

/** Returns a complete frame or a precise decoding error and consumed byte
 * count. */
struct DecodeResult {
  std::optional<Frame> frame{};
  CodecError error{CodecError::none};
  std::size_t consumed{0};

  [[nodiscard]] explicit operator bool() const noexcept {
    return error == CodecError::none && frame.has_value();
  }
};

}  // namespace imlp
