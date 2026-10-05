"""Measure the scope gate on held-out supported and unsupported complaints."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from complaintiq.scope import ANCHOR_OVERRIDE, METHOD, THRESHOLD, ScopeGate

ROOT = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate(output: Path) -> dict:
    gate = ScopeGate()
    rate = lambda texts: sum(not gate.check(t)["in_scope"] for t in texts) / len(texts)  # noqa: E731
    supported_val = [r["text"] for r in rows(ROOT / "data/finetuning/validation.csv")]
    supported_test = [r["text"] for r in rows(ROOT / "data/finetuning/test.csv")]
    other = [r for r in rows(ROOT / "data/scope/other_products.csv") if r["split"] == "test"]
    unrelated = rows(ROOT / "data/scope/unrelated_authored.csv")
    families: dict[str, list[str]] = defaultdict(list)
    for r in other:
        families[r["family"]].append(r["text"])
    report: dict = {
        "method": METHOD,
        "threshold": THRESHOLD,
        "anchor_override": ANCHOR_OVERRIDE,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "supported_sent_to_review": {
            "validation_900_used_for_threshold": round(rate(supported_val), 4),
            "test_900": round(rate(supported_test), 4),
        },
        "other_cfpb_products_caught": {
            "all_test": round(rate([r["text"] for r in other]), 4),
            "test_size": len(other),
            "by_family": {k: round(rate(v), 4) for k, v in sorted(families.items())},
        },
        "unrelated_authored_caught": {
            "test": round(rate([r["text"] for r in unrelated if r["split"] == "test"]), 4),
            "tune": round(rate([r["text"] for r in unrelated if r["split"] == "tune"]), 4),
            "test_size": sum(r["split"] == "test" for r in unrelated),
        },
    }
    slm = ROOT / "artifacts/finetuned_evaluation.json"
    if slm.is_file():
        texts = {r["complaint_id"]: r["text"] for r in rows(ROOT / "data/test.csv")}
        preds = json.loads(slm.read_text())["predictions"]
        gated = [not gate.check(texts[p["complaint_id"]])["in_scope"] for p in preds]
        joint = [
            not g and p["product"] == p["actual_product"] and p["issue"] == p["actual_issue"]
            for p, g in zip(preds, gated)
        ]
        product = [not g and p["product"] == p["actual_product"] for p, g in zip(preds, gated)]
        report["fine_tuned_153_with_gate"] = {
            "sent_to_review": sum(gated),
            "product_accuracy": round(sum(product) / len(preds), 4),
            "joint_accuracy": round(sum(joint) / len(preds), 4),
            "note": "Gated cases count as errors here; in the app they go to human review.",
        }
    report["limitations"] = [
        "Unrelated examples are a small authored challenge set (108 texts), not a real traffic sample.",
        "Other-product complaints come from the same 2011-2018 CFPB archive as the training data.",
        "Debt collection complaints often discuss credit reports, so many still pass the gate.",
        "Supported complaints that are sent to review are not lost; a reviewer classifies them.",
    ]
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(evaluate(ROOT / "artifacts/scope_evaluation.json"), indent=2))
