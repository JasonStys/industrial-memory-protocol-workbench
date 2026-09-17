/**
 * @file codec.cpp
 * @brief Implements defensive frame validation and explicit big-endian
 * conversion.
 * @details Helper, public function, and significant variable locations are
 * indexed in the symbol index.
 */

#include "imlp/codec.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <limits>

namespace imlp {
namespace {

/** Append an unsigned 16-bit integer in network byte order. */
void append_u16(std::vector<std::byte>& output, const std::uint16_t value) {
  output.push_back(static_cast<std::byte>((value >> 8U) & 0xFFU));
  output.push_back(static_cast<std::byte>(value & 0xFFU));
}

/** Append an unsigned 32-bit integer in network byte order. */
void append_u32(std::vector<std::byte>& output, const std::uint32_t value) {
  output.push_back(static_cast<std::byte>((value >> 24U) & 0xFFU));
  output.push_back(static_cast<std::byte>((value >> 16U) & 0xFFU));
  output.push_back(static_cast<std::byte>((value >> 8U) & 0xFFU));
  output.push_back(static_cast<std::byte>(value & 0xFFU));
}

/** Read a known-in-bounds unsigned 16-bit big-endian field. */
[[nodiscard]] std::uint16_t read_u16(const std::span<const std::byte> bytes,
                                     const std::size_t offset) noexcept {
  const auto high = std::to_integer<std::uint16_t>(bytes[offset]);
  const auto low = std::to_integer<std::uint16_t>(bytes[offset + 1]);
  return static_cast<std::uint16_t>((high << 8U) | low);
}

/** Read a known-in-bounds unsigned 32-bit big-endian field. */
[[nodiscard]] std::uint32_t read_u32(const std::span<const std::byte> bytes,
                                     const std::size_t offset) noexcept {
  return (std::to_integer<std::uint32_t>(bytes[offset]) << 24U) |
         (std::to_integer<std::uint32_t>(bytes[offset + 1]) << 16U) |
         (std::to_integer<std::uint32_t>(bytes[offset + 2]) << 8U) |
         std::to_integer<std::uint32_t>(bytes[offset + 3]);
}

/** Return true only for assigned protocol opcodes. */
[[nodiscard]] bool is_supported_opcode(const Opcode opcode) noexcept {
  switch (opcode) {
    case Opcode::read_request:
    case Opcode::write_request:
    case Opcode::data_response:
    case Opcode::write_acknowledgement:
    case Opcode::error_response:
      return true;
  }
  return false;
}

/** Check relationships between opcode, flags, status, and payload before use.
 */
[[nodiscard]] bool has_valid_semantics(const Frame& frame) noexcept {
  const bool is_response = (frame.flags & response_flag) != 0U;
  const bool expects_response_flag = frame.opcode == Opcode::data_response ||
                                     frame.opcode == Opcode::write_acknowledgement ||
                                     frame.opcode == Opcode::error_response;
  if (is_response != expects_response_flag) return false;
  if ((frame.flags & static_cast<std::uint8_t>(~response_flag)) != 0U) return false;

  if (frame.opcode == Opcode::read_request) {
    return frame.status == Status::ok && frame.payload.size() == 2U;
  }
  if (frame.opcode == Opcode::write_request) {
    return frame.status == Status::ok && !frame.payload.empty();
  }
  if (frame.opcode == Opcode::data_response) return frame.status == Status::ok;
  if (frame.opcode == Opcode::write_acknowledgement) {
    return frame.status == Status::ok && frame.payload.empty();
  }
  return frame.opcode == Opcode::error_response && frame.status != Status::ok;
}

/** Convert one hexadecimal character, returning no value for invalid input. */
[[nodiscard]] std::optional<std::uint8_t> hex_nibble(const char value) noexcept {
  if (value >= '0' && value <= '9') return static_cast<std::uint8_t>(value - '0');
  if (value >= 'a' && value <= 'f') return static_cast<std::uint8_t>(value - 'a' + 10);
  if (value >= 'A' && value <= 'F') return static_cast<std::uint8_t>(value - 'A' + 10);
  return std::nullopt;
}

}  // namespace

std::uint32_t crc32(const std::span<const std::byte> bytes) noexcept {
  std::uint32_t crc = 0xFFFFFFFFU;
  for (const std::byte byte : bytes) {
    crc ^= std::to_integer<std::uint32_t>(byte);
    for (unsigned int bit = 0; bit < 8U; ++bit) {
      const std::uint32_t mask = 0U - (crc & 1U);
      crc = (crc >> 1U) ^ (0xEDB88320U & mask);
    }
  }
  return ~crc;
}

EncodeResult encode(const Frame& frame) {
  if (frame.version != protocol_version) return {{}, CodecError::unsupported_version};
  if (!is_supported_opcode(frame.opcode)) return {{}, CodecError::unsupported_opcode};
  if (frame.payload.size() > maximum_payload_size) return {{}, CodecError::payload_too_large};
  if (!has_valid_semantics(frame)) return {{}, CodecError::invalid_semantics};

  std::vector<std::byte> output;
  output.reserve(header_size + frame.payload.size() + checksum_size);
  output.insert(output.end(), magic.begin(), magic.end());
  output.push_back(static_cast<std::byte>(frame.version));
  output.push_back(static_cast<std::byte>(frame.opcode));
  output.push_back(static_cast<std::byte>(frame.flags));
  output.push_back(std::byte{0});
  append_u32(output, frame.request_id);
  append_u32(output, frame.address);
  append_u16(output, static_cast<std::uint16_t>(frame.payload.size()));
  append_u16(output, static_cast<std::uint16_t>(frame.status));
  output.insert(output.end(), frame.payload.begin(), frame.payload.end());
  append_u32(output, crc32(output));
  return {std::move(output), CodecError::none};
}

DecodeResult decode(const std::span<const std::byte> bytes) noexcept {
  if (bytes.size() < header_size) return {{}, CodecError::truncated, 0};
  if (!std::equal(magic.begin(), magic.end(), bytes.begin())) {
    return {{}, CodecError::bad_magic, 0};
  }
  if (std::to_integer<std::uint8_t>(bytes[2]) != protocol_version) {
    return {{}, CodecError::unsupported_version, 0};
  }

  const auto opcode = static_cast<Opcode>(std::to_integer<std::uint8_t>(bytes[3]));
  if (!is_supported_opcode(opcode)) return {{}, CodecError::unsupported_opcode, 0};
  const auto flags = std::to_integer<std::uint8_t>(bytes[4]);
  if ((flags & static_cast<std::uint8_t>(~response_flag)) != 0U) {
    return {{}, CodecError::unsupported_flags, 0};
  }
  if (bytes[5] != std::byte{0}) return {{}, CodecError::nonzero_reserved, 0};

  const std::size_t payload_size = read_u16(bytes, 14);
  if (payload_size > maximum_payload_size) return {{}, CodecError::payload_too_large, 0};
  const std::size_t expected_size = header_size + payload_size + checksum_size;
  if (bytes.size() < expected_size) return {{}, CodecError::truncated, 0};
  if (bytes.size() != expected_size) return {{}, CodecError::length_mismatch, expected_size};

  const std::uint32_t expected_crc = read_u32(bytes, expected_size - checksum_size);
  if (crc32(bytes.first(expected_size - checksum_size)) != expected_crc) {
    return {{}, CodecError::checksum_mismatch, expected_size};
  }

  Frame frame{
      .version = protocol_version,
      .opcode = opcode,
      .flags = flags,
      .request_id = read_u32(bytes, 6),
      .address = read_u32(bytes, 10),
      .status = static_cast<Status>(read_u16(bytes, 16)),
      .payload = std::vector<std::byte>(
          bytes.begin() + static_cast<std::ptrdiff_t>(header_size),
          bytes.begin() + static_cast<std::ptrdiff_t>(header_size + payload_size)),
  };
  if (!has_valid_semantics(frame)) return {{}, CodecError::invalid_semantics, expected_size};
  return {std::move(frame), CodecError::none, expected_size};
}

std::string_view codec_error_name(const CodecError error) noexcept {
  switch (error) {
    case CodecError::none:
      return "none";
    case CodecError::truncated:
      return "truncated";
    case CodecError::bad_magic:
      return "bad_magic";
    case CodecError::unsupported_version:
      return "unsupported_version";
    case CodecError::unsupported_opcode:
      return "unsupported_opcode";
    case CodecError::unsupported_flags:
      return "unsupported_flags";
    case CodecError::nonzero_reserved:
      return "nonzero_reserved";
    case CodecError::payload_too_large:
      return "payload_too_large";
    case CodecError::length_mismatch:
      return "length_mismatch";
    case CodecError::checksum_mismatch:
      return "checksum_mismatch";
    case CodecError::invalid_semantics:
      return "invalid_semantics";
  }
  return "unknown";
}

std::string bytes_to_hex(const std::span<const std::byte> bytes) {
  constexpr std::array<char, 16> digits{'0', '1', '2', '3', '4', '5', '6', '7',
                                        '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'};
  std::string result;
  result.reserve(bytes.size() * 2U);
  for (const std::byte byte : bytes) {
    const auto value = std::to_integer<std::uint8_t>(byte);
    result.push_back(digits[value >> 4U]);
    result.push_back(digits[value & 0x0FU]);
  }
  return result;
}

std::optional<std::vector<std::byte>> bytes_from_hex(const std::string_view text) {
  if ((text.size() % 2U) != 0U || text.size() / 2U > maximum_frame_size) return std::nullopt;
  std::vector<std::byte> result;
  result.reserve(text.size() / 2U);
  for (std::size_t index = 0; index < text.size(); index += 2U) {
    const auto high = hex_nibble(text[index]);
    const auto low = hex_nibble(text[index + 1U]);
    if (!high.has_value() || !low.has_value()) return std::nullopt;
    result.push_back(static_cast<std::byte>(static_cast<std::uint8_t>((*high << 4U) | *low)));
  }
  return result;
}

}  // namespace imlp
