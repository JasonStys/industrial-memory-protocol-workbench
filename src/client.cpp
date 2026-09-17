/**
 * @file client.cpp
 * @brief Implements bounded read retries, single-attempt writes, and response
 * correlation checks.
 * @details Function and significant variable locations are indexed in the
 * generated symbol index.
 */

#include "imlp/client.hpp"

#include <algorithm>
#include <utility>

#include "imlp/codec.hpp"

namespace imlp {

Client::Client(ITransport& transport, ClientOptions options)
    : transport_(transport), options_(options) {
  options_.maximum_read_attempts = std::max<std::size_t>(1U, options_.maximum_read_attempts);
}

OperationResult Client::read(const std::uint32_t address, const std::size_t length,
                             const std::chrono::milliseconds deadline) {
  ++metrics_.operations;
  const std::uint32_t request_id = allocate_request_id();
  if (length == 0U || length > maximum_payload_size ||
      deadline <= std::chrono::milliseconds::zero()) {
    return {.error = ClientError::invalid_argument,
            .request_id = request_id,
            .detail = "read length and deadline must be positive and bounded"};
  }
  const auto wire_length = static_cast<std::uint16_t>(length);
  Frame request{
      .opcode = Opcode::read_request,
      .request_id = request_id,
      .address = address,
      .payload = {static_cast<std::byte>((wire_length >> 8U) & 0xFFU),
                  static_cast<std::byte>(wire_length & 0xFFU)},
  };
  return execute_read(request, length, deadline);
}

OperationResult Client::write(const std::uint32_t address, const std::span<const std::byte> data,
                              const std::chrono::milliseconds deadline) {
  ++metrics_.operations;
  const std::uint32_t request_id = allocate_request_id();
  if (data.empty() || data.size() > maximum_payload_size ||
      deadline <= std::chrono::milliseconds::zero()) {
    return {.error = ClientError::invalid_argument,
            .request_id = request_id,
            .detail = "write payload and deadline must be positive and bounded"};
  }
  Frame request{
      .opcode = Opcode::write_request,
      .request_id = request_id,
      .address = address,
      .payload = std::vector<std::byte>(data.begin(), data.end()),
  };
  return execute_write(request, deadline);
}

std::uint32_t Client::allocate_request_id() noexcept {
  const std::uint32_t allocated = next_request_id_++;
  if (next_request_id_ == 0U) next_request_id_ = 1U;
  return allocated;
}

OperationResult Client::execute_read(const Frame& request, const std::size_t expected_length,
                                     const std::chrono::milliseconds deadline) {
  const EncodeResult encoded = encode(request);
  if (!encoded) {
    return {.error = ClientError::encoding_failed,
            .request_id = request.request_id,
            .detail = std::string(codec_error_name(encoded.error))};
  }

  for (std::size_t attempt = 1; attempt <= options_.maximum_read_attempts; ++attempt) {
    if (!ensure_connected()) {
      return {.error = ClientError::connect_failed,
              .request_id = request.request_id,
              .attempts = attempt,
              .detail = "transport connect failed"};
    }
    ++metrics_.transport_attempts;
    TransportReply reply = transport_.exchange(encoded.bytes, deadline);
    if (reply) {
      return validate_response(request, reply.bytes, Opcode::data_response, expected_length,
                               attempt);
    }

    if (reply.error == TransportError::timeout) ++metrics_.timeouts;
    const bool can_retry =
        attempt < options_.maximum_read_attempts &&
        (reply.error == TransportError::timeout || reply.error == TransportError::disconnected ||
         reply.error == TransportError::not_connected);
    transport_.close();
    if (can_retry) {
      ++metrics_.retries;
      continue;
    }
    const ClientError error =
        reply.error == TransportError::timeout ? ClientError::timeout : ClientError::disconnected;
    return {.error = error,
            .request_id = request.request_id,
            .attempts = attempt,
            .detail = std::string(transport_error_name(reply.error))};
  }
  return {.error = ClientError::disconnected,
          .request_id = request.request_id,
          .attempts = options_.maximum_read_attempts,
          .detail = "read attempts exhausted"};
}

OperationResult Client::execute_write(const Frame& request,
                                      const std::chrono::milliseconds deadline) {
  const EncodeResult encoded = encode(request);
  if (!encoded) {
    return {.error = ClientError::encoding_failed,
            .request_id = request.request_id,
            .detail = std::string(codec_error_name(encoded.error))};
  }
  if (!ensure_connected()) {
    return {.error = ClientError::connect_failed,
            .request_id = request.request_id,
            .attempts = 1,
            .detail = "transport connect failed"};
  }
  ++metrics_.transport_attempts;
  TransportReply reply = transport_.exchange(encoded.bytes, deadline);
  if (!reply) {
    if (reply.error == TransportError::timeout) ++metrics_.timeouts;
    transport_.close();
    const ClientError error =
        reply.error == TransportError::timeout ? ClientError::timeout : ClientError::disconnected;
    return {.error = error,
            .request_id = request.request_id,
            .attempts = 1,
            .detail = "write not retried: " + std::string(transport_error_name(reply.error))};
  }
  return validate_response(request, reply.bytes, Opcode::write_acknowledgement, 0, 1);
}

OperationResult Client::validate_response(const Frame& request,
                                          const std::span<const std::byte> response,
                                          const Opcode expected_opcode,
                                          const std::size_t expected_length,
                                          const std::size_t attempts) {
  const DecodeResult decoded = decode(response);
  if (!decoded || !decoded.frame.has_value()) {
    ++metrics_.protocol_errors;
    return {.error = ClientError::malformed_response,
            .request_id = request.request_id,
            .attempts = attempts,
            .detail = std::string(codec_error_name(decoded.error))};
  }
  Frame frame = *decoded.frame;
  if (frame.request_id != request.request_id || frame.address != request.address) {
    ++metrics_.protocol_errors;
    return {.error = ClientError::correlation_mismatch,
            .remote_status = frame.status,
            .request_id = request.request_id,
            .attempts = attempts,
            .detail = "response request ID or address did not match"};
  }
  if (frame.opcode == Opcode::error_response) {
    return {.error = ClientError::remote_error,
            .remote_status = frame.status,
            .request_id = request.request_id,
            .attempts = attempts,
            .data = std::move(frame.payload),
            .detail = "remote request rejected"};
  }
  if (frame.opcode != expected_opcode || frame.payload.size() != expected_length) {
    ++metrics_.protocol_errors;
    return {.error = ClientError::unexpected_response,
            .remote_status = frame.status,
            .request_id = request.request_id,
            .attempts = attempts,
            .detail = "response opcode or payload length did not match"};
  }
  return {.error = ClientError::none,
          .remote_status = frame.status,
          .request_id = request.request_id,
          .attempts = attempts,
          .data = std::move(frame.payload),
          .detail = "ok"};
}

bool Client::ensure_connected() {
  if (transport_.connected()) return true;
  ++metrics_.reconnects;
  return transport_.connect();
}

std::string_view client_error_name(const ClientError error) noexcept {
  switch (error) {
    case ClientError::none:
      return "none";
    case ClientError::invalid_argument:
      return "invalid_argument";
    case ClientError::connect_failed:
      return "connect_failed";
    case ClientError::timeout:
      return "timeout";
    case ClientError::disconnected:
      return "disconnected";
    case ClientError::encoding_failed:
      return "encoding_failed";
    case ClientError::malformed_response:
      return "malformed_response";
    case ClientError::correlation_mismatch:
      return "correlation_mismatch";
    case ClientError::unexpected_response:
      return "unexpected_response";
    case ClientError::remote_error:
      return "remote_error";
  }
  return "unknown";
}

}  // namespace imlp
