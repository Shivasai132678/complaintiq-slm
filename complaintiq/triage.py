"""Demonstration routing rules, adapted from the MIT upstream triage engine.

These are heuristic work-queue priorities, not legal or regulatory assessments.
"""

from __future__ import annotations

import re

RULES = (
    (
        "Critical",
        (
            "identity theft",
            "stole my identity",
            "account takeover",
            "unauthorized wire",
            "emptied my account",
            "wire fraud",
        ),
    ),
    (
        "High",
        (
            "account frozen",
            "account is frozen",
            "cannot access money",
            "unauthorized charge",
            "unauthorized debit",
            "fraudulent transaction",
            "harassment",
        ),
    ),
    (
        "Medium",
        (
            "refund",
            "late fee",
            "overdraft fee",
            "billing error",
            "dispute",
            "inaccurate",
            "incorrect",
        ),
    ),
)
DEPARTMENTS = {
    "Credit reporting": "Credit Reporting Team",
    "Credit card": "Card Services Team",
    "Checking or savings account": "Deposit Operations Team",
}


def triage(text: str) -> dict[str, str]:
    """Choose the highest matching priority with a concrete, inspectable reason."""
    for priority, phrases in RULES:
        for phrase in phrases:
            for match in re.finditer(r"\b" + re.escape(phrase) + r"\b", text, re.I):
                # Basic local negation guard; complex semantics require a reviewer.
                prefix = text[max(0, match.start() - 28) : match.start()]
                if re.search(
                    r"\b(?:no|not|never|without)(?:\s+(?:any|an|a|the|evidence\s+of|signs?\s+of))?\s*$",
                    prefix,
                    re.I,
                ):
                    continue
                return {
                    "priority": priority,
                    "priority_reason": f"Rule matched “{match.group()}”. Human review required.",
                }
    return {
        "priority": "Low",
        "priority_reason": "No configured urgent-risk phrase detected; standard review queue.",
    }


def routing(product: str, priority: str) -> dict[str, str]:
    """Produce safe suggested actions rather than promise automated bank actions."""
    department = DEPARTMENTS.get(product, "Manual Review Team")
    if priority == "Critical":
        action = "Escalate to a fraud specialist; verify the customer and review reported unauthorized activity."
    elif product == "Credit reporting":
        action = "Review the disputed record and supporting documents; prepare a correction investigation."
    elif product == "Credit card":
        action = "Review the statement and transaction evidence; assess the appropriate billing dispute process."
    elif product == "Checking or savings account":
        action = "Review account access and transaction history; contact the customer to clarify the issue."
    else:
        action = "Ask a reviewer to confirm the complaint category and appropriate department."
    return {"department": department, "action": action}
