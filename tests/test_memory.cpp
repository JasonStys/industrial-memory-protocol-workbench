/**
 * @file test_memory.cpp
 * @brief Verifies memory-region boundaries, server write policy, and
 * malformed-request handling.
 * @details Test function locations are indexed in
 * docs/generated/symbol-index.md.
 */

#include <cstddef>
#include <vector>

#include "imlp/codec.hpp"
#include "imlp/memory_map.hpp"
#include "imlp/server.hpp"
#include "test_harness.hpp"

namespace {

/** Encode a frame and fail the current test if construction is invalid. */
[[nodiscard]] std::vector<std::byte> encoded_bytes(const imlp::Frame& frame) {
  const imlp::EncodeResult encoded = imlp::encode(frame);
  IMLP_EXPECT(encoded);
  return encoded.bytes;
}

/** Decode a server response and return its required frame. */
[[nodiscard]] imlp::Frame response_frame(const imlp::HandleResult& result) {
  const imlp::DecodeResult decoded = imlp::decode(result.response);
  IMLP_EXPECT(decoded);
  return *decoded.frame;
}

IMLP_TEST(memory_map_enforces_regions_and_range_boundaries) {
  imlp::MemoryMap memory;
  IMLP_EXPECT_EQ(imlp::MemoryMap::access_for(0x0000U), imlp::Access::read_only);
  IMLP_EXPECT_EQ(imlp::MemoryMap::access_for(0x0100U), imlp::Access::read_write);
  IMLP_EXPECT_EQ(imlp::MemoryMap::access_for(0x0800U), imlp::Access::denied);
  IMLP_EXPECT(memory.read(0U, 8U));
  IMLP_EXPECT_EQ(memory.read(0x0800U, 1U).status, imlp::Status::access_denied);
  IMLP_EXPECT_EQ(memory.read(0xFFFFFFFFU, 2U).status, imlp::Status::out_of_range);
  IMLP_EXPECT_EQ(memory.read(0U, 0U).status, imlp::Status::out_of_range);
}

IMLP_TEST(memory_map_rejects_read_only_and_cross_region_writes) {
  imlp::MemoryMap memory;
  const std::vector<std::byte> bytes{std::byte{0x11}, std::byte{0x22}};
  IMLP_EXPECT_EQ(memory.write(0x0000U, bytes), imlp::Status::access_denied);
  IMLP_EXPECT_EQ(memory.write(0x0100U, bytes), imlp::Status::ok);
  IMLP_EXPECT_EQ(memory.read(0x0100U, bytes.size()).data, bytes);
  IMLP_EXPECT_EQ(memory.write(0x07FFU, bytes), imlp::Status::access_denied);
}

IMLP_TEST(server_defaults_to_read_only_and_returns_correlated_error) {
  imlp::MemoryServer server;
  const imlp::Frame request{
      .opcode = imlp::Opcode::write_request,
      .request_id = 42,
      .address = 0x0100U,
      .payload = {std::byte{0xAB}},
  };
  const imlp::HandleResult handled = server.handle(encoded_bytes(request));
  const imlp::Frame response = response_frame(handled);
  IMLP_EXPECT_EQ(response.opcode, imlp::Opcode::error_response);
  IMLP_EXPECT_EQ(response.status, imlp::Status::write_disabled);
  IMLP_EXPECT_EQ(response.request_id, request.request_id);
}

IMLP_TEST(server_allows_only_explicitly_enabled_allowlisted_writes) {
  imlp::MemoryServer server(
      {.writes_enabled = true, .write_allow_begin = 0x0120U, .write_allow_end = 0x012FU});
  const imlp::Frame allowed{
      .opcode = imlp::Opcode::write_request,
      .request_id = 1,
      .address = 0x0120U,
      .payload = {std::byte{0xAB}, std::byte{0xCD}},
  };
  IMLP_EXPECT_EQ(response_frame(server.handle(encoded_bytes(allowed))).status, imlp::Status::ok);

  imlp::Frame denied = allowed;
  denied.request_id = 2;
  denied.address = 0x011FU;
  IMLP_EXPECT_EQ(response_frame(server.handle(encoded_bytes(denied))).status,
                 imlp::Status::access_denied);

  denied.request_id = 3;
  denied.address = 0x012FU;
  IMLP_EXPECT_EQ(response_frame(server.handle(encoded_bytes(denied))).status,
                 imlp::Status::access_denied);
}

IMLP_TEST(server_returns_no_frame_for_undecodable_input) {
  imlp::MemoryServer server;
  const std::vector<std::byte> malformed{std::byte{0x49}, std::byte{0x4D}, std::byte{1}};
  const imlp::HandleResult result = server.handle(malformed);
  IMLP_EXPECT(result.response.empty());
  IMLP_EXPECT(!result.event.request_decoded);
  IMLP_EXPECT_EQ(result.event.status, imlp::Status::bad_request);
}

}  // namespace
