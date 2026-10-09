"""Tests for the Windows training kit's shared label/prompt/metric code (no torch needed)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc_kit" / "src"))
sys.path.insert(0, str(ROOT / "pc_kit" / "mac_prep"))

from ckit_common import (  # noqa: E402
    CLASSES,
    TAXONOMY,
    answer_for,
    map_cfpb_label,
    messages_for,
    parse_answer,
)
from ckit_eval import AnswerTrie  # noqa: E402
from ckit_metrics import classification_report  # noqa: E402
from prepare_dataset import allocate  # noqa: E402

from complaintiq.models import BaselineClassifier  # noqa: E402
from scripts.benchmark_local import messages_for as app_messages_for  # noqa: E402

OOS = "Unknown / Needs review"


def test_taxonomy_and_prompt_match_the_app() -> None:
    app_taxonomy = BaselineClassifier().taxonomy
    assert TAXONOMY == app_taxonomy
    text = 'My card was charged twice "please" fix'
    assert messages_for(text) == app_messages_for(text, app_taxonomy)
    assert len(CLASSES) == 10 and CLASSES[-1] == OOS


def test_old_and_new_cfpb_labels_map_to_the_same_class() -> None:
    old = map_cfpb_label("Bank account or service", "", "Deposits and withdrawals", "")
    new = map_cfpb_label(
        "Checking or savings account", "Checking account", "Managing an account", "Deposits and withdrawals"
    )
    assert old == new == ("Checking or savings account", "Deposits and withdrawals", "")
    assert map_cfpb_label(
        "Checking or savings account", "", "Managing an account", "Banking errors"
    ) == ("Checking or savings account", "Managing an account", "")
    assert map_cfpb_label(
        "Credit card or prepaid card", "General-purpose credit card or charge card",
        "Problem with a purchase shown on your statement", "",
    ) == ("Credit card", "Billing disputes", "")
    assert map_cfpb_label(
        "Credit reporting or other personal consumer reports", "Credit reporting",
        "Problem with a company's investigation into an existing problem", "",
    )[1].startswith("Problem with a credit reporting company")


def test_out_of_scope_and_excluded_rows() -> None:
    assert map_cfpb_label("Mortgage", "", "Trouble during payment process", "") == (
        "Unknown", "Needs review", "mortgage",
    )
    assert map_cfpb_label("Credit card or prepaid card", "General-purpose prepaid card", "Fees", "")[2] == "prepaid_card"
    # Supported product, unsupported issue: excluded entirely, not out of scope.
    assert map_cfpb_label("Credit card", "", "Getting a credit card", "") is None
    assert map_cfpb_label(
        "Credit reporting, credit repair services, or other personal consumer reports",
        "Credit repair services", "Incorrect information on your report", "",
    ) is None


def test_answer_round_trip() -> None:
    assert parse_answer(answer_for("Credit card", "Other")) == "Credit card / Other"
    assert parse_answer('{"product": "Credit card", "issue": "Nope"}') == "invalid"
    assert parse_answer("not json") == "invalid"


def test_answer_trie_constrains_to_valid_labels() -> None:
    trie = AnswerTrie({"A / x": [1, 2, 9], "A / y": [1, 3, 9], OOS: [4, 9]}, end_id=9)
    assert sorted(trie.allowed([])) == [1, 4]
    assert sorted(trie.allowed([1])) == [2, 3]
    assert trie.allowed([1, 2]) == [9]
    assert trie.label([1, 3, 9]) == "A / y"
    assert trie.label([5]) == "invalid"


def test_metrics() -> None:
    gold = ["Credit card / Other", "Credit card / Other", OOS, "Credit card / Fees or interest"]
    pred = ["Credit card / Other", OOS, OOS, "Credit card / Other"]
    report = classification_report(gold, pred)
    assert report["accuracy"] == 0.5
    assert report["product_accuracy"] == 0.75
    assert report["in_scope_joint_accuracy"] == round(1 / 3, 4)
    assert report["out_of_scope"]["recall"] == 1.0
    assert report["out_of_scope"]["precision"] == 0.5


def test_allocate_spreads_and_caps() -> None:
    assert allocate(10, {"a": 100, "b": 100}) == {"a": 5, "b": 5}
    share = allocate(10, {"a": 2, "b": 100, "c": 100})
    assert share["a"] == 2 and sum(share.values()) == 10
