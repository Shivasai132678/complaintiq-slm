"""Scope gate: keep complaints outside the trained taxonomy away from the classifier.

The fine-tuned model only ever saw credit card, credit reporting and checking/savings
complaints, so it always answers with one of those labels. This gate runs first and
routes anything that does not look like a supported complaint to human review.

Two local signals, both trained from CSV at startup (no pickles):
1. Domain evidence: supported complaints almost always mention a card, a credit
   report or bureau, or a bank account. Text without any such term is out of scope
   unless the classifier below is very confident.
2. A TF-IDF/logistic regression model separating the 9,000 supported training
   complaints from public CFPB complaints about other financial products
   (mortgages, student loans, debt collection, other loans, money transfers).
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
IN_SCOPE = ROOT / "data" / "finetuning" / "training.csv"
OUT_OF_SCOPE = ROOT / "data" / "scope" / "other_products.csv"
THRESHOLD = 0.25
ANCHOR_OVERRIDE = 0.90
METHOD = "Scope gate: domain terms + TF-IDF logistic regression (supported vs other CFPB products)"

ANCHOR = re.compile(
    r"\b(credit|debit|card|cards|bank|banks|banking|checking|savings?|overdraft\w*|atm|apr|"
    r"bureau|equifax|experian|trans ?union|statement|account|accounts|deposit\w*|withdraw\w*|"
    r"transaction\w*|dispute\w*|balance|chase|citi\w*|capital one|wells fargo|"
    r"bank of america|discover|amex|american express|synchrony|barclays|paypal)\b",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    """Match the classifier input: whitespace-normalized first 2,000 characters."""
    return re.sub(r"\s+", " ", text).strip()[:2000]


def _texts(path: Path, split: str | None = None) -> tuple[list[str], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if not split or r.get("split") == split]
    return [normalize(r["text"]) for r in rows], [r.get("family", "") for r in rows]


class ScopeGate:
    method = METHOD

    def __init__(
        self,
        in_scope_path: Path = IN_SCOPE,
        out_of_scope_path: Path = OUT_OF_SCOPE,
        threshold: float = THRESHOLD,
        anchor_override: float = ANCHOR_OVERRIDE,
    ) -> None:
        inside, _ = _texts(Path(in_scope_path))
        outside, families = _texts(Path(out_of_scope_path), "tune")
        if not inside or not outside:
            raise ValueError("Scope gate needs supported and out-of-scope training rows.")
        self.threshold = threshold
        self.anchor_override = anchor_override
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_features=80000,
            sublinear_tf=True,
            stop_words="english",
        )
        features = self.vectorizer.fit_transform(inside + outside)
        self.model = LogisticRegression(max_iter=3000, C=4, class_weight="balanced")
        self.model.fit(features, [1] * len(inside) + [0] * len(outside))
        # Only used to name the closest unsupported product in the review reason.
        self.family_model = LogisticRegression(max_iter=3000, C=4)
        self.family_model.fit(self.vectorizer.transform(outside), families)

    def check(self, text: str) -> dict[str, Any]:
        excerpt = normalize(text)
        vector = self.vectorizer.transform([excerpt])
        score = float(self.model.predict_proba(vector)[0][1])
        anchored = bool(ANCHOR.search(excerpt))
        if score < self.threshold:
            family = str(self.family_model.predict(vector)[0])
            reason = (
                "Reads like a complaint about another financial product "
                f"(closest: {family}). Not covered by the trained taxonomy."
            )
        elif not anchored and score < self.anchor_override:
            reason = "No card, credit-report or bank-account context found."
        else:
            reason = "Matches the supported credit card, credit reporting and bank account scope."
        in_scope = score >= self.threshold and (anchored or score >= self.anchor_override)
        return {
            "in_scope": in_scope,
            "score": round(score, 4),
            "domain_terms": anchored,
            "reason": reason,
            "method": self.method,
        }


@lru_cache(maxsize=2)
def default_gate() -> ScopeGate:
    """Train once per process; the gate takes about a second to fit."""
    return ScopeGate()
