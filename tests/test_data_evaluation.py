from scripts.evaluate import metric_report


def test_metric_report_includes_all_requested_metrics():
    result = metric_report(["a", "a", "b", "b"], ["a", "b", "b", "b"])
    assert result["accuracy"] == 0.75
    assert set(
        ["precision_macro", "recall_macro", "f1_macro", "per_class", "confusion_matrix"]
    ).issubset(result)


def test_abstention_penalizes_recall_without_inventing_ground_truth_class():
    report = metric_report(["a", "a", "b", "b"], ["a", "Unknown", "b", "b"])
    assert report["recall_macro"] == 0.75
    assert report["f1_macro"] > 0.8
    assert "Unknown" in report["labels"]


def test_real_held_out_baseline_report_has_valid_support():
    from pathlib import Path

    from scripts.evaluate import evaluate

    report = evaluate(Path("data/training.csv"), Path("data/test.csv"))
    assert report["test_size"] == 153
    assert report["errors"] == 0
    assert 0 <= report["joint_accuracy"] <= report["product"]["accuracy"] <= 1
    assert sum(sum(row) for row in report["product"]["confusion_matrix"]) == 153
    assert report["product"]["per_class"]["weighted avg"]["support"] == 153
