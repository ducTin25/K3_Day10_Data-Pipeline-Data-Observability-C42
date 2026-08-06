from datetime import datetime

import pandas as pd

from ingestion.cleaning import build_clean_dataframe, save_clean_artifacts, strip_html_tags
from ingestion.crossref import PaperRecord


def _sample_records() -> list[PaperRecord]:
    return [
        PaperRecord(
            paper_id="10.1000/clean.1",
            title="<jats:p> Clean Title 1 </jats:p>",
            summary="<p>This is a sufficiently long summary for paper 1 to pass the 40 characters minimum length test.</p>",
            authors=["Alice Smith", "Bob Jones"],
            categories=["Computer Science"],
            primary_category="Computer Science",
            published="2026-08-01",
            updated="2026-08-02",
            abs_url="https://doi.org/10.1000/clean.1",
            pdf_url="https://example.com/paper1.pdf",
            comment="",
        ),
        PaperRecord(
            paper_id="10.1000/clean.2",
            title="Clean Title 2",
            summary="Short summary",  # < 40 chars -> should be filtered
            authors=["Charlie Brown"],
            categories=["Physics"],
            primary_category="Physics",
            published="2026-07-15",
            updated="",
            abs_url="https://doi.org/10.1000/clean.2",
            pdf_url="",
            comment="",
        ),
        PaperRecord(
            paper_id="10.1000/clean.1",  # Duplicate paper_id
            title="Duplicate Title",
            summary="This is a duplicate paper summary that has enough length to pass the character limit.",
            authors=["Alice Smith"],
            categories=["Computer Science"],
            primary_category="Computer Science",
            published="2026-08-01",
            updated="",
            abs_url="",
            pdf_url="",
            comment="",
        ),
    ]


def test_strip_html_tags() -> None:
    text = "<jats:p>Hello <b>World</b></jats:p>"
    assert strip_html_tags(text) == "Hello World"


def test_build_clean_dataframe_normalizes_and_filters() -> None:
    records = _sample_records()
    now = datetime(2026, 8, 6)
    df = build_clean_dataframe(records, now)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["paper_id"] == "10.1000/clean.1"
    assert row["title"] == "Clean Title 1"
    assert row["authors_joined"] == "Alice Smith, Bob Jones"
    assert row["categories_joined"] == "Computer Science"
    assert row["age_days"] == 5
    assert "Title: Clean Title 1" in row["text_for_embedding"]
    assert "Summary: This is a sufficiently long summary" in row["text_for_embedding"]


def test_save_clean_artifacts(tmp_path) -> None:
    class DummyPaths:
        clean_csv = tmp_path / "papers_clean.csv"
        clean_json = tmp_path / "papers_clean.json"

    class DummySettings:
        paths = DummyPaths()

    records = _sample_records()
    df = build_clean_dataframe(records, datetime(2026, 8, 6))
    csv_path, json_path = save_clean_artifacts(df, DummySettings())

    assert csv_path.exists()
    assert json_path.exists()
    df_read = pd.read_csv(csv_path)
    assert len(df_read) == 1
    assert df_read.iloc[0]["paper_id"] == "10.1000/clean.1"
