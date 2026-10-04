"""Single-process durable inference queue with atomic case/result commits."""

from __future__ import annotations

import fcntl
import logging
import threading
import time
from typing import Callable, TextIO

from complaintiq.storage import ComplaintStore, now

LOG = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, store: ComplaintStore, analyze: Callable):
        self.store, self.analyze = store, analyze
        self.guard = threading.Lock()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.lock_file: TextIO | None = None

    def start(self):
        with self.guard:
            if self.thread and self.thread.is_alive():
                return
            handle = self.store.path.with_suffix(".worker.lock").open("a")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                raise RuntimeError(
                    "Another application process owns this database queue."
                ) from None
            self.lock_file = handle
            self.stop_event.clear()
            with self.store._connect() as c:
                c.execute(
                    "UPDATE job_rows SET state='pending',started_at=NULL WHERE state='running'"
                )
                c.execute(
                    "UPDATE job_rows SET state='cancelled' WHERE state='pending' AND job_id IN (SELECT id FROM jobs WHERE cancelled=1)"
                )
            self.thread = threading.Thread(
                target=self.run, name="complaintiq-inference", daemon=True
            )
            self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=130)
        if self.lock_file and (not self.thread or not self.thread.is_alive()):
            fcntl.flock(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
            self.lock_file = None

    def run(self):
        while not self.stop_event.is_set():
            with self.store._connect() as c:
                c.execute("BEGIN IMMEDIATE")
                row = c.execute(
                    "SELECT r.* FROM job_rows r JOIN jobs j ON j.id=r.job_id WHERE r.state='pending' AND j.cancelled=0 ORDER BY j.created_at,r.position LIMIT 1"
                ).fetchone()
                if row:
                    c.execute(
                        "UPDATE job_rows SET state='running',started_at=? WHERE job_id=? AND position=?",
                        (now(), row["job_id"], row["position"]),
                    )
            if not row:
                self.stop_event.wait(0.2)
                continue
            started = time.monotonic()
            try:
                record = self.analyze(row["text"], persist=False, record_id=row["case_id"])
                with self.store._connect() as c:
                    c.execute("BEGIN IMMEDIATE")
                    self.store.save(record, c)
                    c.execute(
                        "UPDATE job_rows SET state='complete',finished_at=? WHERE job_id=? AND position=?",
                        (now(), row["job_id"], row["position"]),
                    )
                LOG.info(
                    "job_row_complete job=%s row=%s elapsed_ms=%d",
                    row["job_id"],
                    row["position"],
                    (time.monotonic() - started) * 1000,
                )
            except Exception as exc:
                LOG.warning(
                    "job_row_failed job=%s row=%s error_type=%s",
                    row["job_id"],
                    row["position"],
                    type(exc).__name__,
                )
                with self.store._connect() as c:
                    c.execute(
                        "UPDATE job_rows SET state='failed',error=?,finished_at=? WHERE job_id=? AND position=?",
                        (
                            "Analysis unavailable. Check the model connection, then retry failed rows.",
                            now(),
                            row["job_id"],
                            row["position"],
                        ),
                    )

    def wait(self, job_id: str, timeout: float = 300) -> dict:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            job = self.store.job(job_id)
            if job["status"] not in ("queued", "running"):
                return job
            time.sleep(0.1)
        raise TimeoutError("Processing continues in the queue. Open Imports to check progress.")
