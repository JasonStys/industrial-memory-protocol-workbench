/**
 * @file server.hpp
 * @brief Declares the protocol simulator and its defense-in-depth write policy.
 * @details Exact declarations and line locations are generated in
 * docs/generated/symbol-index.md.
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

#include "imlp/memory_map.hpp"

namespace imlp {

/** Configures writes below the command-line layer; secure defaults remain
 * read-only. */
struct ServerPolicy {
  bool writes_enabled{false};
  std::uint32_t write_allow_begin{0x0100U};
  std::uint32_t write_allow_end{0x07FFU};
};

/** Captures one simulator decision without exposing mutable server state. */
struct ServerEvent {
  bool request_decoded{false};
  std::uint32_t request_id{0};
  Status status{Status::bad_request};
  std::string detail{};
};

/** Returns a response frame when safe and an observable event for every
 * request. */
struct HandleResult {
  std::vector<std::byte> response{};
  ServerEvent event{};
};

/** Decodes exact frames, enforces policy, and serves a private fixed-size
 * memory map. */
class MemoryServer {
 public:
  explicit MemoryServer(ServerPolicy policy = {});

  /** Process one complete frame without retaining caller-owned bytes. */
  [[nodiscard]] HandleResult handle(std::span<const std::byte> request);

  /** Expose read-only memory state for deterministic tests and diagnostics. */
  [[nodiscard]] const MemoryMap& memory() const noexcept { return memory_; }

 private:
  [[nodiscard]] bool write_is_allowed(std::uint32_t address, std::size_t length) const noexcept;
  [[nodiscard]] HandleResult make_response(const Frame& request, Opcode opcode, Status status,
                                           std::vector<std::byte> payload,
                                           std::string detail) const;

  ServerPolicy policy_;
  MemoryMap memory_;
};

}  // namespace imlp
