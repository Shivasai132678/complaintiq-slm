"""Prepare a bounded, deduplicated CFPB narrative dataset from an official archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

PRODUCTS = {
    "Credit reporting": "Credit reporting",
    "Credit reporting, credit repair services, or other personal consumer reports": "Credit reporting",
    "Credit reporting or other personal consumer reports": "Credit reporting",
    "Credit card": "Credit card",
    "Credit card or prepaid card": "Credit card",
    "Bank account or service": "Checking or savings account",
    "Checking or savings account": "Checking or savings account",
}
ISSUE_ALIASES = {
    "Incorrect information on credit report": "Incorrect information on your report",
    "Problem with credit reporting company's investigation": "Problem with a credit reporting company's investigation into an existing problem",
    "Problem with a company's investigation into an existing problem": "Problem with a credit reporting company's investigation into an existing problem",
    "Problem with a purchase shown on your statement": "Billing disputes",
    "Account opening, closing, or management": "Managing an account",
}
FIELDS = ["text", "product", "issue", "complaint_id", "date_received"]


def clean_rows(rows: list[dict[str, str]], min_chars: int = 80) -> list[dict[str, str]]:
    """Remove missing labels and exact normalized duplicates before splitting."""
    seen: set[str] = set()
    cleaned: list[dict[str, str]] = []
    for row in rows:
        text = re.sub(r"\s+", " ", row.get("text", "")).strip()
        key = hashlib.sha256(text.casefold().encode()).hexdigest()
        if len(text) < min_chars or not row.get("product") or not row.get("issue") or key in seen:
            continue
        seen.add(key)
        cleaned.append({**row, "text": text})
    return cleaned


def split_rows(rows: list[dict[str, str]], seed: int = 42) -> dict[str, list[dict[str, str]]]:
    """Stratify by product/issue; test stays untouched by model fitting."""
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["product"], row["issue"]].append(row)
    splits: dict[str, list[dict[str, str]]] = {k: [] for k in ("training", "validation", "test")}
    rng = random.Random(seed)
    for key in sorted(grouped):
        group = list(grouped[key])
        rng.shuffle(group)
        train_end = int(len(group) * 0.7)
        val_end = train_end + int(len(group) * 0.15)
        splits["training"].extend(group[:train_end])
        splits["validation"].extend(group[train_end:val_end])
        splits["test"].extend(group[val_end:])
    return splits


def prepare_archive(archive: Path, output: Path, per_class: int = 110) -> dict[str, object]:
    """Extract supported narratives only; preserve upstream complaint IDs."""
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(archive) as zipped:
        filename = next(name for name in zipped.namelist() if name.lower().endswith(".csv"))
        with zipped.open(filename) as handle:
            for row in csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig")):
                product = PRODUCTS.get(row.get("Product", ""))
                if product:
                    rows.append(
                        {
                            "text": row.get("Consumer complaint narrative", ""),
                            "product": product,
                            "issue": ISSUE_ALIASES.get(row.get("Issue", ""), row.get("Issue", "")),
                            "complaint_id": row.get("Complaint ID", ""),
                            "date_received": row.get("Date received", ""),
                        }
                    )
    rows = clean_rows(rows)
    counts = Counter((r["product"], r["issue"]) for r in rows)
    # Choose three well represented issue labels per family, for nine joint classes.
    selected: set[tuple[str, str]] = set()
    for product in sorted(set(PRODUCTS.values())):
        selected.update(
            key
            for key, count in counts.most_common()
            if key[0] == product
            and count >= 30
            and len([x for x in selected if x[0] == product]) < 3
        )
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["product"], row["issue"])
        if key in selected:
            grouped[key].append(row)
    rng = random.Random(42)
    sampled: list[dict[str, str]] = []
    for key in sorted(grouped):
        rng.shuffle(grouped[key])
        sampled.extend(grouped[key][:per_class])
    splits = split_rows(sampled)
    output.mkdir(parents=True, exist_ok=True)
    for name, values in splits.items():
        with (output / f"{name}.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(values)
    manifest: dict[str, object] = {
        "source": "Official CFPB published narratives archive",
        "source_url": "https://files.consumerfinance.gov/f/documents/CCDB_Export_1_December_2011_through_April_2018.zip",
        "archive_page": "https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/",
        "retrieved_date": "2026-09-30",
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_csv": filename,
        "sample_size": len(sampled),
        "split_counts": {k: len(v) for k, v in splits.items()},
        "class_counts": [
            {
                "product": p,
                "issue": i,
                "count": sum(r["product"] == p and r["issue"] == i for r in sampled),
            }
            for p, i in sorted(selected)
        ],
        "seed": 42,
        "product_aliases": PRODUCTS,
        "issue_aliases": ISSUE_ALIASES,
        "deduplication": "Whitespace-normalized case-insensitive exact narrative hashes before split; near duplicates not detected",
        "sampling": "Up to 110 randomly selected rows per product/issue class; top three issues per product after filtering",
        "limitations": "Historical non-representative demonstration sample; no contemporary or deployment performance claim. Random stratified split; no temporal generalization claim.",
        "trained_slm": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    print(json.dumps(prepare_archive(args.archive, args.output), indent=2))
