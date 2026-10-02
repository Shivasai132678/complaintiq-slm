"""Evaluate the actual baseline or optional local GGUF on untouched held-out rows."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def metric_report(actual: list[str], predicted: list[str]) -> dict[str, Any]:
    """Compute accuracy and macro metrics, retaining per-class support."""
    precision, recall, f1, _ = precision_recall_fscore_support(
        actual, predicted, labels=sorted(set(actual)), average="macro", zero_division=0
    )
    labels = sorted(set(actual) | set(predicted))
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "precision_macro": float(precision),
        "recall_macro": float(recall),
        "f1_macro": float(f1),
        "labels": labels,
        "macro_convention": "Macro averaged over ground-truth labels; abstentions reduce recall. Confusion matrix includes abstentions.",
        "per_class": classification_report(
            actual, predicted, labels=sorted(set(actual)), output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(actual, predicted, labels=labels).tolist(),
    }


def evaluate(training: Path, test: Path, model_path: str | None = None) -> dict[str, Any]:
    from complaintiq.models import BaselineClassifier, LocalSLMClassifier

    baseline = BaselineClassifier(training)
    classifier = LocalSLMClassifier(model_path, baseline.taxonomy) if model_path else baseline
    with test.open() as handle:
        rows = list(csv.DictReader(handle))
    predictions: list[dict[str, Any]] = []
    elapsed: list[float] = []
    for row in rows:
        started = time.perf_counter()
        try:
            predictions.append(classifier.classify(row["text"]))
        except (ValueError, RuntimeError) as error:
            predictions.append({"product": "Unknown", "issue": "Needs review", "error": str(error)})
        elapsed.append(time.perf_counter() - started)
    report = {
        "model": classifier.model_version,
        "backend": classifier.backend,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "test_size": len(rows),
        "data_manifest": "data/manifest.json",
        "status": "measured",
        "product": metric_report([r["product"] for r in rows], [p["product"] for p in predictions]),
        "issue": metric_report([r["issue"] for r in rows], [p["issue"] for p in predictions]),
        "joint_accuracy": sum(
            r["product"] == p["product"] and r["issue"] == p["issue"]
            for r, p in zip(rows, predictions)
        )
        / len(rows),
        "latency_ms_mean": sum(elapsed) * 1000 / len(elapsed),
        "review_rate": sum(p["product"] == "Unknown" for p in predictions) / len(rows),
        "input_tokens": sum(p.get("tokens_input", 0) for p in predictions),
        "output_tokens": sum(p.get("tokens_output", 0) for p in predictions),
        "errors": sum("error" in p for p in predictions),
        "limitations": "Small historical balanced sample; normalized exact duplicates removed, near-duplicate/template leakage remains possible. No performance claim on current workloads.",
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, default=Path("data/training.csv"))
    parser.add_argument("--test", type=Path, default=Path("data/test.csv"))
    parser.add_argument(
        "--model-path", default=None, help="Optional GGUF; no automatic model download"
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    args = parser.parse_args()
    report = evaluate(args.training, args.test, args.model_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("model", "test_size", "joint_accuracy", "latency_ms_mean")
            },
            indent=2,
        )
    )
