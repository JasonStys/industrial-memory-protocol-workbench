"""@file test_studio_service.py
@brief Real original C++ session/codec/stream workflows with independent struct/CRC oracles.
@details No production example is imported as its own expected answer. All workspaces are synthetic.
"""

import hashlib
import http.client
import json
import sqlite3
import struct
import subprocess
import threading
import zlib
from contextlib import closing

import pytest

from imlp_studio import resources, store
from imlp_studio.domain import canonical
from imlp_studio.server import Handler


def session(faults=None, writes=True):
    return {
        "kind": "session",
        "writes_enabled": writes,
        "write_allow_begin": 256,
        "write_allow_end": 2047,
        "read_attempts": 2,
        "operations": [
            {
                "verb": "write",
                "address": 256,
                "payload_hex": "1a0d0a007fff",
                "deadline_ms": 25,
                "faults": faults or [],
            },
            {"verb": "read", "address": 256, "length": 6, "deadline_ms": 25, "faults": []},
        ],
    }


def independent_frame(
    opcode=2, identity=7, address=256, payload=b"\x1a\r\n\x00\x7f\xff", flags=0, status=0
):
    data = (
        struct.pack(
            ">2sBBBBIIHH", b"IM", 1, opcode, flags, 0, identity, address, len(payload), status
        )
        + payload
    )
    return data + struct.pack(">I", zlib.crc32(data))


def submit(client, value, title="Synthetic byte evidence"):
    return client.post("/api/run", json={"title": title, "input": value})


def test_real_same_server_write_then_read_exact_bytes_and_saved_provenance(live):
    host, client = live
    value = session()
    response = submit(client, value)
    assert response.status_code == 201
    evidence = response.json()
    report = evidence["report"]
    assert report["status"] == "completed"
    assert [row["client_error"] for row in report["operations"]] == ["none", "none"]
    assert report["operations"][1]["data_hex"] == "1a0d0a007fff"
    assert report["operations"][0]["before"]["hex"] == "000000000000"
    assert report["operations"][0]["after"]["hex"] == "1a0d0a007fff"
    assert bytes.fromhex(report["final_readable_hex"])[256:262] == b"\x1a\r\n\x00\x7f\xff"
    assert report["trace"][0]["hex"] == independent_frame(identity=1).hex()
    assert (
        report["trace"][2]["hex"]
        == independent_frame(opcode=1, identity=2, payload=b"\x00\x06").hex()
    )
    assert evidence["engine"] == host.engine.identity
    assert (
        evidence["inputSha256"]
        == report["input_sha256"]
        == hashlib.sha256(canonical(value)).hexdigest()
    )
    assert client.get("/api/history/" + evidence["id"]).json() == evidence


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("corrupt_response", "malformed_response"),
        ("truncate_response", "malformed_response"),
        ("wrong_request_id", "correlation_mismatch"),
    ],
)
def test_lost_write_acknowledgement_is_reviewed_not_false_no_effect(live, fault, expected):
    _, client = live
    report = submit(client, session([fault])).json()["report"]
    assert report["status"] == "review"
    write, read = report["operations"]
    assert write["client_error"] == expected and write["attempts"] == 1
    assert write["after"]["hex"] == read["data_hex"] == "1a0d0a007fff"
    assert report["metrics"]["retries"] == 0


def test_actual_read_retry_same_id_and_unconsumed_fault_carries_to_next_operation(live):
    _, client = live
    value = session(["timeout", "corrupt_response"])
    report = submit(client, value).json()["report"]
    first, second = report["operations"]
    assert first["client_error"] == "timeout" and first["attempts"] == 1
    assert first["before"] == first["after"]
    assert second["client_error"] == "malformed_response" and second["attempts"] == 1
    value["operations"] = [
        {"verb": "read", "address": 256, "length": 6, "deadline_ms": 25, "faults": ["timeout"]}
    ]
    report = submit(client, value).json()["report"]
    assert (
        report["operations"][0]["attempts"] == 2
        and report["operations"][0]["client_error"] == "none"
    )
    assert report["trace"][0]["hex"] == report["trace"][2]["hex"]
    assert report["metrics"]["retries"] == report["metrics"]["timeouts"] == 1


@pytest.mark.parametrize(
    "change",
    ["disabled", "read-only", "outside-allowlist", "denied-map", "zero-length", "zero-deadline"],
)
def test_real_permission_and_argument_gates_leave_simulated_memory_unchanged(live, change):
    _, client = live
    value = session()
    if change == "disabled":
        value["writes_enabled"] = False
    elif change == "read-only":
        value["operations"][0]["address"] = 1
    elif change == "outside-allowlist":
        value["write_allow_begin"] = 512
    elif change == "denied-map":
        value["operations"][0]["address"] = 2048
    elif change == "zero-length":
        value["operations"][0]["payload_hex"] = ""
    else:
        value["operations"][0]["deadline_ms"] = 0
    report = submit(client, value).json()["report"]
    assert report["status"] == "review" and report["operations"][0]["client_error"] != "none"
    assert report["initial_readable_hex"] == report["final_readable_hex"]
    assert report["operations"][1]["data_hex"] == "000000000000"


