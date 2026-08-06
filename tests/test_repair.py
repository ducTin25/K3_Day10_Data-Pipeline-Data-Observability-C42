from types import SimpleNamespace

from ingestion.repair import repair_data_from_raw


def test_repair_data_from_raw(tmp_path) -> None:
    raw_json = tmp_path / "crossref_records.json"
    raw_json.write_text(
        """[
        {
            "paper_id": "10.1000/repair.1",
            "title": "Repair Test Title",
            "summary": "This is a sufficiently long summary for repair test paper 1.",
            "authors": ["Author A"],
            "categories": ["CS.SE"],
            "primary_category": "CS.SE",
            "published": "2026-08-01",
            "updated": "",
            "abs_url": "",
            "pdf_url": "",
            "comment": ""
        }
    ]""",
        encoding="utf-8",
    )

    class DummyPaths:
        raw_records_json = raw_json
        repaired_clean_csv = tmp_path / "papers_clean_repaired.csv"
        repaired_clean_json = tmp_path / "papers_clean_repaired.json"
        corrupted_clean_json = tmp_path / "papers_clean_corrupted.json"
        clean_json = tmp_path / "papers_clean.json"
        repaired_metrics = tmp_path / "repaired_metrics.json"

    settings = SimpleNamespace(paths=DummyPaths())

    df_repaired, report = repair_data_from_raw(settings)

    assert len(df_repaired) == 1
    assert df_repaired.iloc[0]["paper_id"] == "10.1000/repair.1"
    assert report["repaired_record_count"] == 1
    assert settings.paths.repaired_clean_csv.exists()
    assert settings.paths.repaired_clean_json.exists()
    assert settings.paths.repaired_metrics.exists()
