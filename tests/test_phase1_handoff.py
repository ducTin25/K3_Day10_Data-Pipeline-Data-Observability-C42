from datetime import datetime
from types import SimpleNamespace

import pytest

from ingestion.cleaning import CleanContractError
from ingestion.crossref import PaperRecord
from pipelines.phase1 import prepare_clean_handoff


def _record(summary: str) -> PaperRecord:
    return PaperRecord(
        paper_id="10.1000/handoff.1",
        title="A stable clean contract",
        summary=summary,
        authors=["Ada Lovelace"],
        categories=["Data Engineering"],
        primary_category="Data Engineering",
        published="2026-08-01",
        updated="2026-08-02",
        abs_url="https://doi.org/10.1000/handoff.1",
        pdf_url="",
        comment="",
    )


def test_handoff_stops_before_testset_and_index_when_contract_fails(monkeypatch, tmp_path) -> None:
    called = {"test_set": False, "index": False}
    monkeypatch.setattr(
        "pipelines.phase1.build_test_set",
        lambda *args, **kwargs: called.__setitem__("test_set", True),
    )
    monkeypatch.setattr(
        "pipelines.phase1.LocalEmbeddingIndex.build",
        lambda *args, **kwargs: called.__setitem__("index", True),
    )
    settings = SimpleNamespace(
        refresh_test_set=True,
        paths=SimpleNamespace(
            clean_csv=tmp_path / "clean.csv",
            clean_json=tmp_path / "clean.json",
            eval_testset=tmp_path / "test_set.json",
            embeddings_json=tmp_path / "embeddings.json",
        ),
        baseline_collection_name="papers-baseline",
    )

    with pytest.raises(CleanContractError):
        prepare_clean_handoff([_record("too short")], settings, datetime(2026, 8, 6))

    assert called == {"test_set": False, "index": False}
