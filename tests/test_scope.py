from pathlib import Path

from complaintiq.scope import default_gate
from complaintiq.service import ComplaintService


def test_gate_separates_supported_and_unrelated_text() -> None:
    gate = default_gate()
    assert gate.check(
        "I was charged a late fee on my credit card although my payment posted before the due date."
    )["in_scope"]
    assert gate.check(
        "My credit report shows a collection account I never opened and the bureau will not remove it."
    )["in_scope"]
    result = gate.check("The restaurant delivered my order an hour late and the food was cold.")
    assert not result["in_scope"]
    assert "No card" in result["reason"]
    mortgage = gate.check(
        "My mortgage servicer misapplied my escrow payment and now says my home loan is delinquent."
    )
    assert not mortgage["in_scope"]
    assert "Mortgage" in mortgage["reason"]


def test_service_routes_out_of_scope_text_to_review(tmp_path: Path) -> None:
    service = ComplaintService(str(tmp_path / "scope.sqlite"))
    record = service.analyze("My neighbour's dog barks all night and the manager ignores me.")
    assert (record["product"], record["issue"]) == ("Unknown", "Needs review")
    assert record["status"] == "Needs review"
    assert record["scope_check"]["in_scope"] is False
    assert record["department"] == "Manual Review Team"
    kept = service.analyze("A duplicate charge appeared on my credit card statement.")
    assert kept["scope_check"]["in_scope"] is True
    assert kept["product"] == "Credit card"
