/**
 * @file codec_fuzzer.cpp
 * @brief Feeds arbitrary bounded bytes through the decoder, round trip, and
 * simulator boundary.
 * @details The fuzzer entry point location is indexed in
 * docs/generated/symbol-index.md.
 */

#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>

#include "imlp/codec.hpp"
#include "imlp/server.hpp"

/** Assert that every accepted frame has a stable encode/decode representation.
 */
extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, const std::size_t size) {
  if (size > imlp::maximum_frame_size * 2U) return 0;
  const auto bytes = std::span<const std::byte>(reinterpret_cast<const std::byte*>(data), size);
  const imlp::DecodeResult decoded = imlp::decode(bytes);
  if (decoded && decoded.frame.has_value()) {
    const imlp::EncodeResult encoded = imlp::encode(*decoded.frame);
    if (!encoded) std::abort();
    const imlp::DecodeResult round_trip = imlp::decode(encoded.bytes);
    if (!round_trip || !round_trip.frame.has_value() || *round_trip.frame != *decoded.frame) {
      std::abort();
    }
  }
  imlp::MemoryServer server;
  static_cast<void>(server.handle(bytes));
  return 0;
}
