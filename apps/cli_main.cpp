/**
 * @file cli_main.cpp
 * @brief Provides safe inspection, read, explicit-write, and fault-demo
 * commands for the simulator.
 * @details Command helpers and significant variable locations are indexed in
 * the generated symbol index.
 */

#include <array>
#include <charconv>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <span>
#include <string>
#include <string_view>

#include "imlp/client.hpp"
#include "imlp/codec.hpp"

namespace {

using namespace std::chrono_literals;

/** Print supported commands and the simulator-only safety boundary. */
void print_usage() {
  std::cout << "Industrial Memory Protocol Workbench (synthetic simulator only)\n"
               "usage:\n"
               "  imlp-cli inspect <frame-hex>\n"
               "  imlp-cli encode-read <address> <length>\n"
               "  imlp-cli read <address> <length>\n"
               "  imlp-cli write <address> <payload-hex> --allow-writes\n"
               "  imlp-cli demo\n";
}

/** Parse a complete decimal or 0x-prefixed unsigned 32-bit value. */
[[nodiscard]] bool parse_u32(std::string_view text, std::uint32_t& value) {
  int base = 10;
  if (text.size() > 2U && text.substr(0, 2) == "0x") {
    text.remove_prefix(2);
    base = 16;
  }
  if (text.empty()) return false;
  const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value, base);
  return error == std::errc{} && end == text.data() + text.size();
}

/** Return a stable printable application status. */
[[nodiscard]] std::string_view status_name(const imlp::Status status) noexcept {
  switch (status) {
    case imlp::Status::ok:
      return "ok";
    case imlp::Status::bad_request:
      return "bad_request";
    case imlp::Status::out_of_range:
      return "out_of_range";
    case imlp::Status::write_disabled:
      return "write_disabled";
    case imlp::Status::access_denied:
      return "access_denied";
    case imlp::Status::internal_error:
      return "internal_error";
  }
  return "unknown";
}

/** Print one client result without leaking process or filesystem details. */
void print_result(const imlp::OperationResult& result) {
  std::cout << "request_id=" << result.request_id
            << " client_error=" << imlp::client_error_name(result.error)
            << " remote_status=" << status_name(result.remote_status)
            << " attempts=" << result.attempts << " detail=" << result.detail;
  if (!result.data.empty()) std::cout << " data=" << imlp::bytes_to_hex(result.data);
  std::cout << '\n';
}

/** Print packet-style trace entries with deterministic sequence numbers. */
void print_trace(const std::span<const imlp::TraceRecord> trace) {
  for (const auto& record : trace) {
    std::cout << "trace=" << record.sequence << " direction=" << record.direction
              << " outcome=" << record.outcome << " bytes=" << imlp::bytes_to_hex(record.bytes)
              << '\n';
  }
}

/** Inspect one exact hexadecimal frame and report validated logical fields. */
[[nodiscard]] int run_inspect(const std::string_view text) {
  const auto bytes = imlp::bytes_from_hex(text);
  if (!bytes.has_value()) {
    std::cerr << "error=invalid_hex\n";
    return 2;
  }
  const imlp::DecodeResult decoded = imlp::decode(*bytes);
  if (!decoded || !decoded.frame.has_value()) {
    std::cerr << "error=" << imlp::codec_error_name(decoded.error) << '\n';
    return 3;
  }
  const imlp::Frame& frame = *decoded.frame;
  std::cout << "version=" << static_cast<unsigned int>(frame.version) << " opcode=0x" << std::hex
            << static_cast<unsigned int>(frame.opcode) << std::dec
            << " flags=" << static_cast<unsigned int>(frame.flags)
            << " request_id=" << frame.request_id << " address=" << frame.address
            << " status=" << status_name(frame.status)
            << " payload=" << imlp::bytes_to_hex(frame.payload) << '\n';
  return 0;
}

