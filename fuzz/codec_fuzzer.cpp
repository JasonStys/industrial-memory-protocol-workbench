/**
 * @file codec_fuzzer.cpp
 * @brief Feeds arbitrary bounded bytes through the decoder, round trip, and
 * simulator boundary.
 * @details The fuzzer entry point location is indexed in
 * docs/generated/symbol-index.md.
 */

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <span>

#include "imlp/codec.hpp"
#include "imlp/server.hpp"
#include "imlp/stream_decoder.hpp"

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
  imlp::StreamDecoder stream;
  const std::size_t split = size / 2;
  const auto first = stream.feed(bytes.first(split));
  const auto second = stream.feed(bytes.subspan(split));
  for (const auto* batch : {&first, &second}) {
    for (const auto& frame : batch->frames) {
      const auto encoded = imlp::encode(frame.frame);
      if (!encoded || frame.offset > size || frame.wire_bytes > size - frame.offset ||
          encoded.bytes.size() != frame.wire_bytes ||
          !std::equal(encoded.bytes.begin(), encoded.bytes.end(),
                      bytes.begin() + static_cast<std::ptrdiff_t>(frame.offset)))
        std::abort();
    }
  }
  if (stream.pending_bytes() >= imlp::maximum_frame_size) std::abort();
  static_cast<void>(stream.finish());
  imlp::MemoryServer server;
  static_cast<void>(server.handle(bytes));
  return 0;
}
