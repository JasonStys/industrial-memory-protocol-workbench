/**
 * @file server.cpp
 * @brief Implements the synthetic simulator's read, opt-in write, and error
 * paths.
 * @details Function and significant variable locations are indexed in the
 * generated symbol index.
 */

#include "imlp/server.hpp"

#include <algorithm>
#include <string_view>
#include <utility>

#include "imlp/codec.hpp"

namespace imlp {
namespace {

/** Convert a stable diagnostic to a bounded protocol payload. */
[[nodiscard]] std::vector<std::byte> text_payload(const std::string_view text) {
  const std::size_t length = std::min(text.size(), maximum_payload_size);
  std::vector<std::byte> bytes;
  bytes.reserve(length);
  for (std::size_t index = 0; index < length; ++index) {
    bytes.push_back(static_cast<std::byte>(static_cast<unsigned char>(text[index])));
  }
  return bytes;
}

}  // namespace

MemoryServer::MemoryServer(const ServerPolicy policy) : policy_(policy) {}

HandleResult MemoryServer::handle(const std::span<const std::byte> request_bytes) {
  const DecodeResult decoded = decode(request_bytes);
  if (!decoded || !decoded.frame.has_value()) {
    return {{},
            {.request_decoded = false,
             .request_id = 0,
             .status = Status::bad_request,
             .detail = std::string(codec_error_name(decoded.error))}};
  }

  const Frame& request = *decoded.frame;
  if (request.opcode == Opcode::read_request) {
    const std::size_t length = (std::to_integer<std::size_t>(request.payload[0]) << 8U) |
                               std::to_integer<std::size_t>(request.payload[1]);
    const MemoryResult result = memory_.read(request.address, length);
    if (result) {
      return make_response(request, Opcode::data_response, Status::ok, result.data, "read_ok");
    }
    return make_response(request, Opcode::error_response, result.status,
                         text_payload("read_rejected"), "read_rejected");
  }

  if (request.opcode == Opcode::write_request) {
    if (!policy_.writes_enabled) {
      return make_response(request, Opcode::error_response, Status::write_disabled,
                           text_payload("write_disabled"), "write_disabled");
    }
    if (!write_is_allowed(request.address, request.payload.size())) {
      return make_response(request, Opcode::error_response, Status::access_denied,
                           text_payload("outside_write_allowlist"), "outside_write_allowlist");
    }
    const Status status = memory_.write(request.address, request.payload);
    if (status != Status::ok) {
      return make_response(request, Opcode::error_response, status,
                           text_payload("memory_write_rejected"), "memory_write_rejected");
    }
    return make_response(request, Opcode::write_acknowledgement, Status::ok, {}, "write_ok");
  }

  return make_response(request, Opcode::error_response, Status::bad_request,
                       text_payload("request_opcode_required"), "request_opcode_required");
}

bool MemoryServer::write_is_allowed(const std::uint32_t address,
                                    const std::size_t length) const noexcept {
  if (length == 0U || address < policy_.write_allow_begin || address > policy_.write_allow_end) {
    return false;
  }
  const auto available = static_cast<std::uint64_t>(policy_.write_allow_end) - address + 1U;
  return static_cast<std::uint64_t>(length) <= available;
}

HandleResult MemoryServer::make_response(const Frame& request, const Opcode opcode,
                                         const Status status, std::vector<std::byte> payload,
                                         std::string detail) const {
  Frame response{
      .version = protocol_version,
      .opcode = opcode,
      .flags = response_flag,
      .request_id = request.request_id,
      .address = request.address,
      .status = status,
      .payload = std::move(payload),
  };
  EncodeResult encoded = encode(response);
  if (!encoded) {
    return {{},
            {.request_decoded = true,
             .request_id = request.request_id,
             .status = Status::internal_error,
             .detail = "response_encoding_failed"}};
  }
  return {std::move(encoded.bytes),
          {.request_decoded = true,
           .request_id = request.request_id,
           .status = status,
           .detail = std::move(detail)}};
}

}  // namespace imlp
