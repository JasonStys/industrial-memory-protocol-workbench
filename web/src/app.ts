/** @file app.ts
 * @brief Editable original-engine sessions, byte review and durable evidence UI by Jason Stys.
 * State: selected record, edit/search revisions and finite busy operation.
 * Symbol locations: docs/generated/symbol-index.md.
 */
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
  type Evidence,
  type JsonObject,
} from "./model.js";

function element<T extends HTMLElement>(id: string, kind: { new (): T }): T {
  const value = document.getElementById(id);
  if (!(value instanceof kind))
    throw new Error(`Missing interface control ${id}`);
  return value;
}
const input = (id: string): HTMLInputElement => element(id, HTMLInputElement);
const area = (id: string): HTMLTextAreaElement =>
  element(id, HTMLTextAreaElement);
const select = (id: string): HTMLSelectElement =>
  element(id, HTMLSelectElement);
const button = (id: string): HTMLButtonElement =>
  element(id, HTMLButtonElement);
const text = (id: string, value: string): void => {
  element(id, HTMLElement).textContent = value;
};
const encoded = (value: unknown): string => JSON.stringify(value, null, 2);
const workflow = select("workflow");
let revision = 0;
let searchRevision = 0;
let busy = false;
let selected: Evidence | null = null;
let page = 0;
let total = 0;
const received = new URLSearchParams(location.hash.slice(1)).get("native");
if (received !== null) {
  sessionStorage.setItem("imlp-owner-capability", received);
  history.replaceState(null, "", location.pathname + location.search);
}
const capability = sessionStorage.getItem("imlp-owner-capability") ?? "";

function status(message: string, failed = false): void {
  text("status", message);
  element("status", HTMLElement).classList.toggle("error", failed);
}
function failure(error: unknown): void {
  status(
    error instanceof Error ? error.message : "The operation could not complete",
    true,
  );
}

async function api(path: string, body?: JsonObject): Promise<JsonObject> {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined
        ? { "X-IMLP-Capability": capability }
        : {
            "X-IMLP-Capability": capability,
            "Content-Type": "application/json",
          },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    credentials: "omit",
    cache: "no-store",
    redirect: "error",
  });
  const result = object(await response.json());
  if (!response.ok)
    throw new Error(
      typeof result.error === "string"
        ? result.error
        : "Operation refused; earlier evidence is unchanged",
    );
  return result;
}

function panels(): void {
  for (const kind of ["session", "stream", "inspect", "compose"])
    element(`${kind}-fields`, HTMLFieldSetElement).hidden =
      workflow.value !== kind;
}

function currentInput(): JsonObject {
  const kind = workflow.value;
  if (kind === "session")
    return request({
      kind,
      writes_enabled: select("writes").value === "true",
      write_allow_begin: numeric(input("allow-begin").value),
      write_allow_end: numeric(input("allow-end").value),
      read_attempts: numeric(input("attempts").value, 3),
      operations: parse(area("operations").value),
    });
  if (kind === "stream")
    return request({ kind, chunks_hex: parse(area("chunks").value) });
  if (kind === "inspect")
    return request({
      kind,
      frame_hex: area("frame").value.replace(/\s+/gu, ""),
    });
  return request({
    kind,
    version: numeric(input("frame-version").value, 255),
    opcode: numeric(input("opcode").value, 255),
    flags: numeric(input("flags").value, 255),
    request_id: numeric(input("request-id").value),
    address: numeric(input("address").value),
    status: numeric(input("remote-status").value, 65535),
    payload_hex: area("payload").value.replace(/\s+/gu, ""),
  });
}

function fill(raw: unknown): void {
  const value = request(raw);
  workflow.value = String(value.kind);
  if (value.kind === "session") {
    select("writes").value = String(value.writes_enabled);
    input("allow-begin").value = String(value.write_allow_begin);
    input("allow-end").value = String(value.write_allow_end);
    input("attempts").value = String(value.read_attempts);
    area("operations").value = encoded(value.operations);
  } else if (value.kind === "stream")
    area("chunks").value = encoded(value.chunks_hex);
  else if (value.kind === "inspect")
    area("frame").value = String(value.frame_hex);
  else {
    for (const [id, key] of [
      ["frame-version", "version"],
      ["opcode", "opcode"],
      ["flags", "flags"],
      ["request-id", "request_id"],
      ["address", "address"],
      ["remote-status", "status"],
    ] as const)
      input(id).value = String(value[key]);
    area("payload").value = String(value.payload_hex);
  }
  revision += 1;
  panels();
}

