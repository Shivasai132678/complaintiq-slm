"""Versioned SQLite storage, immutable predictions and auditable local review."""

from __future__ import annotations

import builtins
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

OUTSIDE = "Outside supported scope"
FIELDS = ("product", "issue", "priority", "department")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Conflict(ValueError):
    pass


class _ClosingConnection(sqlite3.Connection):
    """Commits or rolls back like sqlite3, then also closes at the end of a `with` block.

    Connections are never left open, so database files can be safely replaced or removed.
    """

    def __exit__(self, *exc: Any) -> Any:
        try:
            return super().__exit__(*exc)
        finally:
            self.close()


class ComplaintStore:
    def __init__(self, db_path: str) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            with self._connect() as c:
                version = c.execute("PRAGMA user_version").fetchone()[0]
            if version < 1:
                self.backup("migration")
        with self._connect() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS complaints (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY REFERENCES complaints(id), created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Queued',
                    product TEXT NOT NULL, issue TEXT NOT NULL, priority TEXT NOT NULL,
                    department TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 0,
                    review_flag INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1);
                CREATE INDEX IF NOT EXISTS cases_queue ON cases(status, created_at);
                CREATE INDEX IF NOT EXISTS cases_filters ON cases(product, priority, department);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES cases(id),
                    at TEXT NOT NULL, kind TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS events_case ON events(case_id, seq);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE, digest TEXT NOT NULL,
                    created_at TEXT NOT NULL, source TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS job_rows (
                    job_id TEXT NOT NULL REFERENCES jobs(id), position INTEGER NOT NULL,
                    text TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending', case_id TEXT NOT NULL UNIQUE,
                    error TEXT, started_at TEXT, finished_at TEXT, PRIMARY KEY(job_id, position));
                CREATE INDEX IF NOT EXISTS job_pending ON job_rows(state, job_id, position);
            """)
            for row in c.execute("SELECT id,created_at,record FROM complaints").fetchall():
                self._metadata(c, json.loads(row["record"]))
            c.execute("PRAGMA user_version=1")
        self.backup("auto", daily=True)

    def _connect(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.path), timeout=15, factory=_ClosingConnection)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def _metadata(self, c: sqlite3.Connection, r: dict) -> None:
        c.execute(
            "INSERT OR IGNORE INTO cases(id,created_at,updated_at,status,product,issue,priority,department,review_flag) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                r["id"],
                r["created_at"],
                r["created_at"],
                "Queued",
                *(r.get(k, "") for k in FIELDS),
                int(r.get("status") == "Needs review"),
            ),
        )

    def save(self, record: dict[str, Any], connection: sqlite3.Connection | None = None) -> None:
        def write(c):
            c.execute(
                "INSERT INTO complaints VALUES(?,?,?)",
                (record["id"], record["created_at"], json.dumps(record)),
            )
            self._metadata(c, record)

        if connection is not None:
            write(connection)
        else:
            with self._connect() as c:
                write(c)

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as c:
            return [
                json.loads(r[0])
                for r in c.execute(
                    "SELECT record FROM complaints ORDER BY created_at DESC,rowid DESC"
                )
            ]

    @staticmethod
    def _case(row) -> dict:
        original = json.loads(row["record"])
        return {
            **original,
            **{
                k: row[k]
                for k in ("status", *FIELDS, "confirmed", "review_flag", "revision", "updated_at")
            },
            "original": original,
        }

    def get(self, case_id: str) -> dict:
        with self._connect() as c:
            row = c.execute(
                "SELECT c.*, p.record FROM cases c JOIN complaints p ON p.id=c.id WHERE c.id=?",
                (case_id,),
            ).fetchone()
            if row is None:
                raise KeyError(case_id)
            result = self._case(row)
            result["events"] = [
                {**dict(e), "detail": json.loads(e["detail"])}
                for e in c.execute(
                    "SELECT * FROM events WHERE case_id=? ORDER BY seq DESC", (case_id,)
                )
            ]
            return result

    def search(
        self,
        *,
        q: str = "",
        status: str = "",
        product: str = "",
        priority: str = "",
        department: str = "",
        start: str = "",
        end: str = "",
        confirmed: str = "",
        sort: str = "newest",
        page: int = 1,
        page_size: int = 25,
        urgent: str = "",
    ) -> dict:
        clauses, args = [], []
        for k, v in [
            ("status", status),
            ("product", product),
            ("priority", priority),
            ("department", department),
        ]:
            if v:
                clauses.append(f"c.{k}=?")
                args.append(v)
        if confirmed in ("0", "1"):
            clauses.append("c.confirmed=?")
            args.append(confirmed)
        if urgent == "1":
            clauses.append("c.status!='Resolved' AND c.priority IN ('High','Critical')")
        if q:
            clauses.append(
                "(instr(lower(json_extract(p.record,'$.text')),lower(?))>0 OR instr(lower(c.id),lower(?))>0)"
            )
            args.extend([q, q])
        if start:
            clauses.append("substr(c.created_at,1,10)>=?")
            args.append(start)
        if end:
            clauses.append("substr(c.created_at,1,10)<=?")
            args.append(end)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        base = " FROM cases c JOIN complaints p ON p.id=c.id" + where
        ordering = {
            "newest": "c.created_at DESC,c.id",
            "oldest": "c.created_at,c.id",
            "priority": "CASE c.priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,c.created_at DESC,c.id",
        }.get(sort, "c.created_at DESC,c.id")
        with self._connect() as c:
            total = c.execute("SELECT count(*)" + base, args).fetchone()[0]
            rows = c.execute(
                "SELECT c.*,p.record" + base + " ORDER BY " + ordering + " LIMIT ? OFFSET ?",
                [*args, page_size, (page - 1) * page_size],
            ).fetchall()
        return {
            "items": [self._case(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def change(self, case_id: str, revision: int, kind: str, payload: dict, taxonomy: dict) -> dict:
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if row is None:
                raise KeyError(case_id)
            if row["revision"] != revision:
                raise Conflict(
                    "This case changed in another tab. Reload the case before saving; your draft is still here."
                )
            reason = payload.get("reason", "").strip()
            timestamp = now()
            detail: dict[str, Any] = {}
            if kind == "review":
                if row["status"] == "Resolved":
                    raise ValueError("Reopen the case before changing its review.")
                product, issue = payload["product"], payload["issue"]
                if not (
                    (product == OUTSIDE and issue == OUTSIDE) or issue in taxonomy.get(product, [])
                ):
                    raise ValueError(
                        "Choose a supported product and issue pair, or Outside supported scope."
                    )
                if payload["priority"] not in ("Low", "Medium", "High", "Critical"):
                    raise ValueError("Choose a valid priority.")
                from complaintiq.triage import DEPARTMENTS

                if payload["department"] not in [*DEPARTMENTS.values(), "Manual Review Team"]:
                    raise ValueError("Choose a valid department.")
                changes = {
                    k: {"from": row[k], "to": payload[k]} for k in FIELDS if row[k] != payload[k]
                }
                if changes and not reason:
                    raise ValueError(
                        "A reason is required when changing a classification, priority or department."
                    )
                c.execute(
                    "UPDATE cases SET product=?,issue=?,priority=?,department=?,confirmed=1 WHERE id=?",
                    (*(payload[k] for k in FIELDS), case_id),
                )
                detail = {"changes": changes, "reason": reason, "confirmed": True}
            elif kind == "note":
                if not reason:
                    raise ValueError("Enter a note.")
                detail = {"note": reason}
            elif kind == "transition":
                target = payload["status"]
                allowed = {
                    "Queued": {"In review", "Resolved"},
                    "In review": {"Queued", "Resolved"},
                    "Resolved": {"In review"},
                }
                if target not in allowed[row["status"]]:
                    raise ValueError("This status transition is not allowed.")
                if (target == "Resolved" or row["status"] == "Resolved") and not reason:
                    raise ValueError("Add a resolution or reopening reason.")
                if target == "Resolved" and not row["confirmed"]:
                    raise ValueError("Confirm or correct the classification before resolving.")
                c.execute("UPDATE cases SET status=? WHERE id=?", (target, case_id))
                detail = {"from": row["status"], "to": target, "reason": reason}
            else:
                raise ValueError("Unknown case action.")
            c.execute(
                "UPDATE cases SET revision=revision+1,updated_at=? WHERE id=?", (timestamp, case_id)
            )
            c.execute(
                "INSERT INTO events(case_id,at,kind,actor,detail) VALUES(?,?,?,?,?)",
                (case_id, timestamp, kind, "Local operator", json.dumps(detail)),
            )
        return self.get(case_id)

    def overview(self) -> dict:
        with self._connect() as c:
            counts = dict(c.execute("SELECT status,count(*) FROM cases GROUP BY status").fetchall())
            by_product = dict(
                c.execute("SELECT product,count(*) FROM cases GROUP BY product").fetchall()
            )
            high = c.execute(
                "SELECT count(*) FROM cases WHERE status!='Resolved' AND priority IN ('High','Critical')"
            ).fetchone()[0]
            unreviewed = c.execute(
                "SELECT count(*) FROM cases WHERE confirmed=0 AND status!='Resolved'"
            ).fetchone()[0]
            events = [
                {**dict(r), "detail": json.loads(r["detail"])}
                for r in c.execute("SELECT * FROM events ORDER BY seq DESC LIMIT 8")
            ]
        return {
            "total": sum(counts.values()),
            "by_status": counts,
            "by_product": by_product,
            "high_open": high,
            "unreviewed": unreviewed,
            "activity": events,
        }

    def backup(self, kind: str = "manual", daily: bool = False) -> Path:
        folder = self.path.parent / "backups"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d" if daily else "%Y%m%dT%H%M%S%f")
        dest = folder / f"{self.path.stem}-{kind}-{stamp}.sqlite3"
        if not dest.exists():
            temp = dest.with_suffix(".partial")
            try:
                # closing(): a sqlite3 context manager only commits; close the
                # connections so the backup file is complete before it is renamed.
                with closing(self._connect()) as source, closing(sqlite3.connect(temp)) as target:
                    source.backup(target)
                    if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("Backup validation failed.")
                temp.replace(dest)
            finally:
                temp.unlink(missing_ok=True)
        if kind == "auto":
            for old in sorted(folder.glob(f"{self.path.stem}-auto-*.sqlite3"))[:-7]:
                old.unlink()
        return dest

    def submit_job(self, texts: builtins.list[str], request_key: str, source: str) -> dict:
        digest = hashlib.sha256(json.dumps([texts, source]).encode()).hexdigest()
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            old = c.execute(
                "SELECT id,digest FROM jobs WHERE request_key=?", (request_key,)
            ).fetchone()
            if old:
                if old["digest"] != digest:
                    raise Conflict("This request key was used for a different submission.")
                job_id = old["id"]
            else:
                job_id = "JOB-" + uuid4().hex[:12].upper()
                c.execute(
                    "INSERT INTO jobs VALUES(?,?,?,?,?,0)",
                    (job_id, request_key, digest, now(), source),
                )
                c.executemany(
                    "INSERT INTO job_rows(job_id,position,text,case_id) VALUES(?,?,?,?)",
                    [(job_id, i, t, "CQ-" + uuid4().hex[:10].upper()) for i, t in enumerate(texts)],
                )
        return self.job(job_id)

    def job(self, job_id: str) -> dict:
        with self._connect() as c:
            job = c.execute(
                "SELECT id,created_at,source,cancelled FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
            if job is None:
                raise KeyError(job_id)
            rows = [
                dict(r)
                for r in c.execute(
                    "SELECT position,text,state,case_id,error,started_at,finished_at FROM job_rows WHERE job_id=? ORDER BY position",
                    (job_id,),
                )
            ]
        counts = {
            s: sum(r["state"] == s for r in rows)
            for s in ("pending", "running", "complete", "failed", "cancelled")
        }
        state = (
            "running"
            if counts["running"]
            else "queued"
            if counts["pending"]
            else "cancelled"
            if job["cancelled"]
            else "completed_with_errors"
            if counts["failed"]
            else "complete"
        )
        return {**dict(job), "rows": rows, "counts": counts, "status": state, "total": len(rows)}

    def jobs(self) -> builtins.list[dict]:
        with self._connect() as c:
            ids = [r[0] for r in c.execute("SELECT id FROM jobs ORDER BY created_at DESC LIMIT 50")]
        return [self.job(i) for i in ids]

    def control_job(self, job_id: str, action: str) -> dict:
        self.job(job_id)
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            if action == "cancel":
                c.execute("UPDATE jobs SET cancelled=1 WHERE id=?", (job_id,))
                c.execute(
                    "UPDATE job_rows SET state='cancelled',finished_at=? WHERE job_id=? AND state='pending'",
                    (now(), job_id),
                )
            else:
                c.execute("UPDATE jobs SET cancelled=0 WHERE id=?", (job_id,))
                c.execute(
                    "UPDATE job_rows SET state='pending',error=NULL,started_at=NULL,finished_at=NULL WHERE job_id=? AND state='failed'",
                    (job_id,),
                )
        return self.job(job_id)
