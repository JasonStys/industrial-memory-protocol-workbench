/**
 * @file transport.cpp
 * @brief Implements bounded loopback exchanges, trace capture, and scripted
 * transport faults.
 * @details Function and significant variable locations are indexed in the
 * generated symbol index.
 */

#include "imlp/transport.hpp"

#include <utility>

#include "imlp/codec.hpp"

namespace imlp {

LoopbackTransport::LoopbackTransport(MemoryServer& server) : server_(server) {}

bool LoopbackTransport::connect() {
  connected_ = true;
  return true;
}

void LoopbackTransport::close() noexcept { connected_ = false; }

bool LoopbackTransport::connected() const noexcept { return connected_; }

TransportReply LoopbackTransport::exchange(const std::span<const std::byte> request,
                                           const std::chrono::milliseconds deadline) {
  if (!connected_) return {TransportError::not_connected, {}};
  record("client_to_server", "sent", request);
  if (deadline <= std::chrono::milliseconds::zero()) {
    record("server_to_client", "deadline_expired", {});
    return {TransportError::timeout, {}};
  }

  const bool has_fault = !faults_.empty();
  const TransportFault fault = has_fault ? faults_.front() : TransportFault::timeout;
  if (has_fault) faults_.pop_front();
  if (has_fault && fault == TransportFault::timeout) {
    record("server_to_client", "timeout", {});
    return {TransportError::timeout, {}};
  }
  if (has_fault && fault == TransportFault::disconnect) {
    connected_ = false;
    record("server_to_client", "disconnected", {});
    return {TransportError::disconnected, {}};
  }

  HandleResult handled = server_.handle(request);
  std::vector<std::byte> response = std::move(handled.response);
  if (has_fault && fault == TransportFault::truncate_response && !response.empty()) {
    response.pop_back();
  } else if (has_fault && fault == TransportFault::corrupt_response && !response.empty()) {
    response.back() ^= std::byte{0x01};
  } else if (has_fault && fault == TransportFault::wrong_request_id) {
    DecodeResult decoded = decode(response);
    if (decoded && decoded.frame.has_value()) {
      ++decoded.frame->request_id;
      EncodeResult encoded = encode(*decoded.frame);
      if (encoded) response = std::move(encoded.bytes);
    }
  }

  const std::string outcome = handled.event.request_decoded ? handled.event.detail : "rejected";
  record("server_to_client", outcome, response);
  return {TransportError::none, std::move(response)};
}

void LoopbackTransport::push_fault(const TransportFault fault) { faults_.push_back(fault); }

std::span<const TraceRecord> LoopbackTransport::trace() const noexcept { return trace_; }

void LoopbackTransport::clear_trace() noexcept { trace_.clear(); }

void LoopbackTransport::record(std::string direction, std::string outcome,
                               const std::span<const std::byte> bytes) {
  trace_.push_back({.sequence = next_sequence_++,
                    .direction = std::move(direction),
                    .outcome = std::move(outcome),
                    .bytes = std::vector<std::byte>(bytes.begin(), bytes.end())});
}

std::string_view transport_error_name(const TransportError error) noexcept {
  switch (error) {
    case TransportError::none:
      return "none";
    case TransportError::not_connected:
      return "not_connected";
    case TransportError::timeout:
      return "timeout";
    case TransportError::disconnected:
      return "disconnected";
  }
  return "unknown";
}

}  // namespace imlp
