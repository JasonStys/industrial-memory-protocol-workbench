/** @file model.ts
 * @brief Bounded editable protocol input and exact interchange by Jason Stys.
 * C++ independently validates protocol semantics. Symbols: docs/generated/symbol-index.md.
 */
export type JsonObject = Record<string, unknown>;
export type Kind = "session" | "stream" | "inspect" | "compose";
export interface Evidence extends JsonObject {
  id: string;
  title: string;
  input: JsonObject;
  report: JsonObject;
}
export const faults = [
  "timeout",
  "disconnect",
  "truncate_response",
  "corrupt_response",
  "wrong_request_id",
] as const;

export function object(value: unknown): JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value))
    throw new Error("Expected one JSON object");
  return value as JsonObject;
}

export function parse(raw: string, limit = 256 * 1024): unknown {
  if (new TextEncoder().encode(raw).byteLength > limit)
    throw new Error("Selected JSON exceeds its byte limit");
  return JSON.parse(raw) as unknown;
}

export function numeric(raw: string, maximum = 0xffffffff): number {
  if (!/^(?:0x[\da-f]+|\d+)$/iu.test(raw.trim()))
    throw new Error("Use a decimal or 0x-prefixed whole number");
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 0 || value > maximum)
    throw new Error(`Number must be from 0 to ${maximum}`);
  return value;
}

export function hex(value: Uint8Array, limit: number): string {
  if (value.byteLength > limit) throw new Error(`Input exceeds ${limit} bytes`);
  return Array.from(value, (item) => item.toString(16).padStart(2, "0")).join(
    "",
  );
}

export function bytes(value: unknown, limit: number): Uint8Array {
  if (
    typeof value !== "string" ||
    !/^(?:[\da-f]{2})*$/iu.test(value) ||
    value.length > limit * 2
  )
    throw new Error(`Use contiguous hexadecimal, up to ${limit} bytes`);
  return Uint8Array.from(value.match(/../gu) ?? [], (item) =>
    Number.parseInt(item, 16),
  );
}

export function request(raw: unknown): JsonObject {
  const value = object(raw);
  if (!["session", "stream", "inspect", "compose"].includes(String(value.kind)))
    throw new Error("Choose a supported protocol workflow");
  if (new TextEncoder().encode(JSON.stringify(value)).byteLength > 256 * 1024)
    throw new Error("Input exceeds 256 KiB");
  if (value.kind === "session") {
    if (
      !Array.isArray(value.operations) ||
      value.operations.length < 1 ||
      value.operations.length > 64
    )
      throw new Error("Use 1–64 ordered operations");
    for (const entry of value.operations) {
      const operation = object(entry);
      if (!["read", "write"].includes(String(operation.verb)))
        throw new Error("Each operation must read or write");
      if (
        !Array.isArray(operation.faults) ||
        operation.faults.length > 3 ||
        operation.faults.some(
          (item) => !faults.includes(item as (typeof faults)[number]),
        )
      )
        throw new Error("Choose at most three supported faults per operation");
    }
  } else if (value.kind === "stream") {
    if (
      !Array.isArray(value.chunks_hex) ||
      value.chunks_hex.length < 1 ||
      value.chunks_hex.length > 256
    )
      throw new Error("Use 1–256 bounded chunks");
    if (
      value.chunks_hex.reduce(
        (total: number, item: unknown) => total + bytes(item, 4096).length,
        0,
      ) > 65536
    )
      throw new Error("Stream exceeds 64 KiB");
  } else
    bytes(
      value[value.kind === "inspect" ? "frame_hex" : "payload_hex"],
      value.kind === "inspect" ? 278 : 256,
    );
  return value;
}

/** Prepared cases are editable inputs, never precomputed evidence. */
export function example(name: string): JsonObject {
  if (name === "empty-stream") return { kind: "stream", chunks_hex: [""] };
  if (name === "truncated") return { kind: "inspect", frame_hex: "494d01" };
  if (name === "compose")
    return {
      kind: "compose",
      version: 1,
      opcode: 2,
      flags: 0,
      request_id: 7,
      address: 256,
      status: 0,
      payload_hex: "1a0d0a007fff",
    };
  const corrupt = name === "lost-ack";
  return {
    kind: "session",
    writes_enabled: true,
    write_allow_begin: 256,
    write_allow_end: 2047,
    read_attempts: 2,
    operations: [
      {
        verb: "write",
        address: 256,
        payload_hex: "1a0d0a007fff",
        deadline_ms: 25,
        faults: corrupt ? ["corrupt_response"] : [],
      },
      { verb: "read", address: 256, length: 6, deadline_ms: 25, faults: [] },
    ],
  };
}

export async function fileBytes(
  file: File,
  limit: number,
): Promise<Uint8Array> {
  if (file.size > limit)
    throw new Error(`Selected file exceeds ${limit} bytes`);
  const data = new Uint8Array(await file.arrayBuffer());
  if (data.byteLength !== file.size || data.byteLength > limit)
    throw new Error("Selected file changed while reading");
  return data;
}

export async function jsonFile(file: File, limit: number): Promise<unknown> {
  return parse(
    new TextDecoder("utf-8", { fatal: true }).decode(
      await fileBytes(file, limit),
    ),
    limit,
  );
}
