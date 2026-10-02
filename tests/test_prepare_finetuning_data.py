"""Expanded dataset preserves held-out memberships and uses fixed labels."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import zipfile
from pathlib import Path

import pytest

from scripts.prepare_finetuning_data import FIXED_TAXONOMY, prepare_dataset


def narrative(key: str) -> str:
    rng = random.Random(key)
    return " ".join(f"term{rng.randrange(10000000)}" for _ in range(50))


def make_inputs(tmp_path: Path) -> tuple[Path, Path]:
    original = tmp_path / "original"
    original.mkdir()
    source_rows = []
    for split in ("training", "validation", "test"):
        rows = []
        for product, issues in FIXED_TAXONOMY.items():
            for issue in issues:
                key = f"{split}-{product}-{issue}"
                row = {
                    "text": narrative(key),
                    "product": product,
                    "issue": issue,
                    "complaint_id": key,
                    "date_received": "2017-01-01",
                }
                rows.append(row)
                source_rows.append(row)
        with (original / f"{split}.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    # A new ID repeats a held-out model input: it must never enter any new split.
    source_rows.append(
        {**source_rows[9], "complaint_id": "holdout-clone", "text": source_rows[9]["text"].upper()}
    )
    # Different prefix hash but >=95% word-shingle overlap with reserved holdout.
    source_rows.append(
        {
            **source_rows[9],
            "complaint_id": "holdout-near-clone",
            "text": source_rows[9]["text"] + ". extra",
        }
    )
    source_rows.append(
        {
            "text": narrative("prepaid-only"),
            "product": "Credit card or prepaid card",
            "issue": "Other",
            "complaint_id": "prepaid-card",
            "date_received": "2017-01-01",
            "sub_product": "General-purpose prepaid card",
        }
    )
    for product, issues in FIXED_TAXONOMY.items():
        for issue in issues:
            for index in range(8):
                key = f"new-{product}-{issue}-{index}"
                source_rows.append(
                    {
                        "text": narrative(key),
                        "product": product,
                        "issue": issue,
                        "complaint_id": key,
                        "date_received": "2017-01-01",
                    }
                )
    # A frequent unsupported issue cannot replace the fixed taxonomy.
    source_rows.append(
        {
            **source_rows[0],
            "issue": "Unsupported issue",
            "complaint_id": "unsupported",
            "text": narrative("unsupported"),
        }
    )
    stream = io.StringIO()
    fields = [
        "Product",
        "Issue",
        "Consumer complaint narrative",
        "Complaint ID",
        "Date received",
        "Sub-product",
    ]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in source_rows:
        writer.writerow(
            {
                "Product": row["product"],
                "Issue": row["issue"],
                "Consumer complaint narrative": row["text"],
                "Complaint ID": row["complaint_id"],
                "Date received": row["date_received"],
                "Sub-product": row.get("sub_product", "Credit card"),
            }
        )
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("complaints.csv", stream.getvalue())
    return archive, original


def test_expansion_preserves_allocations_and_excludes_heldout_inputs(tmp_path: Path) -> None:
    archive, original = make_inputs(tmp_path)
    output = tmp_path / "finetuning"
    before = {p.name: p.read_bytes() for p in original.glob("*.csv")}
    manifest = prepare_dataset(
        archive, output, original, train_per_class=3, validation_per_class=2, test_per_class=2
    )
    assert manifest["split_counts"] == {"training": 27, "validation": 18, "test": 18}
    assert manifest["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    ids, hashes = set(), set()
    for split in ("training", "validation", "test"):
        rows = list(csv.DictReader((output / f"{split}.csv").open()))
        originals = list(csv.DictReader((original / f"{split}.csv").open()))
        by_id = {row["complaint_id"]: row for row in rows}
        for row in originals:
            assert by_id[row["complaint_id"]]["text"] == row["text"]
        assert {"holdout-clone", "unsupported", "holdout-near-clone", "prepaid-card"}.isdisjoint(
            by_id
        )
        for row in rows:
            assert row["complaint_id"] not in ids
            assert row["input_sha256"] not in hashes
            ids.add(row["complaint_id"])
            hashes.add(row["input_sha256"])
        messages = [
            json.loads(line)["messages"]
            for line in (output / f"{split}.jsonl").read_text().splitlines()
        ]
        assert len(messages) == len(rows)
        for row, message in zip(rows, messages):
            assert json.loads(message[1]["content"])["complaint"] == row["input_text"]
            assert json.loads(message[2]["content"]) == {
                "product": row["product"],
                "issue": row["issue"],
            }
    assert before == {p.name: p.read_bytes() for p in original.glob("*.csv")}
    assert manifest["overlap_checks"]["cross_split_input_hashes"] == 0
    assert manifest["filters"]["reserved_input_duplicate"] >= 1
    assert manifest["filters"]["near_duplicate_input"] >= 1
    assert manifest["filters"]["prepaid_subtype"] >= 1


def test_shortage_fails_before_output_and_reports_class(tmp_path: Path) -> None:
    archive, original = make_inputs(tmp_path)
    output = tmp_path / "finetuning"
    with pytest.raises(ValueError, match="Insufficient unique rows"):
        prepare_dataset(
            archive, output, original, train_per_class=100, validation_per_class=2, test_per_class=2
        )
    assert not output.exists()


def test_never_overwrite_original_directory(tmp_path: Path) -> None:
    archive, original = make_inputs(tmp_path)
    with pytest.raises(ValueError, match="separate"):
        prepare_dataset(archive, original, original)


def test_seeded_outputs_are_reproducible_and_existing_outputs_are_protected(tmp_path: Path) -> None:
    archive, original = make_inputs(tmp_path)
    first, second = tmp_path / "first", tmp_path / "second"
    kwargs = {"train_per_class": 3, "validation_per_class": 2, "test_per_class": 2}
    left = prepare_dataset(archive, first, original, **kwargs)
    right = prepare_dataset(archive, second, original, **kwargs)
    assert left["output_sha256"] == right["output_sha256"]
    assert left["token_budget_verified"] is False
    assert left["selected_date_ranges"]["training"] == {
        "minimum": "2017-01-01",
        "maximum": "2017-01-01",
    }
    before = (first / "training.csv").read_bytes()
    with pytest.raises(ValueError, match="never overwrite"):
        prepare_dataset(archive, first, original, **kwargs)
    assert (first / "training.csv").read_bytes() == before


def test_inconsistent_original_holdouts_fail_without_output(tmp_path: Path) -> None:
    archive, original = make_inputs(tmp_path)
    # An original validation ID is moved into training: never silently fix splits.
    train = list(csv.DictReader((original / "training.csv").open()))
    validation = list(csv.DictReader((original / "validation.csv").open()))
    train[0]["complaint_id"] = validation[0]["complaint_id"]
    with (original / "training.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(train[0]))
        writer.writeheader()
        writer.writerows(train)
    with pytest.raises(ValueError, match="overlapping IDs"):
        prepare_dataset(archive, tmp_path / "invalid", original)
    assert not (tmp_path / "invalid").exists()
