"""Build the 10-class Qwen3 training data from the official CFPB complaint export.

Runs on the Mac (standard library + the repo's near-duplicate helper). Two
streaming passes over the ZIP, so the 5+ GB CSV is never extracted or held in RAM:

1. Count eligible narratives per (class, month) and choose a time-based split:
   the newest months are the test set, the months before them validation, and
   everything older is training.
2. Select rows deterministically (seed-42 hash of the complaint ID) with enough
   headroom for deduplication, then exact-deduplicate (test > validation > train),
   drop training rows that near-duplicate any evaluation row, and sample the
   per-class targets.

A separate held-out check set is built from the repo's existing reserved rows
(original 153-case test split and the scope-gate test halves); those IDs and
inputs are excluded from every other split.

Usage:
  .venv/bin/python pc_kit/mac_prep/prepare_dataset.py \
      --archive data/cfpb_raw/complaints_hfmirror_20260811.csv.zip --output pc_kit/data
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

KIT = Path(__file__).resolve().parents[1]
REPO = KIT.parent
sys.path.insert(0, str(KIT / "src"))
sys.path.insert(0, str(REPO))

from ckit_common import (  # noqa: E402
    CLASSES,
    OUT_OF_SCOPE,
    class_name,
    map_cfpb_label,
    normalized_input,
)
from scripts.near_duplicates import NearDuplicateIndex  # noqa: E402

FIELDS = ["text", "label", "product", "issue", "family", "complaint_id", "date_received", "source"]
OOS_CLASS = class_name(*OUT_OF_SCOPE)
SEED = 42
MIN_CHARS = 80


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def priority(complaint_id: str) -> float:
    """Deterministic pseudo-random value in [0, 1) per complaint."""
    return int(hashlib.sha256(f"{SEED}:{complaint_id}".encode()).hexdigest()[:15], 16) / 16**15


def input_hash(text: str) -> str:
    return hashlib.sha256(text.casefold().encode()).hexdigest()


def allocate(total: int, available: dict[str, int]) -> dict[str, int]:
    """Split `total` as evenly as possible across groups, capped by availability."""
    share = {key: 0 for key in available}
    remaining, open_keys = total, sorted(k for k, v in available.items() if v > 0)
    while remaining > 0 and open_keys:
        each = max(1, remaining // len(open_keys))
        for key in list(open_keys):
            take = min(each, available[key] - share[key], remaining)
            share[key] += take
            remaining -= take
            if share[key] >= available[key]:
                open_keys.remove(key)
            if remaining == 0:
                break
    return share


def stream_rows(archive: Path) -> Iterator[dict[str, Any]]:
    """Yield eligible, mapped rows with a usable narrative."""
    csv.field_size_limit(sys.maxsize)
    with zipfile.ZipFile(archive) as zipped:
        name = next(n for n in zipped.namelist() if n.lower().endswith(".csv"))
        with zipped.open(name) as handle:
            reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig", newline=""))
            if "Consumer complaint narrative" not in (reader.fieldnames or []):
                raise ValueError("This export has no complaint narratives; see README.")
            for raw in reader:
                narrative = raw.get("Consumer complaint narrative", "")
                if len(narrative) < MIN_CHARS:
                    continue
                complaint_id = raw.get("Complaint ID", "").strip()
                mapped = map_cfpb_label(
                    raw.get("Product", ""),
                    raw.get("Sub-product", ""),
                    raw.get("Issue", ""),
                    raw.get("Sub-issue", ""),
                )
                if not complaint_id or mapped is None:
                    continue
                text = normalized_input(narrative)
                if len(text) < MIN_CHARS:
                    continue
                product, issue, family = mapped
                yield {
                    "text": text,
                    "label": class_name(product, issue),
                    "product": product,
                    "issue": issue,
                    "family": family,
                    "complaint_id": complaint_id,
                    "date_received": raw.get("Date received", "")[:10],
                    "source": "cfpb",
                    "raw_product": raw.get("Product", ""),
                }


def choose_windows(
    counts: dict[tuple[str, str], int], months: list[str], need: dict[str, int], minimum: int
) -> tuple[list[str], list[str]]:
    """Walk back from the newest month until every class has `need` rows."""
    chosen: list[str] = []
    for month in reversed(months):
        chosen.append(month)
        if len(chosen) >= minimum and all(
            sum(counts.get((cls, m), 0) for m in chosen) >= need[cls] for cls in CLASSES
        ):
            return sorted(chosen), [m for m in months if m < min(chosen)]
    raise ValueError("Not enough data to fill the requested window.")


def load_check_set() -> list[dict[str, str]]:
    """Existing reserved rows from the repo, never used for training or selection."""
    rows: list[dict[str, str]] = []
    with (REPO / "data" / "test.csv").open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    "text": normalized_input(raw["text"]),
                    "label": class_name(raw["product"], raw["issue"]),
                    "product": raw["product"],
                    "issue": raw["issue"],
                    "family": "",
                    "complaint_id": raw["complaint_id"],
                    "date_received": raw["date_received"],
                    "source": "original_test_153",
                }
            )
    with (REPO / "data" / "scope" / "other_products.csv").open(encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            if raw["split"] == "test":
                rows.append(
                    {
                        "text": normalized_input(raw["text"]),
                        "label": OOS_CLASS,
                        "product": OUT_OF_SCOPE[0],
                        "issue": OUT_OF_SCOPE[1],
                        "family": raw["family"],
                        "complaint_id": raw["complaint_id"],
                        "date_received": "",
                        "source": "scope_other_products_test",
                    }
                )
    with (REPO / "data" / "scope" / "unrelated_authored.csv").open(encoding="utf-8") as handle:
        for index, raw in enumerate(csv.DictReader(handle)):
            if raw["split"] == "test":
                rows.append(
                    {
                        "text": normalized_input(raw["text"]),
                        "label": OOS_CLASS,
                        "product": OUT_OF_SCOPE[0],
                        "issue": OUT_OF_SCOPE[1],
                        "family": "unrelated_authored",
                        "complaint_id": f"authored-{index}",
                        "date_received": "",
                        "source": "scope_unrelated_authored_test",
                    }
                )
    return rows


def authored_training_rows(copies: int) -> list[dict[str, str]]:
    rows = []
    with (REPO / "data" / "scope" / "unrelated_authored.csv").open(encoding="utf-8") as handle:
        for index, raw in enumerate(csv.DictReader(handle)):
            if raw["split"] != "tune":
                continue
            for copy in range(copies):
                rows.append(
                    {
                        "text": normalized_input(raw["text"]),
                        "label": OOS_CLASS,
                        "product": OUT_OF_SCOPE[0],
                        "issue": OUT_OF_SCOPE[1],
                        "family": "unrelated_authored",
                        "complaint_id": f"authored-{index}-copy{copy}",
                        "date_received": "",
                        "source": "scope_unrelated_authored_tune",
                    }
                )
    return rows


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    output: Path = args.output
    if output.exists() and any(output.glob("*.csv")) and not args.overwrite:
        raise SystemExit(f"{output} already has CSVs; pass --overwrite to rebuild.")
    output.mkdir(parents=True, exist_ok=True)
    targets = {"train": args.train_per_class, "validation": args.val_per_class, "test": args.test_per_class}

    check = load_check_set()
    reserved_ids = {r["complaint_id"] for r in check}
    reserved_hashes = {input_hash(r["text"]) for r in check}

    # Pass 1: eligibility counts by class/month (and OOS family/month).
    counts: Counter[tuple[str, str]] = Counter()
    family_counts: Counter[tuple[str, str]] = Counter()
    scanned = 0
    for row in stream_rows(args.archive):
        scanned += 1
        month = row["date_received"][:7]
        counts[row["label"], month] += 1
        if row["family"]:
            family_counts[row["family"], month] += 1
    months = sorted({m for _, m in counts if m})
    print(f"pass 1: {scanned:,} eligible rows, {months[0]}..{months[-1]}", flush=True)

    headroom = args.headroom
    test_months, rest = choose_windows(
        counts, months, {c: int(targets["test"] * headroom) for c in CLASSES}, args.min_test_months
    )
    val_months, train_months = choose_windows(
        {k: v for k, v in counts.items() if k[1] in rest},
        rest,
        {c: int(targets["validation"] * headroom) for c in CLASSES},
        1,
    )
    split_of_month = {m: "test" for m in test_months} | {m: "validation" for m in val_months}
    split_of_month |= {m: "train" for m in train_months}

    def available(cls: str, split: str) -> int:
        return sum(v for (c, m), v in counts.items() if c == cls and split_of_month.get(m) == split)

    probability = {
        (cls, split): min(1.0, headroom * 1.5 * targets[split] / max(1, available(cls, split)))
        for cls in CLASSES
        for split in targets
    }

    # Pass 2: deterministic selection with headroom.
    selected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in stream_rows(args.archive):
        split = split_of_month.get(row["date_received"][:7])
        if split is None:
            continue
        row["priority"] = priority(row["complaint_id"])
        if row["priority"] < probability[row["label"], split]:
            row["split"] = split
            selected[split].append(row)
    print({k: len(v) for k, v in selected.items()}, flush=True)

    filters: Counter[str] = Counter()
    seen_ids, seen_hashes = set(reserved_ids), set(reserved_hashes)
    near = NearDuplicateIndex(threshold=args.near_threshold)
    for row in check:
        near.add(row["text"], f"check:{row['complaint_id']}")
    final: dict[str, list[dict[str, Any]]] = {}
    shortages: dict[str, Any] = {}
    for split in ("test", "validation", "train"):
        kept_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in sorted(selected[split], key=lambda r: r["priority"]):
            key = input_hash(row["text"])
            if row["complaint_id"] in seen_ids:
                filters[f"{split}_duplicate_or_reserved_id"] += 1
                continue
            if key in seen_hashes:
                filters[f"{split}_exact_duplicate_input"] += 1
                continue
            if near.find(row["text"]) is not None:
                filters[f"{split}_near_duplicate_of_evaluation_row"] += 1
                continue
            seen_ids.add(row["complaint_id"])
            seen_hashes.add(key)
            kept_by_class[row["label"]].append(row)
        rows: list[dict[str, Any]] = []
        for cls in CLASSES:
            pool = kept_by_class[cls]
            target = targets[split]
            if cls == OOS_CLASS:
                by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for row in pool:
                    by_family[row["family"]].append(row)
                share = allocate(target, {f: len(v) for f, v in by_family.items()})
                chosen = [r for f, v in by_family.items() for r in v[: share[f]]]
            else:
                chosen = pool[:target]
            if len(chosen) < target:
                shortages[f"{split}: {cls}"] = {"available": len(chosen), "target": target}
            rows.extend(chosen)
        if split != "train":
            # Evaluation rows enter the near-duplicate index; training rows are checked against it.
            for row in rows:
                near.add(row["text"], row["complaint_id"])
        final[split] = rows

    authored = authored_training_rows(args.authored_copies)
    final["train"].extend(authored)
    final["check"] = check
    rng = random.Random(SEED)
    for rows in final.values():
        rng.shuffle(rows)

    file_names = {"train": "train.csv", "validation": "validation.csv", "test": "test.csv", "check": "check.csv"}
    for split, rows in final.items():
        with (output / file_names[split]).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def summary(rows: list[dict[str, Any]]) -> dict[str, int]:
        return dict(sorted(Counter(r["label"] for r in rows).items()))

    manifest: dict[str, Any] = {
        "source": "Official CFPB Consumer Complaint Database export (complaints.csv.zip)",
        "source_url": "https://files.consumerfinance.gov/ccdb/complaints.csv.zip",
        "archived_copy": args.archived_url,
        "source_note": (
            "The live CFPB export no longer includes consumer narratives (checked 2026-10-08), "
            "so the official file as captured by the Internet Archive on 2026-08-15 is used."
        ),
        "archive_sha256": sha256_file(args.archive),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "classes": CLASSES,
        "eligible_rows_scanned": scanned,
        "data_months": [months[0], months[-1]],
        "split_policy": "time-based: newest months = test, preceding months = validation, older = train",
        "test_months": test_months,
        "validation_months": val_months,
        "train_months": [train_months[0], train_months[-1]] if train_months else [],
        "per_class_targets": targets,
        "split_counts": {k: len(v) for k, v in final.items()},
        "class_counts": {k: summary(v) for k, v in final.items()},
        "out_of_scope_family_counts": {
            k: dict(sorted(Counter(r["family"] for r in v if r["label"] == OOS_CLASS).items()))
            for k, v in final.items()
        },
        "shortages": shortages,
        "filters": dict(filters),
        "authored_unrelated_training_rows": len(authored),
        "check_set_sources": dict(Counter(r["source"] for r in check)),
        "input_policy": "Whitespace-normalized first 2,000 characters (identical to the app). Token truncation to max length happens in the training script.",
        "dedup_policy": "Exact (case-folded input hash) across all splits with priority test > validation > train; check-set IDs/inputs reserved; near-duplicates (shingle Jaccard >= %.2f) of check/test/validation rows removed from later splits." % args.near_threshold,
        "label_mapping": "See src/ckit_common.py map_cfpb_label: old (2011-2017) and new (2017+) CFPB issue names mapped onto the nine app classes; supported products with other issues are excluded; other CFPB products form the out-of-scope class.",
        "elapsed_seconds": round(time.time() - started),
    }
    manifest["output_sha256"] = {
        name: sha256_file(output / name) for name in file_names.values()
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=KIT / "data")
    parser.add_argument("--archived-url", default="https://web.archive.org/web/20260815141332/https://files.consumerfinance.gov/ccdb/complaints.csv.zip")
    parser.add_argument("--train-per-class", type=int, default=7000)
    parser.add_argument("--val-per-class", type=int, default=200)
    parser.add_argument("--test-per-class", type=int, default=300)
    parser.add_argument("--min-test-months", type=int, default=2)
    parser.add_argument("--headroom", type=float, default=1.5)
    parser.add_argument("--near-threshold", type=float, default=0.9)
    parser.add_argument("--authored-copies", type=int, default=3)
    parser.add_argument("--overwrite", action="store_true")
    manifest = prepare(parser.parse_args())
    print(json.dumps({k: manifest[k] for k in ("split_counts", "test_months", "validation_months", "train_months", "shortages", "filters")}, indent=2))


if __name__ == "__main__":
    main()
