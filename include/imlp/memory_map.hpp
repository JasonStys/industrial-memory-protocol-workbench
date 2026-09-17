/**
 * @file memory_map.hpp
 * @brief Declares a bounded simulator memory map with explicit
 * read/write/denied regions.
 * @details Exact class and function line locations are generated in
 * docs/generated/symbol-index.md.
 */

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

#include "imlp/types.hpp"

namespace imlp {

inline constexpr std::size_t memory_capacity = 4096;

/** Describes policy at one simulated byte address. */
enum class Access { read_only, read_write, denied };

/** Returns an application status and, for reads, an owned byte sequence. */
struct MemoryResult {
  Status status{Status::ok};
  std::vector<std::byte> data{};

  [[nodiscard]] explicit operator bool() const noexcept { return status == Status::ok; }
};

/** Owns the fixed-size synthetic address space and enforces its region policy.
 */
class MemoryMap {
 public:
  MemoryMap();

  /** Read a non-empty bounded range only when every byte is readable. */
  [[nodiscard]] MemoryResult read(std::uint32_t address, std::size_t length) const;

  /** Write a non-empty bounded range only when every byte is writable. */
  [[nodiscard]] Status write(std::uint32_t address, std::span<const std::byte> data);

  /** Return the policy of one in-range address. */
  [[nodiscard]] static Access access_for(std::uint32_t address) noexcept;

 private:
  std::array<std::byte, memory_capacity> bytes_{};
};

}  // namespace imlp
