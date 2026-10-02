"""Populate an empty local queue from held-out public CFPB demo records."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from complaintiq.service import ComplaintService


def seed_demo(db_path: str, limit: int = 30) -> int:
    """Avoid duplicate seeding and never alter the source evaluation CSV."""
    service = ComplaintService(db_path=db_path)
    if service.list_complaints():
        return 0
    source = Path(__file__).resolve().parents[1] / "data" / "test.csv"
    with source.open(newline="", encoding="utf-8") as handle:
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in csv.DictReader(handle):
            groups[row["product"]].append(row)
        # Interleave product families so a small dashboard sample is useful.
        rows: list[dict[str, str]] = []
        while groups and len(rows) < limit:
            for product in list(groups):
                rows.append(groups[product].pop(0))
                if not groups[product]:
                    del groups[product]
                if len(rows) == limit:
                    break
    for row in rows:
        service.analyze(row["text"][:6000])
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/complaintiq.sqlite3")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 100:
        parser.error("--limit must be between 1 and 100")
    print(f"Saved {seed_demo(args.db, args.limit)} public demo complaints.")
