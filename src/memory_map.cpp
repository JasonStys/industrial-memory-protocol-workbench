/**
 * @file memory_map.cpp
 * @brief Implements overflow-safe range checks and simulator access controls.
 * @details Function and significant variable locations are indexed in the
 * generated symbol index.
 */

#include "imlp/memory_map.hpp"

#include <algorithm>
#include <string_view>

namespace imlp {
namespace {

/** Check a range without evaluating an overflowing address-plus-length
 * expression. */
[[nodiscard]] bool range_fits(const std::uint32_t address, const std::size_t length) noexcept {
  if (length == 0U || length > memory_capacity) return false;
  const auto start = static_cast<std::size_t>(address);
  return start < memory_capacity && length <= memory_capacity - start;
}

}  // namespace

MemoryMap::MemoryMap() {
  constexpr std::string_view identity = "IMLP/1 synthetic memory simulator";
  for (std::size_t index = 0; index < identity.size(); ++index) {
    bytes_[index] = static_cast<std::byte>(static_cast<unsigned char>(identity[index]));
  }
  bytes_[0x40] = std::byte{protocol_version};
}

MemoryResult MemoryMap::read(const std::uint32_t address, const std::size_t length) const {
  if (!range_fits(address, length) || length > maximum_payload_size) {
    return {Status::out_of_range, {}};
  }
  const auto start = static_cast<std::size_t>(address);
  for (std::size_t offset = 0; offset < length; ++offset) {
    if (access_for(static_cast<std::uint32_t>(start + offset)) == Access::denied) {
      return {Status::access_denied, {}};
    }
  }
  return {Status::ok,
          std::vector<std::byte>(bytes_.begin() + static_cast<std::ptrdiff_t>(start),
                                 bytes_.begin() + static_cast<std::ptrdiff_t>(start + length))};
}

Status MemoryMap::write(const std::uint32_t address, const std::span<const std::byte> data) {
  if (!range_fits(address, data.size()) || data.size() > maximum_payload_size) {
    return Status::out_of_range;
  }
  const auto start = static_cast<std::size_t>(address);
  for (std::size_t offset = 0; offset < data.size(); ++offset) {
    if (access_for(static_cast<std::uint32_t>(start + offset)) != Access::read_write) {
      return Status::access_denied;
    }
  }
  std::copy(data.begin(), data.end(), bytes_.begin() + static_cast<std::ptrdiff_t>(start));
  return Status::ok;
}

Access MemoryMap::access_for(const std::uint32_t address) noexcept {
  if (address <= 0x00FFU) return Access::read_only;
  if (address <= 0x07FFU) return Access::read_write;
  return Access::denied;
}

}  // namespace imlp
