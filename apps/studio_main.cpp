/**
 * @file studio_main.cpp
 * @brief Runs bounded offline editable sessions, exact-frame reviews and stream inspection.
 * @details Reuses the original codec, client, server and stream decoder. Input is fixed-layout
 * local stdin IPC, never a device endpoint, path or command. Symbols:
 * docs/generated/symbol-index.md.
 */

#include <array>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <iostream>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

#include "imlp/client.hpp"
#include "imlp/codec.hpp"
#include "imlp/stream_decoder.hpp"

#ifndef IMLP_APP_VERSION
#error "The application version must come from CMake"
#endif
#ifndef IMLP_SOURCE_SHA
#error "The source identity must come from CMake"
#endif

namespace {

constexpr std::size_t maximum_input = 256U * 1024U;
constexpr std::string_view control_magic = "IMLPS1\n";

/** Decode the closed IPC envelope with subtraction-first bounds before allocating payloads. */
class Input {
 public:
  explicit Input(const std::span<const std::byte> input) : input_(input) {}

  [[nodiscard]] std::vector<std::byte> take(const std::size_t count) {
    if (count > input_.size() - position_) throw std::invalid_argument("truncated control input");
    const auto first = input_.begin() + static_cast<std::ptrdiff_t>(position_);
    position_ += count;
    return {first, first + static_cast<std::ptrdiff_t>(count)};
  }

  [[nodiscard]] std::uint8_t byte() {
    if (position_ == input_.size()) throw std::invalid_argument("truncated control number");
    return std::to_integer<std::uint8_t>(input_[position_++]);
  }

  [[nodiscard]] std::uint16_t u16() {
    const auto high = static_cast<std::uint16_t>(byte());
    return static_cast<std::uint16_t>((high << 8U) | byte());
  }

  [[nodiscard]] std::uint32_t u32() {
    std::uint32_t value = 0;
    for (unsigned int part = 0; part < 4U; ++part) value = (value << 8U) | byte();
    return value;
  }

  [[nodiscard]] bool done() const noexcept { return position_ == input_.size(); }

