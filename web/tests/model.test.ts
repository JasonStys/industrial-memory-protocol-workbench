/** @file model.test.ts
 * @brief Independent UI interchange/byte/number boundary oracles by Jason Stys.
 * Runtime C++ semantics are verified separately through actual compiled processes.
 */
import assert from "node:assert/strict";
import test from "node:test";
import {
  bytes,
  example,
  fileBytes,
  hex,
  jsonFile,
  numeric,
  object,
  parse,
  request,
} from "../src/model.js";

test("exact binary interchange preserves every byte including EOF and CR/LF", () => {
  const raw = Uint8Array.from({ length: 256 }, (_, index) => index);
  const encoded = hex(raw, 256);
  assert.equal(encoded.length, 512);
  assert.equal(encoded.slice(26 * 2, 27 * 2), "1a");
  assert.deepEqual(bytes(encoded, 256), raw);
  assert.deepEqual(bytes("", 0), new Uint8Array());
  for (const value of ["f", " 00", "0g", 7, "00".repeat(257)])
    assert.throws(() => bytes(value, 256));
  assert.throws(() => hex(raw, 255));
});

test("whole numeric fields refuse booleans, signs, floats and excessive addresses", () => {
  assert.equal(numeric("0x100"), 256);
  assert.equal(numeric("4294967295"), 0xffffffff);
  assert.equal(numeric(" 25 ", 1000), 25);
  for (const value of [
    "-1",
    "+1",
    "1.2",
    "1e3",
    "Infinity",
    "",
    "4294967296",
    "0xz",
  ])
    assert.throws(() => numeric(value));
  assert.throws(() => numeric("4", 3));
});

test("prepared inputs remain editable and represent no claimed result", () => {
  for (const name of [
    "healthy",
    "lost-ack",
    "truncated",
    "compose",
    "empty-stream",
  ]) {
    const value = request(example(name));
    assert.equal("report" in value, false);
    assert.equal("source_commit" in value, false);
  }
  const lost = example("lost-ack");
  assert.deepEqual(object((lost.operations as unknown[])[0]).faults, [
    "corrupt_response",
  ]);
  assert.deepEqual(object((lost.operations as unknown[])[1]).faults, []);
  assert.equal(
    object((example("healthy").operations as unknown[])[0]).address,
    256,
  );
});

test("browser input and stream framing refuse unknown, oversize and malformed selections", () => {
  assert.throws(() => object(null));
  assert.throws(() => object([]));
  assert.throws(() => parse("not json"));
  assert.throws(() => parse('"é"', 3));
  assert.throws(() => request({ kind: "host-endpoint" }));
  assert.throws(() => request({ ...example("healthy"), operations: [] }));
  assert.throws(() =>
    request({
      ...example("healthy"),
      operations: [{ verb: "exec", faults: [] }],
    }),
  );
  assert.throws(() =>
    request({
      ...example("healthy"),
      operations: [{ verb: "read", faults: ["unknown"] }],
    }),
  );
  assert.throws(() => request({ kind: "stream", chunks_hex: [] }));
  assert.throws(() =>
    request({
      kind: "stream",
      chunks_hex: ["00".repeat(4096)].flatMap((item) =>
        Array.from({ length: 17 }, () => item),
      ),
    }),
  );
  assert.deepEqual(request({ kind: "stream", chunks_hex: [""] }).chunks_hex, [
    "",
  ]);
});

test("actual File reads enforce bytes and strict UTF-8, not extension labels", async () => {
  const file = new File([Uint8Array.of(0x1a, 13, 10, 0, 255)], "inert.bin");
  assert.deepEqual(
    await fileBytes(file, 5),
    Uint8Array.of(0x1a, 13, 10, 0, 255),
  );
  await assert.rejects(fileBytes(file, 4));
  await assert.rejects(
    jsonFile(new File([Uint8Array.of(255)], "fake.json"), 10),
  );
  assert.deepEqual(
    await jsonFile(
      new File(['{"kind":"inspect","frame_hex":""}'], "custom.bin"),
      100,
    ),
    { kind: "inspect", frame_hex: "" },
  );
});
