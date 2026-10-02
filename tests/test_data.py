from scripts.prepare_data import clean_rows, split_rows


def test_dedup_and_stratified_split():
    rows = [
        {
            "text": f"Complaint narrative example number {i}",
            "product": "Credit card",
            "issue": "Billing",
            "complaint_id": str(i),
        }
        for i in range(20)
    ]
    rows.append(dict(rows[0], text=rows[0]["text"].upper()))
    cleaned = clean_rows(rows, min_chars=10)
    assert len(cleaned) == 20
    splits = split_rows(cleaned)
    assert [len(splits[k]) for k in ("training", "validation", "test")] == [14, 3, 3]
    assert len({row["text"] for values in splits.values() for row in values}) == 20


def test_empty_narratives_removed():
    assert clean_rows([{"text": "", "product": "Credit card", "issue": "Billing"}]) == []


def test_archive_reproduction_preserves_ids_and_source_manifest(tmp_path):
    import csv
    import io
    import json
    import zipfile

    from scripts.prepare_data import prepare_archive

    stream = io.StringIO()
    fields = ["Product", "Issue", "Consumer complaint narrative", "Complaint ID", "Date received"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for i in range(40):
        writer.writerow(
            {
                "Product": "Credit card",
                "Issue": "Billing disputes",
                "Consumer complaint narrative": f"Actual fixture number {i} describes a billing dispute. "
                + "Additional complaint details. " * 4,
                "Complaint ID": str(i),
                "Date received": "2017-01-01",
            }
        )
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("complaints.csv", stream.getvalue())
    manifest = prepare_archive(archive, tmp_path / "output", per_class=30)
    assert manifest["sample_size"] == 30
    assert sum(manifest["split_counts"].values()) == 30
    assert json.loads((tmp_path / "output/manifest.json").read_text())["trained_slm"] is False
    assert (
        (tmp_path / "output/test.csv")
        .read_text()
        .startswith("text,product,issue,complaint_id,date_received")
    )
