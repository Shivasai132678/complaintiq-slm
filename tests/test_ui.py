"""Workflow tests for the Streamlit complaint workstation."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def new_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AppTest:
    monkeypatch.setenv("COMPLAINTIQ_DB_PATH", str(tmp_path / "ui.sqlite3"))
    return AppTest.from_file(str(APP), default_timeout=30).run()


def test_empty_workstation_does_not_analyze(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = new_app(monkeypatch, tmp_path)
    assert not app.exception
    assert app.title[0].value == "ComplaintIQ"
    assert "last_result" not in app.session_state
    app.text_area(key="complaint_text").set_value(
        "My credit report has an account that is not mine."
    ).run()
    assert "last_result" not in app.session_state


def test_analysis_is_saved_and_survives_rerun(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = new_app(monkeypatch, tmp_path)
    app.text_area(key="complaint_text").set_value(
        "My credit report contains an account that is not mine. I disputed the incorrect information but it was not corrected."
    )
    app.button(key="analyze_submit").click().run()
    assert not app.exception
    assert app.session_state["last_result"]["product"]
    result_id = app.session_state["last_result"]["id"]
    app.run()
    assert app.session_state["last_result"]["id"] == result_id
    app.radio(key="workspace").set_value("Complaint queue").run()
    assert not app.exception
    assert len(app.dataframe) > 0


def test_slm_requires_explicit_existing_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = new_app(monkeypatch, tmp_path)
    app.selectbox(key="model_mode").set_value("Local SLM (GGUF)").run()
    app.text_area(key="complaint_text").set_value("My bank charged me an incorrect overdraft fee.")
    app.button(key="analyze_submit").click().run()
    assert not app.exception
    assert any("GGUF" in error.value for error in app.error)
    assert "last_result" not in app.session_state


def test_empty_input_and_empty_dashboard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = new_app(monkeypatch, tmp_path)
    app.button(key="analyze_submit").click().run()
    assert any("Enter a complaint" in error.value for error in app.error)
    app.radio(key="workspace").set_value("Analytics").run()
    assert not app.exception
    assert any("after complaints" in item.value for item in app.info)


def test_dashboard_uses_saved_analysis(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = new_app(monkeypatch, tmp_path)
    app.text_area(key="complaint_text").set_value(
        "My bank charged overdraft fees on my checking account and refused to reverse the fee."
    )
    app.button(key="analyze_submit").click().run()
    app.radio(key="workspace").set_value("Analytics").run()
    assert not app.exception
    assert app.metric[0].value == "1"
    app.radio(key="workspace").set_value("Model evidence").run()
    assert not app.exception
    assert any("fine-tuned" in item.value for item in app.caption)


def test_export_neutralizes_spreadsheet_formulas() -> None:
    import pandas as pd

    from app import csv_export

    exported = csv_export(pd.DataFrame({"text": ["=SUM(A1:A2)", "  @SUM(A1)", "normal narrative"]}))
    assert "'=SUM" in exported
    assert "'  @SUM" in exported
    assert "normal narrative" in exported


def test_batch_requires_text_column_and_saves_only_valid_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = new_app(monkeypatch, tmp_path)
    app.radio(key="workspace").set_value("Batch analysis").run()
    app.file_uploader[0].set_value(("bad.csv", b"narrative\nhello\n", "text/csv")).run()
    assert any("column named text" in error.value for error in app.error)
    data = b'text\nMy checking account was charged an overdraft fee.\n""\n'
    app.file_uploader[0].set_value(("complaints.csv", data, "text/csv")).run()
    assert "batch_output" not in app.session_state
    next(button for button in app.button if button.label == "Analyze and save batch").click().run()
    assert not app.exception
    results = app.session_state["batch_output"]
    assert len(results) == 2
    assert "id" in results[0]
    assert results[1]["error"] == "Empty narrative"
    app.radio(key="workspace").set_value("Analytics").run()
    assert app.metric[0].value == "1"


def test_actual_evaluation_report_renders_readable_limits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report = APP.parent / "artifacts" / "evaluation.json"
    if not report.exists():
        pytest.skip("Measured report not generated yet")
    app = new_app(monkeypatch, tmp_path)
    app.radio(key="workspace").set_value("Model evidence").run()
    assert not app.exception
    assert len(app.metric) == 4
    assert all(len(item.value.strip()) != 1 for item in app.caption)
    assert any(
        "Training deferred" in frame.value.astype(str).to_numpy().flatten()
        for frame in app.dataframe
    )
