"""Evaluate the frozen local SLM on a reserved test split.

Default: the original 153-case split. Use ``--test-file data/finetuning/test.csv`` for all 900 cases.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

from complaintiq.models import BaselineClassifier
from complaintiq.server_model import ServerSLMClassifier
from scripts.evaluate import metric_report

ROOT = Path(__file__).resolve().parents[1]


def evaluate(model_path: str, server_url: str, output: Path, test_path: Path | None = None) -> dict:
    taxonomy = BaselineClassifier().taxonomy
    model = ServerSLMClassifier(model_path, taxonomy, server_url)
    test_path = test_path or ROOT / "data" / "test.csv"
    with test_path.open() as handle:
        rows = list(csv.DictReader(handle))
    with Path(model_path).open("rb") as handle:
        model_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    report: dict[str, Any] = {
        "model": model.model_version,
        "backend": "slm",
        "fine_tuned": True,
        "status": "in_progress",
        "test_size": len(rows),
        "test_file_sha256": hashlib.sha256(test_path.read_bytes()).hexdigest(),
        "model_file_sha256": model_hash,
        "limitations": [
            (
                "153 reserved CFPB test cases preserved within the expanded 900-case test split; the other 747 test cases were not evaluated."
                if len(rows) == 153
                else f"{len(rows)} reserved CFPB test cases from {test_path.name}."
            ),
            "Three product classes and nine allowed product/issue pairs; results do not cover other financial products.",
            "Strict schema decoding enforces valid label pairs; validity alone does not establish accuracy.",
            "Only the first 2,000 normalized characters are used. Priority, routing and summary are separate rules/extractive methods.",
            "Training provenance is based on the supplied Unsloth export; local testing does not independently verify the cloud training configuration.",
        ],
        "predictions": [],
    }
    try:
        for row in rows:
            start = time.perf_counter()
            result = model.classify(row["text"])
            report["predictions"].append(
                {
                    "complaint_id": row["complaint_id"],
                    "actual_product": row["product"],
                    "actual_issue": row["issue"],
                    **result,
                    "latency_ms": (time.perf_counter() - start) * 1000,
                }
            )
            output.write_text(json.dumps(report, indent=2) + "\n")
            if len(report["predictions"]) % 25 == 0:
                print(f"Evaluated {len(report['predictions'])}/{len(rows)}", flush=True)
    except Exception:
        report["status"] = "failed"
        output.write_text(json.dumps(report, indent=2) + "\n")
        raise
    predictions = report["predictions"]
    for key in ("product", "issue"):
        report[key] = metric_report(
            [r[f"actual_{key}"] for r in predictions], [r[key] for r in predictions]
        )
    report.update(
        status="measured",
        joint_accuracy=sum(
            r["product"] == r["actual_product"] and r["issue"] == r["actual_issue"]
            for r in predictions
        )
        / len(rows),
        latency_ms_mean=sum(r["latency_ms"] for r in predictions) / len(rows),
        latency_ms_median=statistics.median(r["latency_ms"] for r in predictions),
        latency_ms_p95=sorted(r["latency_ms"] for r in predictions)[
            max(0, int(0.95 * len(predictions)) - 1)
        ],
        review_rate=sum(r["product"] == "Unknown" for r in predictions) / len(rows),
    )
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in ("test_size", "joint_accuracy", "latency_ms_mean", "latency_ms_p95")
            }
        ),
        flush=True,
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-path", default=str(ROOT / "models/Qwen2.5-1.5B-Instruct.Q4_K_M.gguf")
    )
    parser.add_argument("--server-url", default="http://127.0.0.1:8504")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/finetuned_evaluation.json")
    parser.add_argument(
        "--test-file",
        type=Path,
        default=ROOT / "data/test.csv",
        help="data/finetuning/test.csv evaluates all 900 reserved cases",
    )
    args = parser.parse_args()
    evaluate(args.model_path, args.server_url, args.output, args.test_file)
