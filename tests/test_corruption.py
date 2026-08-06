from datetime import datetime
import json

from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import PaperRecord


def _create_sample_clean_df():
    records = [
        PaperRecord(
            paper_id=f"10.1000/test.{i}",
            title=f"Paper Title {i} with sufficient length",
            summary=f"Summary for paper {i} that is long enough to pass the min length requirement.",
            authors=["Author One", "Author Two"],
            categories=["CS.AI"],
            primary_category="CS.AI",
            published=f"2026-08-0{i+1}",
            updated="",
            abs_url="",
            pdf_url="",
            comment="",
        )
        for i in range(6)
    ]
    return build_clean_dataframe(records, datetime(2026, 8, 10))


def test_corrupt_clean_dataframe(tmp_path) -> None:
    df = _create_sample_clean_df()
    log_path = tmp_path / "corruption_log.json"

    corrupted_df = corrupt_clean_dataframe(df, log_path)

    assert log_path.exists()
    log_data = json.loads(log_path.read_text(encoding="utf-8"))
    assert log_data["initial_rows"] == 6
    assert len(log_data["steps"]) > 0
    for step in log_data["steps"]:
        assert {"parameter", "before_count", "after_count", "changes"}.issubset(step)
        assert all({"paper_id", "before", "after"}.issubset(change) for change in step["changes"])
    assert "text_for_embedding" in corrupted_df.columns
