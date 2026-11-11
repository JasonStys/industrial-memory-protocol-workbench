/** @file native_feature_smoke.mjs
 * @brief Actual editable compiled-app Chromium journeys with independent wire oracles by Jason Stys.
 * No mocked server or source fallback. Symbols: docs/generated/symbol-index.md.
 */
import assert from "node:assert/strict";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";

const [url, outputArgument, source] = process.argv.slice(2);
assert.ok(url && outputArgument && source);
const output = resolve(outputArgument);
await mkdir(output, { recursive: true });
const authority = new URL(url).origin;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const pageErrors = [],
  externalRequests = [],
  records = [];
page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("request", (request) => {
  if (
    new URL(request.url()).origin !== authority &&
    !request.url().startsWith("blob:")
  )
    externalRequests.push(request.url());
});

function crc32(raw) {
  let value = 0xffffffff;
  for (const byte of raw) {
    value ^= byte;
    for (let bit = 0; bit < 8; bit += 1)
      value = (value >>> 1) ^ (value & 1 ? 0xedb88320 : 0);
  }
  return (value ^ 0xffffffff) >>> 0;
}
function wire() {
  const header = Buffer.alloc(18);
  header.write("IM");
  header[2] = 1;
  header[3] = 2;
  header.writeUInt32BE(7, 6);
  header.writeUInt32BE(256, 10);
  header.writeUInt16BE(6, 14);
  const prefix = Buffer.concat([header, Buffer.from("1a0d0a007fff", "hex")]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(prefix));
  return Buffer.concat([prefix, crc]);
}
async function run(title) {
  await page.locator("#title").fill(title);
  const pending = page.waitForResponse(
    (response) =>
      response.url() === authority + "/api/run" &&
      response.request().method() === "POST",
  );
  await page.locator("#run").click();
  const response = await pending;
  assert.equal(response.status(), 201);
  const record = await response.json();
  await page.locator("#selected").filter({ hasText: record.id }).waitFor();
  await page.locator("#run:enabled").waitFor();
  records.push(record);
  return record;
}
async function download(control, filename) {
  const pending = page.waitForEvent("download");
  await page.locator(control).click();
  const file = await pending;
  await file.saveAs(resolve(output, filename));
  return readFile(resolve(output, filename));
}
try {
  await page.goto(url, { waitUntil: "networkidle" });
  await page
    .locator("#status")
    .filter({ hasText: "Owned app ready" })
    .waitFor();
  assert.ok((await page.locator("#identity").innerText()).includes(source));
  assert.ok((await page.locator("#identity").innerText()).includes("1.1.0"));
  const healthy = await run("Exact binary write then read");
  assert.equal(healthy.report.operations[1].data_hex, "1a0d0a007fff");
  assert.equal(healthy.report.status, "completed");
  await page.locator("#example").selectOption("lost-ack");
  await page.locator("#load-example").click();
  const lost = await run("Lost ACK requires human review");
  assert.equal(lost.report.operations[0].client_error, "malformed_response");
  assert.equal(lost.report.operations[0].attempts, 1);
  assert.equal(
    lost.report.operations[0].after.hex,
    lost.report.operations[1].data_hex,
  );
  assert.equal(lost.report.status, "review");
  await page.locator("#result-heading").scrollIntoViewIfNeeded();
  await page
    .locator("section")
    .filter({ has: page.locator("#result-heading") })
    .screenshot({ path: resolve(output, "01-write-ack-review.png") });
  const exported = JSON.parse(
    (await download("#export-evidence", "lost-ack-evidence.json")).toString(
      "utf8",
    ),
  );
  assert.deepEqual(exported, lost);
  const input = JSON.parse(
    (await download("#export-input", "custom-input.json")).toString("utf8"),
  );
  assert.deepEqual(input, lost.input);

  await page.locator("#writes").selectOption("false");
  const denied = await run("Explicit writes-disabled boundary");
  assert.equal(
    denied.report.initial_readable_hex,
    denied.report.final_readable_hex,
  );
  assert.notEqual(denied.report.operations[0].client_error, "none");

  await page.locator("#example").selectOption("compose");
  await page.locator("#load-example").click();
  const composed = await run("Custom composed raw frame");
  assert.equal(composed.report.hex, wire().toString("hex"));
  assert.deepEqual(await download("#export-frame", "composed.bin"), wire());

  await page.locator("#workflow").selectOption("inspect");
  await page.locator("#frame-file").setInputFiles({
    name: "custom-frame.bin",
    mimeType: "application/octet-stream",
    buffer: wire(),
  });
  await page.locator("#frame").filter({ visible: true }).waitFor();
  await page.waitForFunction(
    (expected) => document.querySelector("#frame").value === expected,
    wire().toString("hex"),
  );
  const inspected = await run("Imported exact binary frame");
  assert.equal(inspected.report.accepted, true);
  assert.deepEqual(inspected.report.frame, composed.report.frame);

  await page.locator("#workflow").selectOption("stream");
  const raw = Buffer.concat([Buffer.from("noise"), wire(), Buffer.from("IM")]);
  await page.locator("#stream-file").setInputFiles({
    name: "fragmented.bin",
    mimeType: "application/octet-stream",
    buffer: raw,
  });
  await page.waitForFunction(
    (expected) =>
      JSON.parse(document.querySelector("#chunks").value)[0] === expected,
    raw.toString("hex"),
  );
  await page
    .locator("#chunks")
    .fill(
      JSON.stringify([
        raw.subarray(0, 7).toString("hex"),
        raw.subarray(7, 14).toString("hex"),
        raw.subarray(14).toString("hex"),
      ]),
    );
  const stream = await run("Fragmented custom stream with noise and EOF");
  assert.equal(stream.report.input_bytes, raw.length);
  assert.equal(stream.report.frames[0].offset, 5);
  assert.equal(stream.report.frames[0].hex, wire().toString("hex"));
  assert.equal(
    stream.report.issues.reduce((total, row) => total + row.bytes, 0),
    7,
  );
  assert.equal(stream.report.omitted_issue_bytes, 0);
  assert.equal(stream.report.pending_bytes, 0);
  assert.deepEqual(await download("#export-frame", "stream-frame.bin"), wire());
  await page.locator("#result-heading").scrollIntoViewIfNeeded();
  await page
    .locator("section")
    .filter({ has: page.locator("#result-heading") })
    .screenshot({
      path: resolve(output, "02-stream-offset-review.png"),
    });

  const forged = structuredClone(lost);
  forged.report.status = "completed";
  forged.report.operations[0].client_error = "none";
  const importResponse = page.waitForResponse(
    (response) =>
      response.url() === authority + "/api/run" &&
      response.request().method() === "POST",
  );
  await page.locator("#evidence-file").setInputFiles({
    name: "forged-evidence.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(forged)),
  });
  const rerunResponse = await importResponse;
  assert.equal(rerunResponse.status(), 201);
  const rerun = await rerunResponse.json();
  assert.equal(rerun.report.operations[0].client_error, "malformed_response");
  assert.equal(rerun.report.status, "review");
  assert.notEqual(rerun.id, lost.id);
  records.push(rerun);
  await page.locator("#run:enabled").waitFor();

  await page.locator("#workflow").selectOption("compose");
  await page.locator("#frame-version").fill("2");
  const blocked = await run("Unsupported version stays blocked");
  assert.equal(blocked.report.accepted, false);
  assert.equal(blocked.report.status, "blocked");
  assert.equal(blocked.report.hex, "");
  assert.equal(await page.locator("#export-frame").isDisabled(), true);

  await page.locator("#workflow").selectOption("inspect");
  await page.locator("#frame").fill("494d01");
  const disposable = await run("Disposable blocked frame review");
  assert.equal(disposable.report.error, "truncated");
  const deletion = page.waitForResponse(
    (response) => response.url() === authority + "/api/delete",
  );
  page.once("dialog", (dialog) => dialog.accept());
  await page.locator("#delete").click();
  assert.equal((await deletion).status(), 200);
  await page
    .locator("#history-total")
    .filter({ hasText: "8 matching" })
    .waitFor();
  records.pop();

  await page
    .locator("#frame-file")
    .setInputFiles({
      name: "too-large.bin",
      mimeType: "application/octet-stream",
      buffer: Buffer.alloc(279),
    });
  await page.locator("#status.error").filter({ hasText: "278" }).waitFor();
  assert.equal(await page.locator("#export-evidence").isDisabled(), true);

  await page.locator("#search").fill("Lost ACK");
  await page.locator("#refresh").click();
  await page
    .locator("#history-total")
    .filter({ hasText: "1 matching" })
    .waitFor();
  await page.locator("#history button").click();
  await page.locator("#selected").filter({ hasText: lost.id }).waitFor();
  await page
    .getByText("Complete input, engine identity and result JSON", {
      exact: true,
    })
    .click();
  assert.deepEqual(
    JSON.parse(await page.locator("#evidence").innerText()),
    lost,
  );
  await page
    .locator("#operations")
    .fill('[{"verb":"exec","host":"never accepted"}]');
  await page.locator("#run").click();
  await page.locator("#status.error").waitFor();
  assert.deepEqual(
    JSON.parse(await page.locator("#evidence").innerText()),
    lost,
  );
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    const table = page.getByRole("region", { name: "Protocol result table" });
    await table.focus();
    assert.equal(
      await table.evaluate((value) => value === document.activeElement),
      true,
    );
    assert.ok((await page.locator("#identity").innerText()).includes(source));
  }
  assert.deepEqual(pageErrors, []);
  assert.deepEqual(externalRequests, []);
  await writeFile(
    resolve(output, "browser-acceptance.json"),
    JSON.stringify(
      {
        passed: true,
        source,
        version: "1.1.0",
        actualRecords: records.length,
        workflows: records.map((record) => ({
          id: record.id,
          kind: record.input.kind,
          inputSha256: record.inputSha256,
          outcome: record.report.status,
        })),
        expectedRawFrameSha256: createHash("sha256")
          .update(wire())
          .digest("hex"),
        forgedEvidenceRerun: true,
        explicitSingleRecordDeletion: true,
        oversizedBinaryRefused: true,
        mobileWidths: [390, 320],
        browser: browser.version(),
        externalRequests,
        pageErrors,
      },
      null,
      2,
    ) + "\n",
  );
  await page.locator("#quit").click();
} finally {
  await browser.close();
}
