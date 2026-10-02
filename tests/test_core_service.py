"""Business-level tests using a tiny controlled training corpus."""

import csv
import json
from pathlib import Path

import pytest

from complaintiq.models import BaselineClassifier, validate_prediction
from complaintiq.service import ComplaintService
from complaintiq.triage import triage


@pytest.fixture
def training(tmp_path: Path) -> Path:
    path = tmp_path / "train.csv"
    rows = []
    for index in range(12):
        rows.extend(
            [
                {
                    "text": f"credit report inaccurate bureau dispute wrong record {index}",
                    "product": "Credit reporting",
                    "issue": "Incorrect information on your report",
                },
                {
                    "text": f"credit card merchant purchase billing charge refund {index}",
                    "product": "Credit card",
                    "issue": "Problem with a purchase shown on your statement",
                },
                {
                    "text": f"checking savings bank deposit withdrawal account money {index}",
                    "product": "Checking or savings account",
                    "issue": "Managing an account",
                },
            ]
        )
    with path.open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=["text", "product", "issue"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_baseline_prediction_has_lime_attribution(training: Path) -> None:
    model = BaselineClassifier(training)
    result = model.classify("My credit report has inaccurate bureau records")
    assert result["product"] == "Credit reporting"
    assert result["issue"] == "Incorrect information on your report"
    assert model.explain("My credit report has inaccurate bureau records", result["product"])
    assert model.classify("astronomy nebula stellar physics")["product"] == "Unknown"


def test_triage_severity_and_negation() -> None:
    assert triage("Someone stole my identity")["priority"] == "Critical"
    assert triage("My account is frozen and I cannot access money")["priority"] == "High"
    assert triage("Please refund this late fee")["priority"] == "Medium"
    assert triage("I have a general account question")["priority"] == "Low"
    assert triage("There was no identity theft")["priority"] != "Critical"


def test_service_persists_and_aggregates(training: Path, tmp_path: Path) -> None:
    db = tmp_path / "history.sqlite"
    service = ComplaintService(db_path=str(db), training_path=training)
    result = service.analyze(
        "My credit report has inaccurate bureau records. Someone stole my identity."
    )
    assert result["backend"] == "baseline"
    assert result["priority"] == "Critical"
    assert result["department"] == "Credit Reporting Team"
    assert result["explanation_method"] == "LIME product attribution"
    assert result["tokens_input"] == 0
    assert result["tokens_output"] == 0
    assert service.list_complaints()[0]["id"] == result["id"]
    assert ComplaintService(db_path=str(db), training_path=training).analytics()["total"] == 1
    assert service.analytics()["by_priority"] == {"Critical": 1}
    assert service.analyze("quantum stars galaxies")["status"] == "Needs review"


@pytest.mark.parametrize("text", ["", " ", "a" * 6001, None, 123])
def test_invalid_inputs_never_saved(training: Path, tmp_path: Path, text: object) -> None:
    service = ComplaintService(str(tmp_path / "db.sqlite"), training_path=training)
    with pytest.raises(ValueError):
        service.analyze(text)
    assert service.analytics()["total"] == 0


def test_explicit_backend_failure(training: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="backend"):
        ComplaintService(str(tmp_path / "db"), backend="magic", training_path=training)
    with pytest.raises(ValueError, match="GGUF"):
        ComplaintService(str(tmp_path / "db"), backend="slm", training_path=training)


def test_prediction_schema_validation() -> None:
    taxonomy = {"Credit card": ["Billing"]}
    assert (
        validate_prediction('{"product":"Credit card","issue":"Billing"}', taxonomy)["product"]
        == "Credit card"
    )
    with pytest.raises(ValueError):
        validate_prediction('{"product":"Credit card","issue":"Mortgage"}', taxonomy)
    with pytest.raises(ValueError):
        validate_prediction('{"product":"Unknown","issue":"x"}', taxonomy)
    with pytest.raises(ValueError):
        validate_prediction("I think Credit card", taxonomy)


def test_training_validation(tmp_path: Path) -> None:
    from complaintiq.models import load_rows

    with pytest.raises(ValueError, match="missing"):
        load_rows(tmp_path / "absent.csv")
    path = tmp_path / "bad.csv"
    path.write_text("wrong,columns\nx,y\n")
    with pytest.raises(ValueError, match="columns"):
        load_rows(path)
    path.write_text("text,product,issue\nhello,one,issue\n")
    with pytest.raises(ValueError, match="two product"):
        load_rows(path)


def test_issue_classifier_preserves_product_pairs(training: Path) -> None:
    with training.open("a") as handle:
        for index in range(12):
            handle.write(
                f"credit card application denied rejection approval {index},Credit card,Application rejected\n"
            )
    model = BaselineClassifier(training)
    result = model.classify("credit card application denied rejection approval")
    assert result["product"] == "Credit card"
    assert result["issue"] == "Application rejected"
    assert model.explain("strange text", "Unknown") == []


def test_store_handles_sql_and_unicode(tmp_path: Path) -> None:
    from complaintiq.storage import ComplaintStore

    store = ComplaintStore(str(tmp_path / "store.db"))
    record = {
        "id": "'); DROP TABLE complaints;--",
        "created_at": "2026-01-01",
        "text": "₹ — customer account",
    }
    store.save(record)
    assert store.list() == [record]


def test_local_slm_is_lazy_validated_and_tracks_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys
    import types

    from complaintiq.models import LocalSLMClassifier

    taxonomy = {"Credit card": ["Billing"], "Credit reporting": ["Incorrect report"]}
    path = tmp_path / "test.gguf"
    path.write_bytes(b"not a real model; mocked loader")
    calls = []

    class FakeLlama:
        def __init__(self, **kwargs):
            assert kwargs["n_gpu_layers"] == -1

        def create_chat_completion(self, **kwargs):
            calls.append(kwargs)
            return {
                "choices": [
                    {"message": {"content": '{"product":"Credit card","issue":"Billing"}'}}
                ],
                "usage": {"prompt_tokens": 42, "completion_tokens": 8},
            }

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=FakeLlama))
    model = LocalSLMClassifier(str(path), taxonomy)
    assert model.classify("Please review my billing")["tokens_input"] == 42
    assert model.classify("Please review my billing")["tokens_output"] == 0
    assert model.classify("Please review my billing")["cached"] is True
    assert len(calls) == 1
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert json.loads(calls[0]["messages"][1]["content"])["complaint"] == "Please review my billing"
    assert model.explain("Billing credit card problem", "Credit card")
    assert model.explain("astronomy", "Unknown") == []
    with pytest.raises(ValueError, match="GGUF"):
        LocalSLMClassifier(str(tmp_path / "absent.gguf"), taxonomy)
    assert (
        validate_prediction('{"product":"Unknown","issue":"Needs review"}', taxonomy)["issue"]
        == "Needs review"
    )
    for malformed in [
        "[]",
        '{"product":1,"issue":"Billing"}',
        '{"product":"Credit card","issue":"Billing","confidence":99}',
    ]:
        with pytest.raises(ValueError):
            validate_prediction(malformed, taxonomy)


