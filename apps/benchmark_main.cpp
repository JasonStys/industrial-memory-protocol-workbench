/**
 * @file benchmark_main.cpp
 * @brief Measures repeated encode, server-handle, and decode cycles with stable
 * JSON output.
 * @details Benchmark helper and variable locations are indexed in
 * docs/generated/symbol-index.md.
 */

#include <algorithm>
#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <vector>

#include "imlp/codec.hpp"
#include "imlp/server.hpp"

namespace {

inline constexpr std::size_t samples = 5;
inline constexpr std::size_t operations_per_sample = 50'000;

/** Execute one measured batch and fail fast if any protocol invariant breaks.
 */
[[nodiscard]] double run_sample(imlp::MemoryServer& server, std::uint64_t& checksum) {
  const auto started = std::chrono::steady_clock::now();
  for (std::size_t index = 0; index < operations_per_sample; ++index) {
    const auto request_id = static_cast<std::uint32_t>(index + 1U);
    const imlp::Frame request{
        .opcode = imlp::Opcode::read_request,
        .request_id = request_id,
        .address = static_cast<std::uint32_t>(index % 128U),
        .payload = {std::byte{0}, std::byte{16}},
    };
    const imlp::EncodeResult encoded = imlp::encode(request);
    if (!encoded) return -1.0;
    const imlp::HandleResult handled = server.handle(encoded.bytes);
    const imlp::DecodeResult decoded = imlp::decode(handled.response);
    if (!decoded || !decoded.frame.has_value()) return -1.0;
    checksum += decoded.frame->request_id;
    checksum += decoded.frame->payload.size();
  }
  const auto elapsed = std::chrono::steady_clock::now() - started;
  return std::chrono::duration<double, std::milli>(elapsed).count();
}

}  // namespace

/** Run five samples and emit a reproducible summary suitable for a report
 * artifact. */
int main() {
  imlp::MemoryServer server;
  std::array<double, samples> milliseconds{};
  std::uint64_t checksum = 0;
  for (double& sample : milliseconds) {
    sample = run_sample(server, checksum);
    if (sample < 0.0) {
      std::cerr << "benchmark protocol validation failed\n";
      return 1;
    }
  }
  std::array<double, samples> sorted = milliseconds;
  std::sort(sorted.begin(), sorted.end());
  const double median_ms = sorted[samples / 2U];
  const double operations_per_second =
      static_cast<double>(operations_per_sample) * 1000.0 / median_ms;

  std::cout << std::fixed << std::setprecision(3)
            << "{\n  \"operations_per_sample\": " << operations_per_sample
            << ",\n  \"samples_ms\": [";
  for (std::size_t index = 0; index < milliseconds.size(); ++index) {
    if (index != 0U) std::cout << ", ";
    std::cout << milliseconds[index];
  }
  std::cout << "],\n  \"median_ms\": " << median_ms
            << ",\n  \"median_operations_per_second\": " << operations_per_second
            << ",\n  \"checksum\": " << checksum << "\n}\n";
  return 0;
}
