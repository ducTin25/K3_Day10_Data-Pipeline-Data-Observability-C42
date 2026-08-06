import pandas as pd
import pytest

from retrieval.index import assert_index_contract


def _indexable_rows() -> pd.DataFrame:
    row = {
        "paper_id": "10.1000/index.1",
        "title": "Indexable title",
        "text_for_embedding": "Title: Indexable title\nSummary: useful text",
        "published": "1970-01-01",
        "authors_joined": "Ada Lovelace",
        "categories_joined": "",
        "summary": "",
        "abs_url": "https://doi.org/10.1000/index.1",
        "pdf_url": "",
    }
    return pd.DataFrame([row, row.copy()])


def test_index_contract_allows_intentional_quality_failures() -> None:
    df = _indexable_rows()

    assert_index_contract(df)

    assert df["paper_id"].duplicated().any()
    assert (df["summary"] == "").all()


def test_index_contract_stops_on_structural_failure() -> None:
    df = _indexable_rows().drop(columns=["text_for_embedding"])

    with pytest.raises(ValueError, match="missing columns: text_for_embedding"):
        assert_index_contract(df)


def test_index_contract_stops_on_blank_embedding_text() -> None:
    df = _indexable_rows()
    df.loc[0, "text_for_embedding"] = ""

    with pytest.raises(ValueError, match="text_for_embedding has 1 blank row"):
        assert_index_contract(df)