def test_actual_frame_compose_inspect_stream_offsets_corruption_and_eof(live):
    _, client = live
    raw = independent_frame()
    compose = {
        "kind": "compose",
        "version": 1,
        "opcode": 2,
        "flags": 0,
        "request_id": 7,
        "address": 256,
        "status": 0,
        "payload_hex": "1a0d0a007fff",
    }
    result = submit(client, compose).json()["report"]
    assert result["accepted"] and result["hex"] == raw.hex()
    assert (
        submit(client, {"kind": "inspect", "frame_hex": raw.hex()}).json()["report"]["frame"]
        == result["frame"]
    )
    stream = b"noise" + raw + b"IM"
    report = submit(
        client,
        {"kind": "stream", "chunks_hex": [stream[:7].hex(), stream[7:14].hex(), stream[14:].hex()]},
    ).json()["report"]
    assert report["status"] == "review" and report["input_bytes"] == len(stream)
    assert report["frames"][0]["offset"] == 5 and report["frames"][0]["hex"] == raw.hex()
    assert sum(row["bytes"] for row in report["issues"]) == 7
    assert report["pending_bytes"] == report["omitted_issue_bytes"] == 0
    corrupt = raw[:-1] + bytes([raw[-1] ^ 1])
    blocked = submit(client, {"kind": "inspect", "frame_hex": corrupt.hex()}).json()["report"]
    assert blocked["status"] == "blocked" and blocked["error"] == "checksum_mismatch"
    assert not blocked["accepted"] and blocked["frame"] is None
    empty = submit(client, {"kind": "stream", "chunks_hex": [""]}).json()["report"]
    assert empty["status"] == "review" and empty["input_bytes"] == 0 and empty["frames"] == []


@pytest.mark.parametrize(
    "change",
    [
        "path",
        "unknown-operation",
        "boolean-address",
        "negative",
        "odd-hex",
        "unknown-fault",
        "too-many-chunks",
        "oversized-stream",
    ],
)
def test_invalid_custom_inputs_do_not_save_or_change_existing_evidence(live, change):
    _, client = live
    original = submit(client, session()).json()
    value = session()
    if change == "path":
        value["host"] = "outside.invalid"
    elif change == "unknown-operation":
        value["operations"][0]["command"] = "never executed"
    elif change == "boolean-address":
        value["operations"][0]["address"] = True
    elif change == "negative":
        value["read_attempts"] = -1
    elif change == "odd-hex":
        value["operations"][0]["payload_hex"] = "f"
    elif change == "unknown-fault":
        value["operations"][0]["faults"] = ["socket-connect"]
    elif change == "too-many-chunks":
        value = {"kind": "stream", "chunks_hex": [""] * 257}
    else:
        value = {"kind": "stream", "chunks_hex": ["00" * 4096] * 17}
    assert submit(client, value).status_code == 400
    assert client.get("/api/history").json()["total"] == 1
    assert client.get("/api/history/" + original["id"]).json() == original


def test_literal_history_pagination_explicit_delete_and_persistence(live):
    host, client = live
    record = submit(client, session(), "Literal%_ specimen").json()
    with host.profile.store.connect() as database:
        raw = json.dumps(record)
        for index in range(27):
            database.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?)",
                (
                    f"{index:032x}",
                    f"2026-11-11T00:00:{index:02d}Z",
                    f"Other{index}",
                    "session",
                    "completed",
                    raw,
                ),
            )
    assert client.get("/api/history?q=%25_").json()["total"] == 1
    assert len(client.get("/api/history").json()["items"]) == 25
    assert len(client.get("/api/history?page=1").json()["items"]) == 3
    assert client.post("/api/delete", json={"id": record["id"]}).status_code == 200
    assert client.get("/api/history/" + record["id"]).status_code == 404
    with closing(sqlite3.connect(host.profile.directory / "workspace.sqlite3")) as database:
        assert database.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 27


@pytest.mark.parametrize(
    "failure", ["record-budget", "byte-budget", "engine-timeout", "engine-os", "invalid-title"]
)
def test_failure_cannot_silently_prune_or_create_success(live, monkeypatch, failure):
    host, client = live
    original = submit(client, session()).json()
    if failure == "record-budget":
        monkeypatch.setattr(store, "MAX_RECORDS", 1)
    elif failure == "byte-budget":
        monkeypatch.setattr(store, "MAX_HISTORY_BYTES", 1)
    elif failure in ("engine-timeout", "engine-os"):

        def fail(value):
            if failure == "engine-timeout":
                raise subprocess.TimeoutExpired("owned-fixed-engine", 15)
            raise OSError("inert synthetic I/O failure")

        monkeypatch.setattr(host.engine, "run", fail)
    response = submit(client, session(), "" if failure == "invalid-title" else "New evidence")
    assert response.status_code == (500 if failure.startswith("engine-") else 400)
    assert client.get("/api/history").json()["total"] == 1
    assert client.get("/api/history/" + original["id"]).json() == original


