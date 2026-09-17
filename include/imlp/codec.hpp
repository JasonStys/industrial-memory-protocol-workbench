/**
 * @file codec.hpp
 * @brief Declares bounded big-endian encoding, decoding, CRC-32, and
 * hexadecimal utilities.
 * @details Exact function line locations are generated in
 * docs/generated/symbol-index.md.
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "imlp/types.hpp"

namespace imlp {

/** Calculate the IEEE CRC-32 used to detect accidental frame corruption. */
[[nodiscard]] std::uint32_t crc32(std::span<const std::byte> bytes) noexcept;

/** Encode a semantically valid frame into one bounded wire representation. */
[[nodiscard]] EncodeResult encode(const Frame& frame);

/** Decode one exact frame, rejecting truncation, trailing data, and invalid
 * fields. */
[[nodiscard]] DecodeResult decode(std::span<const std::byte> bytes) noexcept;

/** Return a stable diagnostic identifier for a codec error. */
[[nodiscard]] std::string_view codec_error_name(CodecError error) noexcept;

/** Convert bytes to lowercase hexadecimal for traces and command-line
 * inspection. */
[[nodiscard]] std::string bytes_to_hex(std::span<const std::byte> bytes);

/** Parse even-length hexadecimal without accepting separators or partial input.
 */
[[nodiscard]] std::optional<std::vector<std::byte>> bytes_from_hex(std::string_view text);

}  // namespace imlp
