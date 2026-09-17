# Fault catalog

`LoopbackTransport` consumes at most one queued fault per exchange. Scenarios are deterministic and
leave a direction/outcome trace.

| Fault | Injection behavior | Required client behavior | Evidence |
| --- | --- | --- | --- |
| Timeout | No response bytes; transport returns timeout | Retry read within attempt bound; do not retry write | client tests and demo |
| Disconnect | Connection closes before response | Reconnect and retry read; report write ambiguity | client tests/transport contract |
| Truncated response | Remove final byte | Decoder reports truncation | codec and fault tests |
| Corrupt response | Flip one CRC bit | Decoder reports checksum mismatch | client test and demo |
| Wrong request ID | Re-encode response with a different ID | Client reports correlation mismatch | client test |
| Oversized length | Header advertises more than 256 bytes | Reject before payload indexing | codec test and fuzzer |
| Trailing bytes | Valid frame plus additional byte | Reject exact-length mismatch | codec test |
| Denied write | Address outside server/memory policy | Return correlated `access_denied` | server test |
| Disabled write | Server left at default policy | Return correlated `write_disabled` | server/client tests and demo |

## Retry rationale

A timeout is not proof that a server failed to apply a request. Repeating a read is safe because it
does not create a side effect. Repeating a write can duplicate an effect, so the library returns the
ambiguous failure after one attempt. A higher-level design could add durable idempotency records, but
that behavior is deliberately not implied here.

## Trace interpretation

An exchange normally yields a request record followed by a response record. A timeout or disconnect
still creates a response-direction record with empty bytes and an outcome. A retried read therefore
shows two request records with identical frame bytes and request ID.

## Adding a fault

1. Add a distinct `TransportFault` value.
2. Define where it acts relative to server processing.
3. Record a stable outcome name.
4. Add a unit or integration test for the client response.
5. State whether an operation is safe to retry.
6. Update this catalog and the validation report.