def test_slm_service_has_no_silent_fallback(
    training: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from complaintiq import service as module

    class FakeSLM:
        model_version = "mock.gguf"

        def __init__(self, model_path, taxonomy):
            pass

        def classify(self, text):
            return {
                "product": "Credit card",
                "issue": "Problem with a purchase shown on your statement",
                "tokens_input": 60,
                "tokens_output": 15,
            }

        def explain(self, text, product):
            return [{"token": "purchase", "weight": 0.1}]

    monkeypatch.setattr(module, "LocalSLMClassifier", FakeSLM)
    service = module.ComplaintService(
        str(tmp_path / "slm.db"), backend="slm", model_path="mock.gguf", training_path=training
    )
    result = service.analyze("I dispute a purchase shown on my credit card statement")
    assert result["backend"] == "slm"
    assert result["tokens_input"] == 60
    assert result["explanation"] == []
    assert "disabled" in result["explanation_method"]
    service.slm_lime = True
    assert service.analyze("Please review a purchase")["explanation"][0]["token"] == "purchase"
    assert len(service._summary("a" * 500)) == 320

    def fail(text):
        raise ValueError("Invalid SLM label")

    service.model.classify = fail
    with pytest.raises(ValueError, match="Invalid SLM"):
        service.analyze("This must not silently fall back")
    assert service.analytics()["total"] == 2


def test_negation_only_applies_to_the_risk_phrase() -> None:
    assert triage("The bank did not refund the unauthorized charge")["priority"] == "High"
    assert triage("There was no unauthorized charge")["priority"] == "Low"


def test_explanation_failure_preserves_valid_analysis(
    training: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ComplaintService(str(tmp_path / "explanation.db"), training_path=training)

    def fail(text, product):
        raise RuntimeError("explanation failed")

    monkeypatch.setattr(service.model, "explain", fail)
    record = service.analyze("credit card merchant purchase billing charge")
    assert record["explanation"] == []
    assert "unavailable" in record["explanation_method"]
    assert len(service.list_complaints()) == 1
