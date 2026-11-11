"""@file test_studio_boundaries.py
@brief Independent malformed-child, resource, IPC and store contract negatives by Jason Stys.
@details Actual valid reports come from the real C++ engine; corruptions must fail before saving.
"""

import copy
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from types import SimpleNamespace

import pytest
from test_studio_service import independent_frame, session

from imlp_studio import store
from imlp_studio.domain import canonical, control, fields, hexadecimal, integer, request
from imlp_studio.engine import Engine, validate_report, wire_frame
from imlp_studio.private_io import bounded


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        {"kind": "host"},
        {"kind": []},
        {"kind": "inspect", "frame_hex": "f"},
        {"kind": "inspect", "frame_hex": "ff" * 279},
        {"kind": "inspect", "frame_hex": "  "},
        {"kind": "stream", "chunks_hex": []},
        {"kind": "stream", "chunks_hex": ["00" * 4097]},
        {"kind": "stream", "chunks_hex": [""] * 257},
    ],
)
def test_closed_input_shape_extent_and_hex_refusals(value):
    with pytest.raises(ValueError):
        request(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("writes_enabled", 1),
        ("write_allow_begin", -1),
        ("write_allow_end", 1),
        ("read_attempts", True),
        ("read_attempts", 4),
        ("operations", []),
        ("operations", [None]),
        ("operations", [{"verb": "exec"}]),
    ],
)
def test_typed_session_refusals(field, value):
    submitted = session()
    submitted[field] = value
    with pytest.raises(ValueError):
        request(submitted)


@pytest.mark.parametrize(
    "field,value",
    [
        ("address", True),
        ("deadline_ms", 1001),
        ("faults", ["timeout"] * 4),
        ("faults", [False]),
        ("faults", "timeout"),
        ("payload_hex", "00" * 257),
    ],
)
def test_typed_operation_refusals(field, value):
    submitted = session()
    submitted["operations"][0][field] = value
    with pytest.raises(ValueError):
        request(submitted)


def test_canonical_and_direct_helpers_refuse_unsupported_types_and_large_input():
    for value in [{"x": object()}, {"x": float("nan")}]:
        with pytest.raises(ValueError):
            canonical(value)
    with pytest.raises(ValueError):
        fields({}, {"required"}, "fixture")
    with pytest.raises(ValueError):
        integer(1.0, "count", 0, 1)
    with pytest.raises(ValueError):
        hexadecimal(None, "bytes", 1)
    value = session()
    value["oversized"] = "x" * (256 * 1024)
    with pytest.raises(ValueError, match="256 KiB"):
        request(value)


@pytest.mark.parametrize(
    "change",
    [
        "bridge-bool",
        "source",
        "input-crc",
        "extra-field",
        "trace-count",
        "trace-sequence",
        "trace-direction",
        "trace-detail",
        "trace-request",
        "operation-id",
        "attempts",
        "client-error",
        "remote-status",
        "detail",
        "trace-partition",
        "before-size",
        "read-changed",
        "counter-bool",
        "counter-sum",
        "success-data",
        "whole-map",
    ],
)
def test_actual_session_report_corruptions_refused(engine, change):
    submitted = session()
    report = engine.run(submitted)
    report.pop("status")
    report.pop("input_sha256")
    if change == "bridge-bool":
        report["bridge_version"] = True
    elif change == "source":
        report["source_commit"] = "other"
    elif change == "input-crc":
        report["input_crc32"] ^= 1
    elif change == "extra-field":
        report["host_endpoint"] = "not accepted"
    elif change == "trace-count":
        report["trace"].pop()
    elif change == "trace-sequence":
        report["trace"][0]["sequence"] = 2
    elif change == "trace-direction":
        report["trace"][0]["direction"] = "server_to_client"
    elif change == "trace-detail":
        report["trace"][0]["outcome"] = "x" * 257
    elif change == "trace-request":
        report["trace"][0]["hex"] = independent_frame(identity=99).hex()
    elif change == "operation-id":
        report["operations"][0]["request_id"] = 2
    elif change == "attempts":
        report["operations"][0]["attempts"] = 2
    elif change == "client-error":
        report["operations"][0]["client_error"] = "invented"
    elif change == "remote-status":
        report["operations"][0]["remote_status"] = 6
    elif change == "detail":
        report["operations"][0]["detail"] = "x" * 513
    elif change == "trace-partition":
        report["operations"][1]["trace_begin"] = 0
    elif change == "before-size":
        report["operations"][0]["before"]["hex"] = ""
    elif change == "read-changed":
        report["operations"][1]["after"]["hex"] = "00" * 6
    elif change == "counter-bool":
        report["metrics"]["operations"] = True
    elif change == "counter-sum":
        report["metrics"]["retries"] = 1
    elif change == "success-data":
        report["operations"][1]["data_hex"] = ""
    else:
        report["final_readable_hex"] = "00"
    with pytest.raises(ValueError):
        validate_report(submitted, report, control(submitted), "development")


