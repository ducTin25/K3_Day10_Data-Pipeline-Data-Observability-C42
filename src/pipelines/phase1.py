from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import assert_clean_contract, build_clean_dataframe, save_clean_artifacts
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
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
    """Execute baseline end-to-end pipeline: raw -> clean -> index -> test set -> evaluate -> quality/freshness -> report."""
    settings = load_settings()

    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    run_dt = datetime.now(UTC)
    handoff = prepare_clean_handoff(records, settings, run_dt)

    bundle = evaluate_pipeline(
        settings=settings,
        index=handoff.index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality_report = run_data_quality_checks(handoff.dataframe, settings, "baseline")
    freshness_report = build_freshness_report(handoff.dataframe, settings, settings.paths.freshness_report)

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "raw_record_count": len(records),
        "clean_record_count": len(handoff.dataframe),
    }

    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )

    print("Phase 1 Baseline Pipeline completed successfully!")

