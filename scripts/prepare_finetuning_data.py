"""Expand fixed CFPB classes while preserving original split memberships.

No download or model training occurs. Reads the official historical ZIP in a
stream, keeps bounded candidate pools, and writes a separate fine-tuning dataset.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import io
import json
import random
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_local import messages_for  # noqa: E402
from scripts.prepare_data import ISSUE_ALIASES, PRODUCTS  # noqa: E402

FIXED_TAXONOMY = {
    "Checking or savings account": [
        "Deposits and withdrawals",
        "Managing an account",
        "Problems caused by my funds being low",
    ],
    "Credit card": ["Billing disputes", "Fees or interest", "Other"],
    "Credit reporting": [
        "Improper use of your report",
        "Incorrect information on your report",
        "Problem with a credit reporting company's investigation into an existing problem",
    ],
}
SOURCE_URL = "https://files.consumerfinance.gov/f/documents/CCDB_Export_1_December_2011_through_April_2018.zip"
SPLITS = ("training", "validation", "test")
CSV_FIELDS = [
    "text",
    "input_text",
    "product",
    "issue",
    "complaint_id",
    "date_received",
    "input_sha256",
    "original_split",
]
INPUT_LIMIT = 2000


def normalized_input(text: str) -> str:
    """Match the existing whitespace normalization and fixed inference excerpt."""
    return re.sub(r"\s+", " ", text).strip()[:INPUT_LIMIT]


def sha256_file(path: Path) -> str:
    """Hash archives in chunks without loading their complete bytes into RAM."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(raw: dict[str, str], original_split: str = "") -> dict[str, str]:
    prefix = normalized_input(raw["text"])
    return {
        **raw,
        "input_text": prefix,
        "input_sha256": hashlib.sha256(prefix.casefold().encode()).hexdigest(),
        "original_split": original_split,
    }