@pytest.mark.parametrize(
    "change",
    [
        "byte-count",
        "pending",
        "frames-type",
        "offset",
        "extent",
        "slice",
        "frame-bool",
        "issues-type",
        "issue-error",
        "issue-overlap",
        "omitted-negative",
        "accounting",
    ],
)
def test_actual_stream_report_corruptions_refused(engine, change):
    submitted = {"kind": "stream", "chunks_hex": [(b"noise" + independent_frame()).hex()]}
    report = engine.run(submitted)
    report.pop("status")
    report.pop("input_sha256")
    if change == "byte-count":
        report["input_bytes"] = True
    elif change == "pending":
        report["pending_bytes"] = 1
    elif change == "frames-type":
        report["frames"] = {}
    elif change == "offset":
        report["frames"][0]["offset"] = -1
    elif change == "extent":
        report["frames"][0]["wire_bytes"] = 20
    elif change == "slice":
        report["frames"][0]["hex"] = independent_frame(identity=8).hex()
    elif change == "frame-bool":
        report["frames"][0]["frame"]["version"] = True
    elif change == "issues-type":
        report["issues"] = {}
    elif change == "issue-error":
        report["issues"][0]["error"] = "none"
    elif change == "issue-overlap":
        report["issues"][0]["bytes"] = 6
    elif change == "omitted-negative":
        report["omitted_issue_records"] = -1
    else:
        report["omitted_issue_bytes"] = 1
    with pytest.raises(ValueError):
        validate_report(submitted, report, control(submitted), "development")


@pytest.mark.parametrize(
    "change", ["accepted-type", "error", "submitted-bytes", "fields", "false-blocked", "wire-crc"]
)
def test_frame_evidence_cannot_claim_false_acceptance(engine, change):
    submitted = {"kind": "inspect", "frame_hex": independent_frame().hex()}
    report = engine.run(submitted)
    report.pop("status")
    report.pop("input_sha256")
    if change == "accepted-type":
        report["accepted"] = 1
    elif change == "error":
        report["error"] = "checksum_mismatch"
    elif change == "submitted-bytes":
        report["hex"] = independent_frame(identity=8).hex()
    elif change == "fields":
        report["frame"]["address"] = 257
    elif change == "false-blocked":
        report["accepted"] = False
    else:
        report["hex"] = report["hex"][:-2] + "00"
    with pytest.raises(ValueError):
        validate_report(submitted, report, control(submitted), "development")


def test_wire_shape_magic_length_and_crc_have_independent_refusals():
    for raw in [b"", b"x" * 22, independent_frame()[:-1], independent_frame()[:-1] + b"\x00"]:
        with pytest.raises(ValueError):
            wire_frame(raw)


@pytest.mark.parametrize(
    "output,code,stderr",
    [
        (b"not-json", 0, b""),
        (b"\xff", 0, b""),
        (b"[]", 0, b""),
        (b"{}", 0, b""),
        (b"{}", 7, b""),
        (b"{}", 0, b"unexpected"),
        (b"x" * (8 * 1024 * 1024 + 1), 0, b""),
        (b'{"a":1,"a":2}', 0, b""),
        (b'{"a":NaN}', 0, b""),
    ],
    ids=[
        "invalid-json",
        "invalid-utf8",
        "array",
        "empty-object",
        "nonzero-exit",
        "unexpected-stderr",
        "output-budget",
        "duplicate-key",
        "nonfinite-json",
    ],
)
def test_untrusted_child_shape_never_becomes_saved_success(
    engine, monkeypatch, output, code, stderr
):
    def fake_run(arguments, **kwargs):
        assert arguments == [str(engine.executable), "run"]
        assert kwargs["input"] == control(session()) and kwargs["timeout"] == 15
        assert "PYTHONPATH" not in kwargs["env"] and "shell" not in kwargs
        return SimpleNamespace(returncode=code, stdout=output, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ValueError):
        engine.run(session())