/** Encode one bounded read request for use as a documented test vector. */
[[nodiscard]] int run_encode_read(const std::string_view address_text,
                                  const std::string_view length_text) {
  std::uint32_t address = 0;
  std::uint32_t length = 0;
  if (!parse_u32(address_text, address) || !parse_u32(length_text, length) || length == 0U ||
      length > imlp::maximum_payload_size) {
    std::cerr << "error=invalid_address_or_length\n";
    return 2;
  }
  const auto wire_length = static_cast<std::uint16_t>(length);
  const imlp::Frame request{
      .opcode = imlp::Opcode::read_request,
      .request_id = 1,
      .address = address,
      .payload = {static_cast<std::byte>((wire_length >> 8U) & 0xFFU),
                  static_cast<std::byte>(wire_length & 0xFFU)},
  };
  const imlp::EncodeResult encoded = imlp::encode(request);
  if (!encoded) {
    std::cerr << "error=" << imlp::codec_error_name(encoded.error) << '\n';
    return 3;
  }
  std::cout << imlp::bytes_to_hex(encoded.bytes) << '\n';
  return 0;
}

/** Run a simulated read using default read-only server policy. */
[[nodiscard]] int run_read(const std::string_view address_text,
                           const std::string_view length_text) {
  std::uint32_t address = 0;
  std::uint32_t length = 0;
  if (!parse_u32(address_text, address) || !parse_u32(length_text, length)) {
    std::cerr << "error=invalid_address_or_length\n";
    return 2;
  }
  imlp::MemoryServer server;
  imlp::LoopbackTransport transport(server);
  imlp::Client client(transport);
  const imlp::OperationResult result = client.read(address, length, 100ms);
  print_result(result);
  print_trace(transport.trace());
  return result ? 0 : 4;
}

/** Run an explicitly enabled simulated write; policy remains enforced inside
 * the server. */
[[nodiscard]] int run_write(const std::string_view address_text,
                            const std::string_view payload_text,
                            const std::string_view confirmation) {
  std::uint32_t address = 0;
  const auto payload = imlp::bytes_from_hex(payload_text);
  if (!parse_u32(address_text, address) || !payload.has_value() || payload->empty() ||
      confirmation != "--allow-writes") {
    std::cerr << "error=invalid_write_or_missing_explicit_opt_in\n";
    return 2;
  }
  imlp::MemoryServer server({.writes_enabled = true});
  imlp::LoopbackTransport transport(server);
  imlp::Client client(transport);
  const imlp::OperationResult result = client.write(address, *payload, 100ms);
  print_result(result);
  print_trace(transport.trace());
  return result ? 0 : 4;
}

/** Demonstrate normal reads, denied writes, retry, corruption, and opt-in
 * writes. */
[[nodiscard]] int run_demo() {
  std::cout << "scenario=read_only_default\n";
  imlp::MemoryServer read_only_server;
  imlp::LoopbackTransport transport(read_only_server);
  imlp::Client client(transport);
  print_result(client.read(0x0000U, 12U, 100ms));
  const std::array<std::byte, 2> sample{std::byte{0x12}, std::byte{0x34}};
  print_result(client.write(0x0100U, sample, 100ms));

  std::cout << "scenario=transient_read_timeout\n";
  transport.push_fault(imlp::TransportFault::timeout);
  print_result(client.read(0x0040U, 1U, 100ms));

  std::cout << "scenario=corrupted_response\n";
  transport.push_fault(imlp::TransportFault::corrupt_response);
  print_result(client.read(0x0000U, 4U, 100ms));
  print_trace(transport.trace());

  std::cout << "scenario=explicit_write_opt_in\n";
  imlp::MemoryServer writable_server({.writes_enabled = true});
  imlp::LoopbackTransport writable_transport(writable_server);
  imlp::Client writable_client(writable_transport);
  print_result(writable_client.write(0x0100U, sample, 100ms));
  print_result(writable_client.read(0x0100U, sample.size(), 100ms));
  return 0;
}

}  // namespace

/** Dispatch validated command-line input without connecting to physical
 * equipment. */
int main(const int argc, const char* const argv[]) {
  if (argc < 2) {
    print_usage();
    return 1;
  }
  const std::string_view command = argv[1];
  if (command == "inspect" && argc == 3) return run_inspect(argv[2]);
  if (command == "encode-read" && argc == 4) return run_encode_read(argv[2], argv[3]);
  if (command == "read" && argc == 4) return run_read(argv[2], argv[3]);
  if (command == "write" && argc == 5) return run_write(argv[2], argv[3], argv[4]);
  if (command == "demo" && argc == 2) return run_demo();
  print_usage();
  return 1;
}
