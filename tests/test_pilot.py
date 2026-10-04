"""Pilot acceptance: migration, review integrity, queue recovery and restore."""

import csv
import io
import json
import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient

from complaintiq.api import create_app
from complaintiq.jobs import JobRunner
from complaintiq.storage import OUTSIDE, ComplaintStore, Conflict
from scripts.restore_backup import restore

TAXONOMY = {"Credit card": ["Billing disputes", "Fees or interest"]}


def record(text="A disputed card payment", record_id="CQ-ONE"):
    return {
        "id": record_id,
        "created_at": "2026-10-04T00:00:00+00:00",
        "text": text,
        "product": "Credit card",
        "issue": "Billing disputes",
        "priority": "Low",
        "department": "Card Services Team",
        "status": "Needs review",
        "backend": "slm",
        "model_version": "test.gguf",
        "latency_ms": 100,
        "priority_reason": "No match",
        "action": "Review",
        "summary": text,
        "explanation": [],
    }


def review(revision=1, **kwargs):
    return {
        "revision": revision,
        "product": "Credit card",
        "issue": "Billing disputes",
        "priority": "Low",
        "department": "Card Services Team",
        "reason": "",
        **kwargs,
    }


def test_migration_keeps_original_and_does_not_invent_events(tmp_path):
    path = tmp_path / "old.sqlite"
    r = record()
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE complaints(id TEXT PRIMARY KEY,created_at TEXT,record TEXT)")
        c.execute("INSERT INTO complaints VALUES(?,?,?)", (r["id"], r["created_at"], json.dumps(r)))
    store = ComplaintStore(str(path))
    result = store.get("CQ-ONE")
    assert result["original"] == r
    assert result["status"] == "Queued" and result["review_flag"] == 1
    assert result["confirmed"] == 0 and result["events"] == []
    assert len(list((tmp_path / "backups").glob("*migration*"))) == 1
    assert ComplaintStore(str(path)).get("CQ-ONE") == result


def test_review_lifecycle_and_optimistic_conflicts(tmp_path):
    store = ComplaintStore(str(tmp_path / "db"))
    original = record()
    store.save(original)
    with pytest.raises(ValueError, match="reason"):
        store.change("CQ-ONE", 1, "review", review(issue="Fees or interest"), TAXONOMY)
    with pytest.raises(ValueError, match="supported"):
        store.change("CQ-ONE", 1, "review", review(issue="Invented"), TAXONOMY)
    with pytest.raises(ValueError, match="Confirm"):
        store.change("CQ-ONE", 1, "transition", {"status": "Resolved", "reason": "Done"}, TAXONOMY)
    r = store.change(
        "CQ-ONE", 1, "review", review(issue="Fees or interest", reason="Fee dispute"), TAXONOMY
    )
    assert r["original"] == original and r["revision"] == 2 and r["confirmed"] == 1
    with pytest.raises(Conflict):
        store.change("CQ-ONE", 1, "note", {"reason": "Stale"}, TAXONOMY)
    r = store.change("CQ-ONE", 2, "note", {"reason": "Called customer"}, TAXONOMY)
    r = store.change(
        "CQ-ONE", 3, "transition", {"status": "Resolved", "reason": "Fee reviewed"}, TAXONOMY
    )
    assert r["status"] == "Resolved"
    with pytest.raises(ValueError, match="reason"):
        store.change("CQ-ONE", 4, "transition", {"status": "In review", "reason": ""}, TAXONOMY)
    r = store.change(
        "CQ-ONE", 4, "transition", {"status": "In review", "reason": "New evidence"}, TAXONOMY
    )
    assert len(r["events"]) == 4 and r["original"] == original
    assert store.overview()["by_status"] == {"In review": 1}


def test_queue_idempotency_atomic_results_and_recovery(tmp_path):
    store = ComplaintStore(str(tmp_path / "db"))
    job = store.submit_job(["one", "two"], "same-request-key", "import")
    assert store.submit_job(["one", "two"], "same-request-key", "import")["id"] == job["id"]
    with pytest.raises(Conflict):
        store.submit_job(["different"], "same-request-key", "import")
    # Simulate a process crash after claiming a row but before committing a case.
    with store._connect() as c:
        c.execute("UPDATE job_rows SET state='running' WHERE position=0")
    calls = []

    def analyze(text, persist, record_id):
        calls.append(text)
        assert persist is False
        return record(text, record_id)

    runner = JobRunner(store, analyze)
    runner.start()
    try:
        complete = runner.wait(job["id"], 5)
        assert complete["counts"]["complete"] == 2
        assert len(store.list()) == 2
        assert calls == ["one", "two"]
        store.submit_job(["one", "two"], "same-request-key", "import")
        assert len(store.list()) == 2
        other = JobRunner(store, analyze)
        with pytest.raises(RuntimeError, match="Another"):
            other.start()
    finally:
        runner.stop()
    runner.start()
    runner.stop()
    assert len(store.list()) == 2