@pytest.mark.parametrize(
    "error", [OSError("inert error"), subprocess.TimeoutExpired("fixed child", 15)]
)
def test_child_failure_is_explicit_not_a_record(engine, monkeypatch, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(ValueError):
        engine.run(session())


def test_engine_identity_digest_source_and_unavailable_child_refusals(engine, monkeypatch):
    with pytest.raises(ValueError, match="digest"):
        Engine(engine.executable, "development", "0" * 64)
    digest = engine.identity["sha256"]
    with pytest.raises(ValueError, match="source/version"):
        Engine(engine.executable, "wrong-source", digest)

    def unavailable(*args, **kwargs):
        raise OSError("inert process failure")

    monkeypatch.setattr(subprocess, "check_output", unavailable)
    with pytest.raises(ValueError, match="unavailable"):
        Engine(engine.executable, "development", digest)


def test_store_rejects_misbound_input_source_and_outcome(engine, tmp_path):
    owner = store.Profile(tmp_path / "workspace")
    try:
        value = session()
        actual = engine.run(value)
        for key, altered in [
            ("input_sha256", "0" * 64),
            ("source_commit", "other"),
            ("status", "blocked"),
            ("status", "error"),
        ]:
            report = copy.deepcopy(actual)
            report[key] = altered
            with pytest.raises(ValueError):
                owner.store.save("not retained", value, report, engine.identity)
        for title in [None, "", "x" * 101]:
            with pytest.raises(ValueError):
                owner.store.save(title, value, actual, engine.identity)
        for query in [True, "x" * 101]:
            with pytest.raises(ValueError):
                owner.store.history(query)
        with pytest.raises(ValueError):
            owner.store.history(page=True)
        with pytest.raises(ValueError):
            owner.store.get(False)
        assert owner.store.history()["total"] == 0
    finally:
        owner.close()


@pytest.mark.parametrize(
    "marker",
    [
        [],
        {},
        {"schema_version": True, "product": "industrial-memory-protocol-workbench"},
        {"schema_version": 2, "product": "industrial-memory-protocol-workbench"},
        {"schema_version": 1, "product": "other"},
    ],
)
def test_unknown_marker_is_not_overwritten(tmp_path, marker):
    directory = tmp_path / "workspace"
    directory.mkdir()
    path = directory / "profile.json"
    path.write_text(json.dumps(marker), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        store.Profile(directory)
    assert path.read_bytes() == before and list(directory.iterdir()) == [path]


def test_future_database_not_migrated_or_reset(tmp_path):
    directory = tmp_path / "workspace"
    owner = store.Profile(directory)
    owner.close()
    path = directory / "workspace.sqlite3"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA user_version=99")
        connection.commit()
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Unsupported"):
        store.Profile(directory)
    assert path.read_bytes() == before


def test_default_locations_are_explicit_os_user_paths(tmp_path, monkeypatch):
    for system, variable in [("win32", "LOCALAPPDATA"), ("linux", "XDG_DATA_HOME")]:
        monkeypatch.setattr(sys, "platform", system)
        monkeypatch.setenv(variable, str(tmp_path / "data"))
        assert (
            store.default_directory()
            == tmp_path / "data/JasonStysPortfolio/industrial-memory-protocol-workbench/profile"
        )
        monkeypatch.setenv(variable, "relative-path")
        with pytest.raises(ValueError):
            store.default_directory()
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(store.Path, "home", lambda: tmp_path)
    assert (
        store.default_directory()
        == tmp_path
        / "Library/Application Support/JasonStysPortfolio"
        / "industrial-memory-protocol-workbench/profile"
    )


def test_actual_bounded_descriptor_reader_type_size_growth_and_closed_on_error(
    tmp_path, monkeypatch
):
    path = tmp_path / "resource"
    path.write_bytes(b"abcd")
    assert bounded(path, 4) == b"abcd"
    with pytest.raises(ValueError):
        bounded(path, 3)
    with pytest.raises((ValueError, OSError)):
        bounded(tmp_path, 4)
    actual_read = os.read

    def shortened(descriptor, count):
        return actual_read(descriptor, min(count, 1))

    monkeypatch.setattr(os, "read", shortened)
    assert bounded(path, 4) == b"abcd"

    def interrupted(*args):
        raise OSError("inert interrupted read")

    monkeypatch.setattr(os, "read", interrupted)
    with pytest.raises(OSError):
        bounded(path, 4)
