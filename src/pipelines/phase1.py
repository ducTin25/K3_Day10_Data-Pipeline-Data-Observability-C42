from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from core.config import Settings
from core.utils import read_json
from evaluation.testset import build_test_set
from ingestion.cleaning import assert_clean_contract, build_clean_dataframe, save_clean_artifacts
from ingestion.crossref import PaperRecord
from retrieval.index import LocalEmbeddingIndex


@dataclass(frozen=True)
class CleanHandoff:
    dataframe: pd.DataFrame
    contract: dict
    test_set: list[dict]
    index: LocalEmbeddingIndex


def prepare_clean_handoff(
    records: list[PaperRecord],
    settings: Settings,
    run_date: datetime,
) -> CleanHandoff:
    """Gate clean data once, then hand the same dataframe to test-set and index."""
    clean_df = build_clean_dataframe(records, run_date)
    contract = assert_clean_contract(clean_df)
    save_clean_artifacts(clean_df, settings)

    clean_ids = set(clean_df["paper_id"].astype(str))
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
    ground_truth_ids = {
        doc_id
        for sample in test_set
        for doc_id in sample.get("ground_truth_doc_ids", [])
    }
    if not ground_truth_ids or not ground_truth_ids.issubset(clean_ids):
        raise ValueError("Test-set document IDs are not a subset of the gated clean corpus.")

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    index_ids = {document["paper_id"] for document in index.documents}
    if index.collection_name != settings.baseline_collection_name:
        raise ValueError("Baseline handoff wrote to an unexpected Chroma collection.")
    if len(index.documents) != len(clean_df) or index_ids != clean_ids:
        raise ValueError("Baseline index count/IDs do not match the gated clean corpus.")

    return CleanHandoff(dataframe=clean_df, contract=contract, test_set=test_set, index=index)


def main() -> None:
    """TODO(student): xay dung baseline pipeline end-to-end.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    raise NotImplementedError("Student task: implement phase1 pipeline.")
