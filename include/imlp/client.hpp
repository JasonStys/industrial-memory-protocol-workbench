/**
 * @file client.hpp
 * @brief Declares the correlation-aware client, bounded read retry policy, and
 * metrics.
 * @details Exact declarations and line locations are generated in
 * docs/generated/symbol-index.md.
 */

#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "imlp/transport.hpp"

namespace imlp {

/** Distinguishes client validation, transport, protocol, and remote application
 * failures. */
enum class ClientError {
  none,
  invalid_argument,
  connect_failed,
  timeout,
  disconnected,
  encoding_failed,
  malformed_response,
  correlation_mismatch,
  unexpected_response,
  remote_error,
};

/** Limits attempts for idempotent reads; writes are never retried implicitly.
 */
struct ClientOptions {
  std::size_t maximum_read_attempts{2};
};

/** Makes retry and failure behavior observable to tests and operators. */
struct ClientMetrics {
  std::uint64_t operations{0};
  std::uint64_t transport_attempts{0};
  std::uint64_t reconnects{0};
  std::uint64_t retries{0};
  std::uint64_t timeouts{0};
  std::uint64_t protocol_errors{0};
};

/** Returns one operation result without exceptions crossing the protocol
 * boundary. */
struct OperationResult {
  ClientError error{ClientError::none};
  Status remote_status{Status::ok};
  std::uint32_t request_id{0};
  std::size_t attempts{0};
  std::vector<std::byte> data{};
  std::string detail{};

  [[nodiscard]] explicit operator bool() const noexcept { return error == ClientError::none; }
};

/** Issues validated requests over an injected transport and enforces retry
 * semantics. */
class Client {
 public:
  explicit Client(ITransport& transport, ClientOptions options = {});

  /** Read one bounded range; transient transport failures may reuse the same
   * request ID. */
  [[nodiscard]] OperationResult read(std::uint32_t address, std::size_t length,
                                     std::chrono::milliseconds deadline);

  /** Write once with no implicit retry because the remote side effect may have
   * occurred. */
  [[nodiscard]] OperationResult write(std::uint32_t address, std::span<const std::byte> data,
                                      std::chrono::milliseconds deadline);

  /** Return cumulative counters without allowing external mutation. */
  [[nodiscard]] const ClientMetrics& metrics() const noexcept { return metrics_; }

 private:
  [[nodiscard]] std::uint32_t allocate_request_id() noexcept;
  [[nodiscard]] OperationResult execute_read(const Frame& request, std::size_t expected_length,
                                             std::chrono::milliseconds deadline);
  [[nodiscard]] OperationResult execute_write(const Frame& request,
                                              std::chrono::milliseconds deadline);
  [[nodiscard]] OperationResult validate_response(const Frame& request,
                                                  std::span<const std::byte> response,
                                                  Opcode expected_opcode,
                                                  std::size_t expected_length,
                                                  std::size_t attempts);
  [[nodiscard]] bool ensure_connected();

  ITransport& transport_;
  ClientOptions options_;
  ClientMetrics metrics_{};
  std::uint32_t next_request_id_{1};
};

/** Return a stable diagnostic identifier for client results. */
[[nodiscard]] std::string_view client_error_name(ClientError error) noexcept;

}  // namespace imlp
