"""Conservative approximate duplicate detection on actual inference excerpts."""

from scripts.near_duplicates import NearDuplicateIndex


def narrative(subject: str, count: int = 200) -> str:
    return " ".join(f"{subject}{number}" for number in range(count))


def test_normalized_exact_and_high_overlap_retrieval() -> None:
    index = NearDuplicateIndex()
    text = narrative("transaction")
    index.add(text, "legacy-001")
    assert index.find("  " + text.upper().replace(" ", "  ") + " ") == "legacy-001"
    changed = text.replace("transaction50", "changed_reference")
    assert index.find(changed) == "legacy-001"


def test_shared_boilerplate_does_not_make_distinct_complaints_duplicates() -> None:
    index = NearDuplicateIndex()
    boilerplate = narrative("standard", 45)
    index.add(boilerplate + " " + narrative("bank_issue", 60), "first")
    assert index.find(boilerplate + " " + narrative("card_issue", 60)) is None


def test_small_text_and_repeated_add_are_safe() -> None:
    index = NearDuplicateIndex()
    index.add("Hello world", "small")
    assert index.find("hello   WORLD") == "small"
    assert index.find("hello universe") is None
    index.add("Hello world", "other")
    assert index.find("Hello world") == "small"


def test_index_never_mutates_or_moves_reserved_records() -> None:
    index = NearDuplicateIndex()
    index.add(narrative("reserved"), "original-test-id")
    match = index.find(narrative("reserved").replace("reserved50", "edited50"))
    assert match == "original-test-id"
    assert len(index) == 1