def prepare_dataset(
    archive: Path,
    output: Path,
    original_data: Path = ROOT / "data",
    *,
    train_per_class: int = 1000,
    validation_per_class: int = 100,
    test_per_class: int = 100,
    retrieved_date: str = "2026-10-03",
) -> dict[str, Any]:
    """Preserve reserved rows, exclude duplicate/near inputs and fail shortages."""
    from scripts.near_duplicates import NearDuplicateIndex

    output, original_data = output.resolve(), original_data.resolve()
    if output == original_data or original_data.is_relative_to(output):
        raise ValueError("Fine-tuning output must be separate from original data")
    if output.exists() and any(output.iterdir()):
        raise ValueError(
            "Output must be an empty separate directory; never overwrite an existing dataset"
        )
    targets = {
        "training": train_per_class,
        "validation": validation_per_class,
        "test": test_per_class,
    }
    if any(value < 1 for value in targets.values()):
        raise ValueError("Per-class targets must be positive")
    pairs = {(product, issue) for product, issues in FIXED_TAXONOMY.items() for issue in issues}
    originals: dict[str, list[dict[str, str]]] = {}
    original_counts: dict[str, Counter[tuple[str, str]]] = {}
    reserved_ids: set[str] = set()
    reserved_hashes: set[str] = set()
    reserved_split_by_id: dict[str, str] = {}
    near_index = NearDuplicateIndex()
    reserved_near_pairs: list[dict[str, str]] = []
    for split in SPLITS:
        with (original_data / f"{split}.csv").open(encoding="utf-8", newline="") as handle:
            originals[split] = [record(dict(row), split) for row in csv.DictReader(handle)]
        original_counts[split] = Counter((r["product"], r["issue"]) for r in originals[split])
        if set(original_counts[split]) != pairs:
            raise ValueError(f"Original {split} must contain exactly the fixed nine label pairs")
        for row in originals[split]:
            if original_counts[split][row["product"], row["issue"]] > targets[split]:
                raise ValueError(
                    f"Target {split} is smaller than its preserved original class allocation"
                )
            if row["complaint_id"] in reserved_ids or row["input_sha256"] in reserved_hashes:
                raise ValueError(
                    "Original splits already contain overlapping IDs or normalized input prefixes"
                )
            match = near_index.find(row["input_text"])
            if match is not None:
                reserved_near_pairs.append(
                    {
                        "complaint_id": row["complaint_id"],
                        "near_original_id": match,
                        "split": split,
                        "near_original_split": reserved_split_by_id[match],
                    }
                )
            near_index.add(row["input_text"], row["complaint_id"])
            reserved_split_by_id[row["complaint_id"]] = split
            reserved_ids.add(row["complaint_id"])
            reserved_hashes.add(row["input_sha256"])
    needed = {
        pair: sum(targets[split] - original_counts[split][pair] for split in SPLITS)
        for pair in pairs
    }
    heaps: dict[tuple[str, str], list[tuple[int, str, dict[str, str]]]] = defaultdict(list)
    pool_limits = {pair: max(64, needed[pair] * 2) for pair in pairs}
    source_unique_counts: Counter[tuple[str, str]] = Counter()
    seen_ids = set(reserved_ids)
    seen_hashes = set(reserved_hashes)
    filters: Counter[str] = Counter()
    scanned = 0
    with zipfile.ZipFile(archive) as zipped:
        filename = next((name for name in zipped.namelist() if name.lower().endswith(".csv")), None)
        if filename is None:
            raise ValueError("Archive contains no CSV")
        with zipped.open(filename) as source:
            for raw in csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig")):
                scanned += 1
                product = PRODUCTS.get(raw.get("Product", ""))
                issue = ISSUE_ALIASES.get(raw.get("Issue", ""), raw.get("Issue", ""))
                pair = (product or "", issue)
                if pair not in pairs:
                    filters["unsupported_pair"] += 1
                    continue
                source_id = raw.get("Complaint ID", "").strip()
                if source_id in reserved_ids:
                    filters["reserved_id"] += 1
                    continue
                subtype = raw.get("Sub-product", "").casefold()
                if raw.get("Product") == "Credit card or prepaid card" and (
                    "prepaid" in subtype or "gift" in subtype
                ):
                    filters["prepaid_subtype"] += 1
                    continue
                text = re.sub(r"\s+", " ", raw.get("Consumer complaint narrative", "")).strip()
                if not source_id or len(text) < 80:
                    filters["missing_id_or_short_text"] += 1
                    continue
                candidate = record(
                    {
                        "text": text,
                        "product": product or "",
                        "issue": issue,
                        "complaint_id": source_id,
                        "date_received": raw.get("Date received", ""),
                    }
                )
                if source_id in seen_ids:
                    filters["duplicate_id"] += 1
                    continue
                if candidate["input_sha256"] in seen_hashes:
                    filters[
                        "reserved_input_duplicate"
                        if candidate["input_sha256"] in reserved_hashes
                        else "new_input_duplicate"
                    ] += 1
                    continue
                seen_ids.add(source_id)
                seen_hashes.add(candidate["input_sha256"])
                source_unique_counts[pair] += 1
                priority = int(
                    hashlib.sha256(("42:" + candidate["input_sha256"]).encode()).hexdigest(), 16
                )
                entry = (-priority, source_id, candidate)
                if len(heaps[pair]) < pool_limits[pair]:
                    heapq.heappush(heaps[pair], entry)
                elif priority < -heaps[pair][0][0]:
                    heapq.heapreplace(heaps[pair], entry)
    # Near detection indexes only reserved rows and admitted bounded candidates.
    pools: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for pair in sorted(pairs):
        for _, source_id, candidate in sorted(heaps[pair], key=lambda item: (-item[0], item[1])):
            if near_index.find(candidate["input_text"]) is not None:
                filters["near_duplicate_input"] += 1
                continue
            if len(pools[pair]) >= needed[pair]:
                continue
            pools[pair].append(candidate)
            near_index.add(candidate["input_text"], source_id)
    shortages = {
        f"{p} / {i}": {"available_new": len(pools[p, i]), "required_new": needed[p, i]}
        for p, i in sorted(pairs)
        if len(pools[p, i]) < needed[p, i]
    }
    if shortages:
        raise ValueError(
            "Insufficient unique rows after preserving splits and duplicate filtering: "
            + json.dumps(shortages)
        )
    rng = random.Random(42)
    splits = {split: list(originals[split]) for split in SPLITS}
    for pair in sorted(pairs):
        selected = list(pools[pair])
        rng.shuffle(selected)
        offset = 0
        for split in SPLITS:
            count = targets[split] - original_counts[split][pair]
            splits[split].extend(selected[offset : offset + count])
            offset += count
    for values in splits.values():
        rng.shuffle(values)
    id_sets = {name: {r["complaint_id"] for r in values} for name, values in splits.items()}
    hash_sets = {name: {r["input_sha256"] for r in values} for name, values in splits.items()}
    id_overlap = sum(
        len(id_sets[a] & id_sets[b])
        for a, b in [("training", "validation"), ("training", "test"), ("validation", "test")]
    )
    hash_overlap = sum(
        len(hash_sets[a] & hash_sets[b])
        for a, b in [("training", "validation"), ("training", "test"), ("validation", "test")]
    )
    original_holdout_ids = {
        r["complaint_id"] for split in ("validation", "test") for r in originals[split]
    }
    original_holdout_hashes = {
        r["input_sha256"] for split in ("validation", "test") for r in originals[split]
    }
    assert id_overlap == hash_overlap == 0
    assert not original_holdout_ids & id_sets["training"]
    assert not original_holdout_hashes & hash_sets["training"]
    manifest: dict[str, Any] = {
        "source": "Official CFPB historical published narrative archive, December 2011–April 2018",
        "source_url": SOURCE_URL,
        "retrieved_date": retrieved_date,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": sha256_file(archive),
        "archive_csv": filename,
        "source_rows_scanned": scanned,
        "taxonomy": FIXED_TAXONOMY,
        "taxonomy_policy": "Fixed original nine pairs; never reselect top issues",
        "product_aliases": PRODUCTS,
        "issue_aliases": ISSUE_ALIASES,
        "seed": 42,
        "sampling": "Scan complete source, reserve IDs/prefixes, globally exact-deduplicate eligible inputs, retain lowest seed42 input-hash priorities in bounded 2x-needed per-class pools, conservatively filter near duplicates, then shuffle class/split allocations with seed42. Labels in identical source inputs use first occurrence; not temporal splitting.",
        "candidate_pool_limits": {f"{p} / {i}": pool_limits[p, i] for p, i in sorted(pairs)},
        "source_unique_counts": {
            f"{p} / {i}": source_unique_counts[p, i] for p, i in sorted(pairs)
        },
        "candidate_pool_counts": {f"{p} / {i}": len(heaps[p, i]) for p, i in sorted(pairs)},
        "per_class_targets": targets,
        "split_counts": {k: len(v) for k, v in splits.items()},
        "class_counts": {
            split: [
                {
                    "product": p,
                    "issue": i,
                    "count": sum((r["product"], r["issue"]) == (p, i) for r in values),
                }
                for p, i in sorted(pairs)
            ]
            for split, values in splits.items()
        },
        "original_preserved_counts": {k: len(v) for k, v in originals.items()},
        "original_file_sha256": {
            name: sha256_file(original_data / f"{name}.csv") for name in SPLITS
        },
        "input_policy": "text preserves full normalized source narrative and original text; input_text is whitespace-normalized first2000 characters; JSONL uses input_text and benchmark messages_for prompt",
        "input_character_limit": INPUT_LIMIT,
        "input_hash_policy": "SHA256 of case-folded normalized input_text",
        "truncated_counts": {
            k: sum(len(r["text"]) > len(r["input_text"]) for r in v) for k, v in splits.items()
        },
        "filters": dict(filters),
        "preserved_original_near_duplicate_pairs": reserved_near_pairs,
        "preserved_original_cross_split_near_matches": sum(
            r["split"] != r["near_original_split"] for r in reserved_near_pairs
        ),
        "selected_date_ranges": {
            split: {
                "minimum": min(r["date_received"] for r in values),
                "maximum": max(r["date_received"] for r in values),
            }
            for split, values in splits.items()
        },
        "token_budget_verified": False,
        "token_budget_note": "Character clipping is not a token guarantee; selected model tokenizer must verify complete messages fit training context before GPU training.",
        "near_duplicate_policy": "Conservative bounded lexical shingle candidate matching; see scripts/near_duplicates.py. Reject new near-duplicates against all reserved and accepted input prefixes; original allocations remain unchanged.",
        "overlap_checks": {
            "cross_split_ids": id_overlap,
            "cross_split_input_hashes": hash_overlap,
            "original_holdout_ids_in_training": 0,
            "original_holdout_prefixes_in_training": 0,
        },
        "trained_slm": False,
        "limitations": "Historical balanced training sample. Prefix truncation can omit evidence; conservative approximate near-duplicate blocking may miss paraphrases/templates. Existing original near-duplicate pairs are retained and disclosed to preserve prior splits. More rows do not guarantee fine-tuned accuracy.",
    }
    output.mkdir(parents=True, exist_ok=True)
    for split, values in splits.items():
        with (output / f"{split}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(values)
        with (output / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
            for row in values:
                messages = messages_for(row["input_text"], FIXED_TAXONOMY)
                messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps({"product": row["product"], "issue": row["issue"]}),
                    }
                )
                handle.write(json.dumps({"messages": messages}, ensure_ascii=False) + "\n")
    manifest["output_sha256"] = {p.name: sha256_file(p) for p in output.iterdir() if p.is_file()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "finetuning")
    parser.add_argument("--original-data", type=Path, default=ROOT / "data")
    parser.add_argument("--train-per-class", type=int, default=1000)
    parser.add_argument("--validation-per-class", type=int, default=100)
    parser.add_argument("--test-per-class", type=int, default=100)
    parser.add_argument("--retrieved-date", default="2026-10-03")
    args = parser.parse_args()
    manifest = prepare_dataset(
        args.archive,
        args.output,
        args.original_data,
        train_per_class=args.train_per_class,
        validation_per_class=args.validation_per_class,
        test_per_class=args.test_per_class,
        retrieved_date=args.retrieved_date,
    )
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in ["split_counts", "original_preserved_counts", "overlap_checks", "filters"]
            },
            indent=2,
        )
    )
