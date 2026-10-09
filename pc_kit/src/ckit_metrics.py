"""Classification metrics and markdown summary (standard library only)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ckit_common import CLASSES, OUT_OF_SCOPE, class_name

OOS_CLASS = class_name(*OUT_OF_SCOPE)


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def classification_report(gold: list[str], predicted: list[str]) -> dict[str, Any]:
    """Accuracy, macro/weighted precision-recall-F1, per-class scores and confusion matrix.

    Predictions outside CLASSES (e.g. 'invalid') count as errors for every class.
    """
    if len(gold) != len(predicted) or not gold:
        raise ValueError("gold and predicted must be non-empty and the same length")
    labels = [c for c in CLASSES if c in set(gold) | set(predicted)]
    per_class: dict[str, dict[str, float]] = {}
    for label in labels:
        tp = sum(g == p == label for g, p in zip(gold, predicted))
        fp = sum(p == label and g != label for g, p in zip(gold, predicted))
        fn = sum(g == label and p != label for g, p in zip(gold, predicted))
        precision, recall, f1 = _prf(tp, fp, fn)
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(g == label for g in gold),
        }
    present = [label for label in labels if per_class[label]["support"] > 0]
    total = len(gold)
    product = lambda name: name.split(" / ")[0]  # noqa: E731
    in_scope = [(g, p) for g, p in zip(gold, predicted) if g != OOS_CLASS]
    oos_tp = sum(g == p == OOS_CLASS for g, p in zip(gold, predicted))
    oos_fp = sum(p == OOS_CLASS and g != OOS_CLASS for g, p in zip(gold, predicted))
    oos_fn = sum(g == OOS_CLASS and p != OOS_CLASS for g, p in zip(gold, predicted))
    oos_p, oos_r, oos_f = _prf(oos_tp, oos_fp, oos_fn)
    confusion = {
        g_label: dict(Counter(p for g, p in zip(gold, predicted) if g == g_label))
        for g_label in present
    }
    return {
        "n": total,
        "accuracy": round(sum(g == p for g, p in zip(gold, predicted)) / total, 4),
        "macro_precision": round(sum(per_class[c]["precision"] for c in present) / len(present), 4),
        "macro_recall": round(sum(per_class[c]["recall"] for c in present) / len(present), 4),
        "macro_f1": round(sum(per_class[c]["f1"] for c in present) / len(present), 4),
        "weighted_f1": round(
            sum(per_class[c]["f1"] * per_class[c]["support"] for c in present) / total, 4
        ),
        "product_accuracy": round(
            sum(product(g) == product(p) for g, p in zip(gold, predicted)) / total, 4
        ),
        "in_scope_joint_accuracy": (
            round(sum(g == p for g, p in in_scope) / len(in_scope), 4) if in_scope else None
        ),
        "in_scope_n": len(in_scope),
        "out_of_scope": {
            "precision": round(oos_p, 4),
            "recall": round(oos_r, 4),
            "f1": round(oos_f, 4),
            "support": oos_tp + oos_fn,
        },
        "invalid_predictions": sum(p not in CLASSES for p in predicted),
        "per_class": per_class,
        "confusion": confusion,
    }


def report_by_source(rows: list[dict[str, str]], predicted: list[str]) -> dict[str, Any]:
    """Overall report plus one per data source (check set mixes several sources)."""
    gold = [r["label"] for r in rows]
    result: dict[str, Any] = {"overall": classification_report(gold, predicted)}
    sources = sorted({r.get("source", "") for r in rows})
    if len(sources) > 1:
        for source in sources:
            idx = [i for i, r in enumerate(rows) if r.get("source", "") == source]
            result[source] = classification_report([gold[i] for i in idx], [predicted[i] for i in idx])
    return result


SUMMARY_KEYS = [
    ("accuracy", "10-class accuracy"),
    ("macro_f1", "Macro F1"),
    ("macro_precision", "Macro precision"),
    ("macro_recall", "Macro recall"),
    ("weighted_f1", "Weighted F1"),
    ("product_accuracy", "Product accuracy"),
    ("in_scope_joint_accuracy", "In-scope joint (product+issue) accuracy"),
]


def summary_markdown(report: dict[str, Any], title: str) -> str:
    """report: report_by_source() output. Overall table, per-source accuracy, per-class F1."""
    overall = report["overall"]
    lines = [f"### {title}", "", "| Metric | Value |", "|---|---|"]
    for key, label in SUMMARY_KEYS:
        value = overall.get(key)
        lines.append(f"| {label} | {'-' if value is None else f'{value:.2%}'} |")
    for key in ("precision", "recall"):
        lines.append(f"| Out-of-scope {key} | {overall['out_of_scope'][key]:.2%} |")
    lines.append(f"| Invalid replies | {overall['invalid_predictions']} |")
    for source, sub in report.items():
        if source != "overall":
            lines.append(f"| Accuracy on {source} (n={sub['n']}) | {sub['accuracy']:.2%} |")
    lines += ["", "| Class | Precision | Recall | F1 | Support |", "|---|---|---|---|---|"]
    for name, scores in overall["per_class"].items():
        lines.append(f"| {name} | {scores['precision']:.2%} | {scores['recall']:.2%} | {scores['f1']:.2%} | {scores['support']} |")
    return "\n".join(lines) + "\n"


def load_predictions(path: Path) -> dict[str, str]:
    """complaint_id -> predicted class from a saved predictions file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {p["complaint_id"]: p["predicted"] for p in data["predictions"]}
