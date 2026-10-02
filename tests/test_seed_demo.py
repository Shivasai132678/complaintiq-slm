"""Seeding creates a usable queue without duplicating existing history."""

from pathlib import Path

from complaintiq.service import ComplaintService
from scripts.seed_demo import seed_demo


def test_seed_populates_public_records_and_is_idempotent(tmp_path: Path) -> None:
    database = str(tmp_path / "demo.sqlite3")
    assert seed_demo(database, limit=3) == 3
    rows = ComplaintService(db_path=database).list_complaints()
    assert len(rows) == 3
    assert all(row["backend"] == "baseline" and row["text"] for row in rows)
    assert {row["product"] for row in rows} == {
        "Checking or savings account",
        "Credit card",
        "Credit reporting",
    }
    assert seed_demo(database, limit=3) == 0
    assert len(ComplaintService(db_path=database).list_complaints()) == 3