function download(name: string, value: BlobPart, type: string): void {
  const url = URL.createObjectURL(new Blob([value], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}
function saveJson(name: string, value: unknown): void {
  download(name, encoded(value) + "\n", "application/json");
}

function table(headers: string[], rows: unknown[][], caption: string): void {
  const head = element("table-head", HTMLTableSectionElement);
  const body = element("table-body", HTMLTableSectionElement);
  head.replaceChildren();
  body.replaceChildren();
  text("table-caption", caption);
  const row = document.createElement("tr");
  for (const value of headers) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = value;
    row.append(cell);
  }
  head.append(row);
  for (const values of rows) {
    const entry = document.createElement("tr");
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = typeof value === "string" ? value : encoded(value);
      entry.append(cell);
    }
    body.append(entry);
  }
}

function show(value: JsonObject): void {
  if (typeof value.id !== "string" || typeof value.title !== "string")
    throw new Error("Invalid saved record identity");
  const report = object(value.report);
  const frameIndex = input("frame-index").parentElement;
  if (frameIndex !== null) frameIndex.hidden = report.kind !== "stream";
  selected = value as Evidence;
  fill(value.input);
  text("selected", `${value.title} | ${String(report.status)} | ${value.id}`);
  text("evidence", encoded(value));
  if (report.kind === "session") {
    const rows = (report.operations as unknown[]).map(object);
    table(
      [
        "Operation",
        "Request ID",
        "Attempts",
        "Client result",
        "Remote status",
        "Read bytes",
        "Memory before",
        "Memory after",
        "Detail",
      ],
      rows.map((row) => [
        row.verb,
        row.request_id,
        row.attempts,
        row.client_error,
        row.remote_status,
        row.data_hex,
        object(row.before).hex,
        object(row.after).hex,
        row.detail,
      ]),
      "Actual ordered operations on one simulated memory server",
    );
    text(
      "summary",
      `Outcome: ${String(report.status)}. ${rows.length} operations. Counters: ${encoded(report.metrics)}. A failed acknowledgement may follow a completed write; compare the actual before/after bytes.`,
    );
    text(
      "trace",
      encoded({
        initial_readable_hex: report.initial_readable_hex,
        final_readable_hex: report.final_readable_hex,
        trace: report.trace,
      }),
    );
  } else if (report.kind === "stream") {
    const frames = (report.frames as unknown[]).map(object);
    const issues = (report.issues as unknown[]).map(object);
    table(
      ["Type", "Offset", "Bytes", "Disposition", "Exact accepted frame"],
      [
        ...frames.map((row, index) => [
          "Frame " + index,
          row.offset,
          row.wire_bytes,
          "Accepted",
          row.hex,
        ]),
        ...issues.map((row) => [
          "Discard",
          row.offset,
          row.bytes,
          row.error,
          "Not an accepted frame",
        ]),
      ].sort((a, b) => Number(a[1]) - Number(b[1])),
      "Zero-based extents in the exact concatenated input",
    );
    text(
      "summary",
      `${String(report.input_bytes)} input bytes; ${frames.length} accepted frames; ${issues.length} listed issues; ${String(report.omitted_issue_records)} omitted issue records / ${String(report.omitted_issue_bytes)} omitted bytes; ${String(report.pending_bytes)} pending after EOF.`,
    );
    text(
      "trace",
      encoded({
        frames: report.frames,
        issues: report.issues,
        omitted_issue_records: report.omitted_issue_records,
        omitted_issue_bytes: report.omitted_issue_bytes,
      }),
    );
  } else {
    const accepted = report.accepted === true;
    table(
      ["Measure", "Observed"],
      Object.entries(
        report.frame === null
          ? { accepted, error: report.error, exact_hex: report.hex }
          : {
              accepted,
              error: report.error,
              ...object(report.frame),
              exact_hex: report.hex,
            },
      ).map(([key, entry]) => [key, entry]),
      "Original codec decision and exact bytes",
    );
    text(
      "summary",
      `${accepted ? "Accepted exact frame" : "Blocked frame"}: ${String(report.error)}. CRC is not authentication.`,
    );
    text("trace", String(report.hex));
  }
  button("export-evidence").disabled = false;
  button("export-frame").disabled = !(
    report.accepted === true ||
    (Array.isArray(report.frames) && report.frames.length > 0)
  );
  button("delete").disabled = busy;
}