 private:
  std::span<const std::byte> input_;
  std::size_t position_{};
};

/** One operation retains the queued faults; unconsumed faults intentionally carry forward. */
struct Operation {
  bool write{};
  std::uint32_t address{};
  std::size_t length{};
  std::chrono::milliseconds deadline{};
  std::vector<imlp::TransportFault> faults;
  std::vector<std::byte> payload;
};

/** Validate the complete request before constructing any simulator state. */
struct Request {
  std::uint8_t mode{};
  imlp::ServerPolicy policy;
  std::size_t attempts{};
  std::vector<Operation> operations;
  std::vector<std::vector<std::byte>> chunks;
  std::vector<std::byte> exact;
  imlp::Frame frame;
};

/** Only five declared deterministic loopback faults exist; no host action is representable. */
[[nodiscard]] imlp::TransportFault fault(const std::uint8_t value) {
  switch (value) {
    case 1:
      return imlp::TransportFault::timeout;
    case 2:
      return imlp::TransportFault::disconnect;
    case 3:
      return imlp::TransportFault::truncate_response;
    case 4:
      return imlp::TransportFault::corrupt_response;
    case 5:
      return imlp::TransportFault::wrong_request_id;
    default:
      throw std::invalid_argument("unknown loopback fault");
  }
}

/** Parse versioned binary control fields independently of the application's JSON validator. */
[[nodiscard]] Request parse(const std::span<const std::byte> raw) {
  Input input(raw);
  for (const char expected : control_magic) {
    if (input.byte() != static_cast<std::uint8_t>(expected))
      throw std::invalid_argument("wrong control header");
  }
  Request request;
  request.mode = input.byte();
  if (request.mode == 1U) {
    const auto enabled = input.byte();
    if (enabled > 1U) throw std::invalid_argument("invalid write permission");
    request.policy.writes_enabled = enabled == 1U;
    request.policy.write_allow_begin = input.u32();
    request.policy.write_allow_end = input.u32();
    request.attempts = input.byte();
    const auto count = input.u16();
    if (request.policy.write_allow_begin > request.policy.write_allow_end ||
        request.attempts < 1U || request.attempts > 3U || count < 1U || count > 64U)
      throw std::invalid_argument("invalid session bounds");
    for (std::size_t index = 0; index < count; ++index) {
      Operation operation;
      const auto verb = input.byte();
      if (verb != 1U && verb != 2U) throw std::invalid_argument("unknown session operation");
      operation.write = verb == 2U;
      operation.address = input.u32();
      operation.length = input.u16();
      operation.deadline = std::chrono::milliseconds(input.u16());
      const auto fault_count = input.byte();
      if (operation.length > imlp::maximum_payload_size || operation.deadline.count() > 1000 ||
          fault_count > 3U)
        throw std::invalid_argument("invalid operation bounds");
      for (std::size_t item = 0; item < fault_count; ++item)
        operation.faults.push_back(fault(input.byte()));
      if (operation.write) operation.payload = input.take(operation.length);
      request.operations.push_back(std::move(operation));
    }
  } else if (request.mode == 2U) {
    const auto count = input.u16();
    if (count < 1U || count > 256U) throw std::invalid_argument("invalid stream chunk count");
    std::size_t total = 0;
    for (std::size_t index = 0; index < count; ++index) {
      const auto size = input.u16();
      if (size > imlp::maximum_stream_chunk || size > imlp::maximum_stream_bytes - total)
        throw std::invalid_argument("invalid stream byte bounds");
      total += size;
      request.chunks.push_back(input.take(size));
    }
  } else if (request.mode == 3U) {
    const auto size = input.u16();
    if (size > imlp::maximum_frame_size) throw std::invalid_argument("invalid exact frame bound");
    request.exact = input.take(size);
  } else if (request.mode == 4U) {
    request.frame.version = input.byte();
    request.frame.opcode = static_cast<imlp::Opcode>(input.byte());
    request.frame.flags = input.byte();
    request.frame.request_id = input.u32();
    request.frame.address = input.u32();
    request.frame.status = static_cast<imlp::Status>(input.u16());
    const auto size = input.u16();
    if (size > imlp::maximum_payload_size)
      throw std::invalid_argument("invalid frame payload bound");
    request.frame.payload = input.take(size);
  } else {
    throw std::invalid_argument("unknown review mode");
  }
  if (!input.done()) throw std::invalid_argument("trailing control bytes");
  return request;
}

/** JSON-escape text; user bytes are always separately rendered as bounded lowercase hex. */
void quote(std::ostream& out, const std::string_view text) {
  constexpr std::string_view digits = "0123456789abcdef";
  out << '"';
  for (const char character : text) {
    const auto value = static_cast<unsigned char>(character);
    if (character == '"' || character == '\\')
      out << '\\' << character;
    else if (value < 32U)
      out << "\\u00" << digits[value >> 4U] << digits[value & 0x0FU];
    else
      out << character;
  }
  out << '"';
}

/** Retain all actual wire fields without interpreting CRC as authentication. */
void frame_json(std::ostream& out, const imlp::Frame& frame) {
  out << "{\"version\":" << static_cast<unsigned int>(frame.version)
      << ",\"opcode\":" << static_cast<unsigned int>(frame.opcode)
      << ",\"flags\":" << static_cast<unsigned int>(frame.flags)
      << ",\"request_id\":" << frame.request_id << ",\"address\":" << frame.address
      << ",\"status\":" << static_cast<unsigned int>(frame.status) << ",\"payload_hex\":";
  quote(out, imlp::bytes_to_hex(frame.payload));
  out << '}';
}

/** An affected range can be unreadable; that status remains explicit rather than fabricated bytes.
 */
void memory_json(std::ostream& out, const imlp::MemoryResult& result) {
  out << "{\"status\":" << static_cast<unsigned int>(result.status) << ",\"hex\":";
  quote(out, imlp::bytes_to_hex(result.data));
  out << '}';
}

/** Snapshot the whole readable simulator region through its original bounded read API. */
[[nodiscard]] std::string readable_memory(const imlp::MemoryMap& memory) {
  std::string result;
  for (std::uint32_t address = 0; address < 0x800U; address += 256U) {
    const auto part = memory.read(address, 256U);
    if (!part) throw std::runtime_error("original readable map invariant failed");
    result += imlp::bytes_to_hex(part.data);
  }
  return result;
}

/** Render actual cumulative client counters alongside exact original transport traces. */
void metrics_json(std::ostream& out, const imlp::ClientMetrics& metrics) {
  out << "{\"operations\":" << metrics.operations
      << ",\"transport_attempts\":" << metrics.transport_attempts
      << ",\"reconnects\":" << metrics.reconnects << ",\"retries\":" << metrics.retries
      << ",\"timeouts\":" << metrics.timeouts << ",\"protocol_errors\":" << metrics.protocol_errors
      << '}';
}

/** A single real server survives every operation in this run; writes are not silently reseeded. */
void session(std::ostream& out, const Request& request) {
  imlp::MemoryServer server(request.policy);
  imlp::LoopbackTransport transport(server);
  imlp::Client client(transport, {.maximum_read_attempts = request.attempts});
  out << ",\"kind\":\"session\",\"initial_readable_hex\":";
  quote(out, readable_memory(server.memory()));
  out << ",\"operations\":[";
  for (std::size_t index = 0; index < request.operations.size(); ++index) {
    const auto& operation = request.operations[index];
    if (index != 0U) out << ',';
    for (const auto selected : operation.faults) transport.push_fault(selected);
    const auto before = server.memory().read(operation.address, operation.length);
    const auto begin = transport.trace().size();
    const auto result = operation.write
                            ? client.write(operation.address, operation.payload, operation.deadline)
                            : client.read(operation.address, operation.length, operation.deadline);
    const auto after = server.memory().read(operation.address, operation.length);
    out << "{\"index\":" << index << ",\"verb\":\"" << (operation.write ? "write" : "read")
        << "\",\"request_id\":" << result.request_id << ",\"attempts\":" << result.attempts
        << ",\"client_error\":";
    quote(out, imlp::client_error_name(result.error));
    out << ",\"remote_status\":" << static_cast<unsigned int>(result.remote_status)
        << ",\"data_hex\":";
    quote(out, imlp::bytes_to_hex(result.data));
    out << ",\"detail\":";
    quote(out, result.detail);
    out << ",\"trace_begin\":" << begin << ",\"trace_end\":" << transport.trace().size()
        << ",\"before\":";
    memory_json(out, before);
    out << ",\"after\":";
    memory_json(out, after);
    out << '}';
  }
  out << "],\"final_readable_hex\":";
  quote(out, readable_memory(server.memory()));
  out << ",\"metrics\":";
  metrics_json(out, client.metrics());
  out << ",\"trace\":[";
  const auto trace = transport.trace();
  for (std::size_t index = 0; index < trace.size(); ++index) {
    if (index != 0U) out << ',';
    const auto& record = trace[index];
    out << "{\"sequence\":" << record.sequence << ",\"direction\":";
    quote(out, record.direction);
    out << ",\"outcome\":";
    quote(out, record.outcome);
    out << ",\"hex\":";
    quote(out, imlp::bytes_to_hex(record.bytes));
    out << '}';
  }
  out << ']';
}

/** Feed the original bounded stream engine; cap cross-feed diagnostics without dropping byte
 * totals. */
void stream(std::ostream& out, const Request& request) {
  imlp::StreamDecoder decoder;
  imlp::StreamBatch combined;
  std::size_t total = 0;
  const auto retain = [&combined](imlp::StreamBatch batch) {
    combined.frames.insert(combined.frames.end(), batch.frames.begin(), batch.frames.end());
    combined.omitted_issue_records += batch.omitted_issue_records;
    combined.omitted_issue_bytes += batch.omitted_issue_bytes;
    for (const auto& issue : batch.issues) {
      if (combined.issues.size() < imlp::maximum_stream_issues)
        combined.issues.push_back(issue);
      else {
        ++combined.omitted_issue_records;
        combined.omitted_issue_bytes += issue.bytes;
      }
    }
  };
  for (const auto& chunk : request.chunks) {
    total += chunk.size();
    retain(decoder.feed(chunk));
  }
  retain(decoder.finish());
  out << ",\"kind\":\"stream\",\"input_bytes\":" << total << ",\"frames\":[";
  for (std::size_t index = 0; index < combined.frames.size(); ++index) {
    if (index != 0U) out << ',';
    const auto& record = combined.frames[index];
    const auto encoded = imlp::encode(record.frame);
    if (!encoded) throw std::runtime_error("accepted frame cannot be reencoded");
    out << "{\"offset\":" << record.offset << ",\"wire_bytes\":" << record.wire_bytes
        << ",\"hex\":";
    quote(out, imlp::bytes_to_hex(encoded.bytes));
    out << ",\"frame\":";
    frame_json(out, record.frame);
    out << '}';
  }
  out << "],\"issues\":[";
  for (std::size_t index = 0; index < combined.issues.size(); ++index) {
    if (index != 0U) out << ',';
    const auto& issue = combined.issues[index];
    out << "{\"offset\":" << issue.offset << ",\"bytes\":" << issue.bytes << ",\"error\":";
    quote(out, imlp::codec_error_name(issue.error));
    out << '}';
  }
  out << "],\"omitted_issue_records\":" << combined.omitted_issue_records
      << ",\"omitted_issue_bytes\":" << combined.omitted_issue_bytes
      << ",\"pending_bytes\":" << decoder.pending_bytes();
}

/** Exact decoder and encoder refusals are domain evidence, not process success fabrication. */
void exact_frame(std::ostream& out, const Request& request) {
  const auto encoded = request.mode == 4U ? imlp::encode(request.frame) : imlp::EncodeResult{};
  const auto decoded = request.mode == 3U ? imlp::decode(request.exact) : imlp::DecodeResult{};
  const bool accepted =
      request.mode == 3U ? static_cast<bool>(decoded) : static_cast<bool>(encoded);
  const auto error = request.mode == 3U ? decoded.error : encoded.error;
  out << ",\"kind\":\"" << (request.mode == 3U ? "inspect" : "compose")
      << "\",\"accepted\":" << (accepted ? "true" : "false") << ",\"error\":";
  quote(out, imlp::codec_error_name(error));
  out << ",\"hex\":";
  quote(out, imlp::bytes_to_hex(request.mode == 3U ? request.exact : encoded.bytes));
  out << ",\"frame\":";
  if (!accepted)
    out << "null";
  else if (request.mode == 3U) {
    if (!decoded.frame.has_value())
      throw std::logic_error("accepted decode without a retained frame");
    frame_json(out, decoded.frame.value());
  } else
    frame_json(out, request.frame);
}

/** Every response binds the actual product/version/source and exact consumed control-envelope CRC.
 */
void identity(std::ostream& out) {
  out << "{\"bridge_version\":1,\"product\":\"industrial-memory-protocol-workbench\",\"version\":";
  quote(out, IMLP_APP_VERSION);
  out << ",\"source_commit\":";
  quote(out, IMLP_SOURCE_SHA);
}

}  // namespace