def test_cancel_allows_active_row_and_retry_only_failed(tmp_path):
    store = ComplaintStore(str(tmp_path / "db"))
    entered, release = threading.Event(), threading.Event()

    def analyze(text, persist, record_id):
        if text == "one":
            entered.set()
            release.wait(5)
        return record(text, record_id)

    j = store.submit_job(["one", "two"], "cancel-request", "import")
    runner = JobRunner(store, analyze)
    runner.start()
    try:
        assert entered.wait(3)
        store.control_job(j["id"], "cancel")
        release.set()
        result = runner.wait(j["id"], 5)
        assert result["counts"]["complete"] == 1 and result["counts"]["cancelled"] == 1
    finally:
        release.set()
        runner.stop()
    attempts = []

    def flaky(text, persist, record_id):
        attempts.append(text)
        if text == "bad" and attempts.count("bad") == 1:
            raise RuntimeError("secret narrative must not enter error response")
        return record(text, record_id)

    j = store.submit_job(["good", "bad"], "retry-request", "import")
    runner = JobRunner(store, flaky)
    runner.start()
    try:
        result = runner.wait(j["id"], 5)
        assert result["counts"]["failed"] == 1
        assert "secret" not in result["rows"][1]["error"]
        store.control_job(j["id"], "retry")
        assert runner.wait(j["id"], 5)["counts"]["complete"] == 2
        assert attempts == ["good", "bad", "bad"]
    finally:
        runner.stop()


def test_backup_restore_and_lock(tmp_path):
    store = ComplaintStore(str(tmp_path / "source.sqlite"))
    store.save(record())
    store.change("CQ-ONE", 1, "note", {"reason": "Persistent note"}, TAXONOMY)
    backup = store.backup()
    target = tmp_path / "restored.sqlite"
    assert restore(backup, target) is None
    assert ComplaintStore(str(target)).get("CQ-ONE") == store.get("CQ-ONE")
    runner = JobRunner(store, lambda *args: None)
    runner.start()
    try:
        with pytest.raises(ValueError, match="Stop"):
            restore(backup, store.path)
    finally:
        runner.stop()
    assert restore(backup, target).is_file()


@pytest.fixture
def pilot_client(tmp_path):
    app = create_app(db_path=tmp_path / "api.sqlite")
    app.state.store.save(record())
    with TestClient(app) as client:
        yield client


def test_api_review_exports_origin_and_model_down(pilot_client):
    c = pilot_client
    # Reading case storage never instantiates the configured inference engine.
    assert c.app.state.service is None
    assert c.get("/api/cases").json()["total"] == 1
    assert c.get("/api/cases?q=payment").json()["total"] == 1
    assert c.get("/api/cases?status=Resolved").json()["total"] == 0
    assert c.get("/api/cases?start=invalid").status_code == 422
    assert c.get("/api/cases/CQ-ONE").json()["confirmed"] == 0
    assert (
        len(list(csv.DictReader(io.StringIO(c.get("/api/cases/export?kind=reviewed").text)))) == 0
    )
    assert c.patch("/api/cases/CQ-ONE/review", json=review()).status_code == 200
    assert c.patch("/api/cases/CQ-ONE/review", json=review()).status_code == 409
    rows = list(csv.DictReader(io.StringIO(c.get("/api/cases/export?kind=reviewed").text)))
    assert len(rows) == 1
    assert (
        c.patch(
            "/api/cases/CQ-ONE/review",
            json=review(
                2,
                product=OUTSIDE,
                issue=OUTSIDE,
                department="Manual Review Team",
                reason="Mortgage complaint",
            ),
        ).status_code
        == 200
    )
    assert (
        len(list(csv.DictReader(io.StringIO(c.get("/api/cases/export?kind=reviewed").text)))) == 0
    )
    assert (
        c.post("/api/backups", json={}, headers={"Origin": "https://untrusted.example"}).status_code
        == 403
    )
    assert (
        c.post("/api/backups", json={}, headers={"Origin": "http://testserver"}).status_code == 200
    )
    assert c.get("/api/cases", headers={"Host": "evil.example"}).status_code == 400
    assert (
        c.post("/api/jobs", json={"texts": ["a"] * 101, "request_key": "abcdefgh"}).status_code
        == 422
    )
    assert c.app.state.service is None