function setBusy(value: boolean): void {
  busy = value;
  for (const control of document.querySelectorAll<
    | HTMLInputElement
    | HTMLSelectElement
    | HTMLTextAreaElement
    | HTMLButtonElement
  >("[data-edit]"))
    control.disabled = value;
  button("delete").disabled = value || selected === null;
}

async function refresh(): Promise<void> {
  const captured = ++searchRevision;
  const result = await api(
    "/api/history?" +
      new URLSearchParams({
        q: input("search").value,
        kind: select("history-kind").value,
        page: String(page),
      }).toString(),
  );
  if (captured !== searchRevision) return;
  total = Number(result.total);
  text(
    "history-total",
    `${total} matching saved experiments | page ${page + 1}`,
  );
  const list = element("history", HTMLUListElement);
  list.replaceChildren();
  for (const raw of result.items as unknown[]) {
    const row = object(raw);
    const item = document.createElement("li");
    const open = document.createElement("button");
    open.textContent = `${String(row.title)} | ${String(row.kind)} | ${String(row.status)} | ${String(row.created)}`;
    open.addEventListener("click", () => {
      const expected = ++revision;
      void api("/api/history/" + encodeURIComponent(String(row.id)))
        .then((record) => {
          if (expected === revision) {
            show(record);
            status(
              "Selected the exact saved experiment and its original input.",
            );
          }
        })
        .catch(failure);
    });
    item.append(open);
    list.append(item);
  }
  button("previous").disabled = page === 0;
  button("next").disabled = (page + 1) * 25 >= total;
}

async function run(value: JsonObject = currentInput()): Promise<void> {
  if (busy) return;
  const captured = revision;
  setBusy(true);
  status("Running the actual fixed C++ engines on inert simulator bytes…");
  try {
    const result = await api("/api/run", {
      title: input("title").value,
      input: value,
    });
    if (captured === revision) {
      show(result);
      status(
        "Saved actual simulator evidence. Review blocked and uncertain outcomes; no device was contacted.",
      );
    } else
      status(
        "Experiment saved; edited context changed. Select the saved record explicitly.",
      );
    await refresh();
  } finally {
    setBusy(false);
  }
}

for (const control of document.querySelectorAll("[data-edit]"))
  control.addEventListener("input", () => {
    revision += 1;
  });