@pytest.mark.parametrize(
    "header,value",
    [
        ("Host", "external.invalid"),
        ("Origin", "https://external.invalid"),
        ("X-IMLP-Capability", "wrong"),
        ("X-IMLP-Capability", "caf\xe9"),
    ],
)
def test_actual_authority_origin_and_capability_refusals_precede_any_body(live, header, value):
    host, _ = live
    headers = {
        "Host": host.authority,
        "Origin": host.origin,
        "X-IMLP-Capability": host.capability,
        "Content-Type": "application/json",
        "Content-Length": "17",
    }
    headers[header] = value
    connection = http.client.HTTPConnection("127.0.0.1", host.server.server_port, timeout=3)
    try:
        connection.putrequest("POST", "/api/quit", skip_host=True)
        for name, entry in headers.items():
            connection.putheader(name, entry)
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == 403
        assert json.loads(response.read())["error"]
        assert not host.stop_requested.is_set()
    finally:
        connection.close()


@pytest.mark.parametrize(
    "override",
    [
        {"Content-Length": "262145"},
        {"Content-Length": "-1"},
        {"Content-Length": ""},
        {"Content-Type": "text/plain"},
        {"Content-Encoding": "gzip"},
        {"Transfer-Encoding": "chunked"},
    ],
)
def test_actual_out_of_bound_or_wrong_framing_is_refused_before_any_body(live, override):
    """A header-only sender proves early rejection without an unread-body Windows reset."""
    host, _ = live
    headers = {
        "Host": host.authority,
        "Origin": host.origin,
        "X-IMLP-Capability": host.capability,
        "Content-Type": "application/json",
        "Content-Length": "17",
        **override,
    }
    connection = http.client.HTTPConnection("127.0.0.1", host.server.server_port, timeout=3)
    try:
        connection.putrequest("POST", "/api/quit", skip_host=True)
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == 400 and json.loads(response.read())["error"]
        assert not host.stop_requested.is_set()
    finally:
        connection.close()


def test_json_framing_duplicate_nonfinite_depth_and_unknown_routes(live):
    host, client = live
    assert client.post("/api/quit", json={"quit": 1}).status_code == 404
    assert not host.stop_requested.is_set()
    for payload in [
        b'{"quit":true,"quit":true}',
        b'{"quit":NaN}',
        b"[]",
        b"\xff",
        b'{"deep":' + b"[" * 1500 + b"0" + b"]" * 1500 + b"}",
    ]:
        assert (
            client.post(
                "/api/quit", content=payload, headers={"Content-Type": "application/json"}
            ).status_code
            == 400
        )
    assert not host.stop_requested.is_set()
    assert client.post("/unknown", json={}).status_code == 404
    assert client.get("/api/history?q=a&q=b").status_code == 400
    assert client.get("/api/history?page=-1").status_code == 400
    assert client.get("/api/history/" + "a" * 32).status_code == 404
    assert client.get("/../workspace.sqlite3").status_code == 404
    for method in ("OPTIONS", "PUT", "TRACE"):
        response = client.request(method, "/api/history")
        assert (
            response.status_code == 501
            and "default-src 'none'" in response.headers["content-security-policy"]
        )
    for _ in range(4):
        assert host.slots.acquire(blocking=False)
    try:
        assert submit(client, session()).status_code == 429
    finally:
        for _ in range(4):
            host.slots.release()
    observed = []
    actual_reply = Handler.reply

    def reply(handler, status, value):
        if value == {"closing": True}:
            observed.append(host.stop_requested.is_set())
        return actual_reply(handler, status, value)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Handler, "reply", reply)
        assert client.post("/api/quit", json={"quit": True}).status_code == 200
    assert observed == [True]


def test_actual_held_engine_keeps_workspace_owned_until_real_completion(live, monkeypatch):
    host, client = live
    entered, release_event = threading.Event(), threading.Event()
    actual = host.engine.run

    def held(value):
        entered.set()
        if not release_event.wait(5):
            raise AssertionError("Test did not release its own operation")
        return actual(value)

    monkeypatch.setattr(host.engine, "run", held)
    errors = []

    def send():
        try:
            assert submit(client, session()).status_code == 201
        except BaseException as error:
            errors.append(error)

    worker = threading.Thread(target=send)
    worker.start()
    assert entered.wait(2)
    closer = threading.Thread(target=host.close)
    closer.start()
    try:
        assert closer.is_alive() and host.profile.descriptor >= 0
        with pytest.raises(OSError):
            store.Profile(host.profile.directory)
    finally:
        release_event.set()
    worker.join(5)
    closer.join(5)
    assert not errors and not worker.is_alive() and not closer.is_alive()
    assert host.closed and host.profile.descriptor == -1


def test_source_resources_are_real_and_bounded():
    engine, assets, metadata = resources.load_resources()
    assert metadata["sourceCommit"] == "development" and len(assets) == 5
    assert b"Industrial Memory Protocol Workbench" in assets["/"][1]
    assert engine.identity["version"] == "1.1.0"
