/**
 * @file test_client.cpp
 * @brief Verifies retry, no-retry, correlation, malformed response, and
 * remote-error behavior.
 * @details Test function locations are indexed in
 * docs/generated/symbol-index.md.
 */

#include <array>
#include <chrono>
#include <cstddef>

#include "imlp/client.hpp"
#include "imlp/codec.hpp"
#include "test_harness.hpp"

namespace {

using namespace std::chrono_literals;

IMLP_TEST(client_reads_identity_and_reports_metrics) {
  imlp::MemoryServer server;
  imlp::LoopbackTransport transport(server);
  imlp::Client client(transport);
  const imlp::OperationResult result = client.read(0U, 4U, 100ms);
  IMLP_EXPECT(result);
  IMLP_EXPECT_EQ(imlp::bytes_to_hex(result.data), std::string("494d4c50"));
  IMLP_EXPECT_EQ(result.attempts, 1U);
  IMLP_EXPECT_EQ(client.metrics().operations, 1U);
  IMLP_EXPECT_EQ(client.metrics().transport_attempts, 1U);
}

IMLP_TEST(client_retries_idempotent_read_with_same_correlation_id) {
  imlp::MemoryServer server;
  imlp::LoopbackTransport transport(server);
  transport.push_fault(imlp::TransportFault::timeout);
  imlp::Client client(transport, {.maximum_read_attempts = 2});
  const imlp::OperationResult result = client.read(0x0040U, 1U, 100ms);
  IMLP_EXPECT(result);
  IMLP_EXPECT_EQ(result.attempts, 2U);
  IMLP_EXPECT_EQ(client.metrics().timeouts, 1U);
  IMLP_EXPECT_EQ(client.metrics().retries, 1U);
  IMLP_EXPECT_EQ(transport.trace().size(), 4U);
  const imlp::DecodeResult first = imlp::decode(transport.trace()[0].bytes);
  const imlp::DecodeResult second = imlp::decode(transport.trace()[2].bytes);
  IMLP_EXPECT(first);
  IMLP_EXPECT(second);
  IMLP_EXPECT_EQ(first.frame->request_id, second.frame->request_id);
}

IMLP_TEST(client_never_retries_an_ambiguous_write_timeout) {
  imlp::MemoryServer server({.writes_enabled = true});
  imlp::LoopbackTransport transport(server);
  transport.push_fault(imlp::TransportFault::timeout);
  imlp::Client client(transport, {.maximum_read_attempts = 5});
  const std::array<std::byte, 1> data{std::byte{0x7A}};
  const imlp::OperationResult result = client.write(0x0100U, data, 100ms);
  IMLP_EXPECT(!result);
  IMLP_EXPECT_EQ(result.error, imlp::ClientError::timeout);
  IMLP_EXPECT_EQ(result.attempts, 1U);
  IMLP_EXPECT_EQ(client.metrics().transport_attempts, 1U);
  IMLP_EXPECT_EQ(client.metrics().retries, 0U);
}

IMLP_TEST(client_rejects_wrong_correlation_and_corrupt_responses) {
  imlp::MemoryServer server;
  imlp::LoopbackTransport transport(server);
  imlp::Client client(transport);

  transport.push_fault(imlp::TransportFault::wrong_request_id);
  const imlp::OperationResult wrong_id = client.read(0U, 4U, 100ms);
  IMLP_EXPECT_EQ(wrong_id.error, imlp::ClientError::correlation_mismatch);

  transport.push_fault(imlp::TransportFault::corrupt_response);
  const imlp::OperationResult corrupt = client.read(0U, 4U, 100ms);
  IMLP_EXPECT_EQ(corrupt.error, imlp::ClientError::malformed_response);
  IMLP_EXPECT_EQ(client.metrics().protocol_errors, 2U);
}

IMLP_TEST(client_preserves_remote_write_policy_status) {
  imlp::MemoryServer server;
  imlp::LoopbackTransport transport(server);
  imlp::Client client(transport);
  const std::array<std::byte, 1> data{std::byte{0x01}};
  const imlp::OperationResult result = client.write(0x0100U, data, 100ms);
  IMLP_EXPECT_EQ(result.error, imlp::ClientError::remote_error);
  IMLP_EXPECT_EQ(result.remote_status, imlp::Status::write_disabled);
}

IMLP_TEST(client_validates_arguments_before_transport_use) {
  imlp::MemoryServer server;
  imlp::LoopbackTransport transport(server);
  imlp::Client client(transport);
  IMLP_EXPECT_EQ(client.read(0U, 0U, 100ms).error, imlp::ClientError::invalid_argument);
  IMLP_EXPECT_EQ(client.read(0U, imlp::maximum_payload_size + 1U, 100ms).error,
                 imlp::ClientError::invalid_argument);
  const std::array<std::byte, 1> data{std::byte{0x01}};
  IMLP_EXPECT_EQ(client.write(0x0100U, data, 0ms).error, imlp::ClientError::invalid_argument);
  IMLP_EXPECT(transport.trace().empty());
}

}  // namespace
