/**
 * @file transport.hpp
 * @brief Declares an injectable transport and deterministic loopback fault
 * simulator.
 * @details Exact declarations and line locations are generated in
 * docs/generated/symbol-index.md.
 */

#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "imlp/server.hpp"

namespace imlp {

/** Separates connection failures from protocol and application statuses. */
enum class TransportError { none, not_connected, timeout, disconnected };

/** Selects a single deterministic fault for the next exchange. */
enum class TransportFault {
  timeout,
  disconnect,
  truncate_response,
  corrupt_response,
  wrong_request_id,
};

/** Returns either response bytes or a transport-layer failure. */
struct TransportReply {
  TransportError error{TransportError::none};
  std::vector<std::byte> bytes{};

  [[nodiscard]] explicit operator bool() const noexcept { return error == TransportError::none; }
};

/** Records one direction of an exchange for packet-style inspection. */
struct TraceRecord {
  std::uint64_t sequence{0};
  std::string direction{};
  std::string outcome{};
  std::vector<std::byte> bytes{};
};

/** Abstracts the deadline-aware request/response boundary used by the client.
 */
class ITransport {
 public:
  virtual ~ITransport() = default;

  [[nodiscard]] virtual bool connect() = 0;
  virtual void close() noexcept = 0;
  [[nodiscard]] virtual bool connected() const noexcept = 0;
  [[nodiscard]] virtual TransportReply exchange(std::span<const std::byte> request,
                                                std::chrono::milliseconds deadline) = 0;
};

/** Connects the client to an in-process server and injects reproducible
 * failures. */
class LoopbackTransport final : public ITransport {
 public:
  explicit LoopbackTransport(MemoryServer& server);

  [[nodiscard]] bool connect() override;
  void close() noexcept override;
  [[nodiscard]] bool connected() const noexcept override;
  [[nodiscard]] TransportReply exchange(std::span<const std::byte> request,
                                        std::chrono::milliseconds deadline) override;

  /** Queue one fault; each subsequent exchange consumes at most one queued
   * item. */
  void push_fault(TransportFault fault);

  /** Return the immutable packet trace accumulated by this transport. */
  [[nodiscard]] std::span<const TraceRecord> trace() const noexcept;

  /** Remove trace records without changing connection or fault state. */
  void clear_trace() noexcept;

 private:
  void record(std::string direction, std::string outcome, std::span<const std::byte> bytes);

  MemoryServer& server_;
  bool connected_{false};
  std::deque<TransportFault> faults_{};
  std::vector<TraceRecord> trace_{};
  std::uint64_t next_sequence_{1};
};

/** Return a stable diagnostic identifier for transport results. */
[[nodiscard]] std::string_view transport_error_name(TransportError error) noexcept;

}  // namespace imlp