/** Consume only bounded parent-owned stdin, render one complete JSON document, and never open
 * hardware. */
int main(const int argc, const char* const argv[]) {
  try {
    if (argc == 2 && std::string_view(argv[1]) == "version") {
      identity(std::cout);
      std::cout << "}\n";
      return 0;
    }
    if (argc != 2 || std::string_view(argv[1]) != "run") return 2;
#ifdef _WIN32
    // Preserve0x1a and CR/LF in actual inert payload bytes instead of Windows text translation.
    if (_setmode(_fileno(stdin), _O_BINARY) == -1) throw std::runtime_error("binary stdin failed");
#endif
    std::array<char, maximum_input + 1U> storage{};
    std::cin.read(storage.data(), static_cast<std::streamsize>(storage.size()));
    const auto count = static_cast<std::size_t>(std::cin.gcount());
    if (std::cin.bad() || count > maximum_input) throw std::invalid_argument("control byte budget");
    const auto raw = std::as_bytes(std::span(storage.data(), count));
    const auto request = parse(raw);
    std::ostringstream out;
    identity(out);
    out << ",\"input_crc32\":" << imlp::crc32(raw);
    if (request.mode == 1U)
      session(out, request);
    else if (request.mode == 2U)
      stream(out, request);
    else
      exact_frame(out, request);
    out << "}\n";
    const auto result = out.str();
    if (result.size() > 8U * 1024U * 1024U) throw std::runtime_error("result byte budget");
    std::cout << result;
    return 0;
  } catch (const std::exception&) {
    std::cerr << "invalid or unsupported bounded studio input\n";
    return 2;
  }
}