workflow.addEventListener("change", panels);
button("run").addEventListener("click", () => {
  try {
    void run().catch(failure);
  } catch (error) {
    failure(error);
  }
});
button("load-example").addEventListener("click", () => {
  fill(example(select("example").value));
  status("Loaded an editable input; no result has been invented.");
});
button("append-operation").addEventListener("click", () => {
  try {
    const operations = parse(area("operations").value);
    if (!Array.isArray(operations) || operations.length >= 64)
      throw new Error("Use at most 64 ordered operations");
    const verb = select("op-verb").value;
    const fault = select("op-fault").value;
    const operation = {
      verb,
      address: numeric(input("op-address").value),
      deadline_ms: numeric(input("op-deadline").value, 1000),
      faults: fault ? [fault] : [],
      ...(verb === "read"
        ? { length: numeric(input("op-length").value, 256) }
        : { payload_hex: hex(bytes(input("op-payload").value, 256), 256) }),
    };
    area("operations").value = encoded([...operations, operation]);
    revision += 1;
  } catch (error) {
    failure(error);
  }
});
button("export-input").addEventListener("click", () => {
  try {
    saveJson("imlp-input.json", currentInput());
  } catch (error) {
    failure(error);
  }
});
button("export-evidence").addEventListener("click", () => {
  if (selected) saveJson(`imlp-evidence-${selected.id}.json`, selected);
});
button("export-frame").addEventListener("click", () => {
  try {
    if (!selected) return;
    const report = selected.report;
    const raw =
      report.kind === "stream"
        ? object(
            (report.frames as unknown[])[
              numeric(input("frame-index").value, 2978)
            ],
          ).hex
        : report.hex;
    download(
      "imlp-accepted-frame.bin",
      new Uint8Array(bytes(raw, 278)).buffer,
      "application/octet-stream",
    );
  } catch (error) {
    failure(error);
  }
});
button("delete").addEventListener("click", () => {
  if (
    !selected ||
    busy ||
    !confirm(
      "Delete only this selected record? Export complete evidence first if needed.",
    )
  )
    return;
  const id = selected.id;
  void api("/api/delete", { id })
    .then(async () => {
      if (selected?.id === id) {
        selected = null;
        text(
          "selected",
          "Selected history entry deleted; existing exports were not changed.",
        );
        for (const key of ["delete", "export-evidence", "export-frame"])
          button(key).disabled = true;
      }
      await refresh();
      status("Deleted only the selected saved experiment.");
    })
    .catch(failure);
});

for (const id of ["input-file", "evidence-file", "stream-file", "frame-file"])
  input(id).addEventListener("change", () => {
    const file = input(id).files?.[0];
    if (!file) return;
    const captured = ++revision;
    void (async () => {
      if (id === "stream-file" || id === "frame-file") {
        const raw = await fileBytes(file, id === "stream-file" ? 65536 : 278);
        if (captured !== revision) return;
        if (id === "frame-file")
          fill({ kind: "inspect", frame_hex: hex(raw, 278) });
        else {
          const chunks = [];
          for (let index = 0; index < raw.length; index += 4096)
            chunks.push(hex(raw.slice(index, index + 4096), 4096));
          fill({ kind: "stream", chunks_hex: chunks.length ? chunks : [""] });
        }
      } else {
        const value = object(
          await jsonFile(
            file,
            id === "evidence-file" ? 8 * 1024 * 1024 : 256 * 1024,
          ),
        );
        if (captured !== revision) return;
        if (id === "evidence-file") {
          if (
            value.product !== "industrial-memory-protocol-workbench" ||
            value.schemaVersion !== 1
          )
            throw new Error("Choose this application's exported evidence");
          const prepared = request(value.input);
          fill(prepared);
          await run(prepared);
        } else fill(value);
      }
      status(
        id === "evidence-file"
          ? "Imported input reran with actual C++; supplied result claims were ignored."
          : "Loaded exact local input. Review parameters before running.",
      );
    })()
      .catch(failure)
      .finally(() => {
        input(id).value = "";
      });
  });
button("refresh").addEventListener("click", () => {
  page = 0;
  void refresh().catch(failure);
});
for (const id of ["search", "history-kind"])
  element(id, HTMLElement).addEventListener("input", () => {
    searchRevision += 1;
  });
button("previous").addEventListener("click", () => {
  page = Math.max(0, page - 1);
  void refresh().catch(failure);
});
button("next").addEventListener("click", () => {
  if ((page + 1) * 25 < total) {
    page += 1;
    void refresh().catch(failure);
  }
});
button("quit").addEventListener("click", () => {
  void api("/api/quit", { quit: true })
    .then(() => {
      setBusy(true);
      button("quit").disabled = true;
      status(
        "Closing after the actual owned work drains. Workspace history remains saved.",
      );
    })
    .catch(failure);
});
fill(example("healthy"));
if (capability)
  void api("/health")
    .then((value) => {
      text(
        "identity",
        `Version ${String(value.version)} | C++20 source ${String(object(value.engine).sourceCommit)}`,
      );
      status(
        "Owned app ready. Configure or import your supported synthetic input.",
      );
      return refresh();
    })
    .catch(failure);
else {
  setBusy(true);
  button("quit").disabled = true;
  status(
    "Open this application from its native owner window for an authorized private session.",
    true,
  );
}
