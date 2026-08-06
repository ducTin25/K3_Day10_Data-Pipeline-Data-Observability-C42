from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import assert_clean_contract, build_clean_dataframe, save_clean_artifacts
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records, write_raw_lineage_handoff
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
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    index_ids = {document["paper_id"] for document in index.documents}
    if index.collection_name != settings.baseline_collection_name:
        raise ValueError("Baseline handoff wrote to an unexpected Chroma collection.")
    if len(index.documents) != len(clean_df) or index_ids != clean_ids:
        raise ValueError("Baseline index count/IDs do not match the gated clean corpus.")

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
    ground_truth_ids = {
        doc_id
        for sample in test_set
        for doc_id in sample.get("ground_truth_doc_ids", [])
    }
    if not ground_truth_ids or not ground_truth_ids.issubset(index_ids):
        raise ValueError("Test-set document IDs are not a subset of the gated baseline index.")

    return CleanHandoff(dataframe=clean_df, contract=contract, test_set=test_set, index=index)


def main() -> None:
    """Run raw → clean → index → test set → evaluate → observability → report."""
    settings = load_settings()
    paths = settings.paths

    raw_snapshot_ready = paths.raw_api_response.exists() and paths.raw_records_json.exists()
    if settings.refresh_source or not raw_snapshot_ready:
        records = fetch_source_records(settings)
        raw_mode = "fetched"
    else:
        records = load_raw_records(paths.raw_records_json)
        raw_mode = "snapshot"
    lineage = write_raw_lineage_handoff(settings)
    if not lineage.get("cleaning_input_ready"):
        raise RuntimeError("Raw lineage audit failed; clean/index handoff was not started.")

    handoff = prepare_clean_handoff(records, settings, run_date=now_utc())
    evaluation = evaluate_pipeline(
        settings=settings,
        index=handoff.index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    quality = run_data_quality_checks(handoff.dataframe, settings, report_name="baseline")
    freshness = build_freshness_report(handoff.dataframe, settings, paths.freshness_report)

    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary={
            "source": settings.source_api,
            "raw_mode": raw_mode,
            "query": settings.source_query,
            "filter": settings.source_filter,
            "raw_records": len(records),
            "clean_records": len(handoff.dataframe),
            "indexed_documents": len(handoff.index.documents),
            "test_samples": len(handoff.test_set),
            "collection": handoff.index.collection_name,
        },
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    if not quality.get("passed") or not freshness.get("is_fresh"):
        raise RuntimeError(
            "Baseline artifacts were generated, but quality/freshness did not pass. "
            f"Inspect {paths.quality_dir.relative_to(paths.project_dir)}."
        )

    print(
        "Baseline complete: "
        f"{len(records)} raw -> {len(handoff.dataframe)} clean -> "
        f"{len(handoff.index.documents)} indexed -> {len(handoff.test_set)} test samples"
    )
    print(f"Metrics: {paths.baseline_metrics.relative_to(paths.project_dir)}")
    print(f"Report: {paths.baseline_report.relative_to(paths.project_dir)}")
