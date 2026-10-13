"""Offline, validated SQLite restore with an exclusive worker lock."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complaintiq.locking import lock_exclusive  # noqa: E402
from complaintiq.storage import ComplaintStore  # noqa: E402


def restore(source: Path, destination: Path) -> Path | None:
    source, destination = source.resolve(), destination.resolve()
    if source == destination or not source.is_file():
        raise ValueError("Choose an existing backup different from the destination database.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.with_suffix(".worker.lock").open("a+") as lock:
        try:
            lock_exclusive(lock)
        except BlockingIOError:
            raise ValueError("Stop the application before restoring this database.") from None
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed.")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("Unsupported backup schema version.")
            db.execute("SELECT id,created_at,record FROM complaints LIMIT 1")
            if version == 1:
                for table in ("cases", "events", "jobs", "job_rows"):
                    db.execute(f"SELECT * FROM {table} LIMIT 1")
                if db.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Backup has invalid references.")
            temporary = destination.with_suffix(".restore-tmp")
            try:
                # closing(): release the file before it is renamed into place.
                with closing(sqlite3.connect(temporary)) as target:
                    db.backup(target)
                before = (
                    ComplaintStore(str(destination)).backup("pre-restore")
                    if destination.exists()
                    else None
                )
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        return before


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data/complaintiq.sqlite3",
    )
    args = parser.parse_args()
    try:
        before = restore(args.backup, args.database)
        print(f"Restored {args.database}. Pre-restore backup: {before or 'new database'}")
    except (ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Restore failed: {exc}\n")
