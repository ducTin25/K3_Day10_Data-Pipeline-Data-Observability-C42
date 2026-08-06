from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import chromadb
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import assert_clean_contract, build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _baseline_collection_snapshot(settings) -> dict:
    client = chromadb.PersistentClient(path=str(settings.paths.chroma_dir))
    collection = client.get_collection(settings.baseline_collection_name)
    result = collection.get(include=["metadatas"])
    ids = sorted(str(metadata["paper_id"]) for metadata in result.get("metadatas", []) if metadata)
    return {"count": collection.count(), "paper_ids": ids}


def _collection_count(settings, collection_name: str) -> int:
    client = chromadb.PersistentClient(path=str(settings.paths.chroma_dir))
    return client.get_collection(collection_name).count()


def _save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def main() -> None:
    """Run corrupt → evaluate → repair → compare without mutating baseline."""
    settings = load_settings()
    paths = settings.paths
    required_baseline = (
        paths.raw_records_json,
        paths.clean_json,
        paths.embeddings_json,
        paths.eval_testset,
        paths.baseline_metrics,
        paths.baseline_answers,
    )
    missing = [path.relative_to(paths.project_dir).as_posix() for path in required_baseline if not path.exists()]
    if missing:
        raise RuntimeError(
            "Baseline artifacts are required before corruption flow. Missing: " + ", ".join(missing)
        )

    baseline_hashes = {path: _sha256(path) for path in required_baseline}
    baseline_collection = _baseline_collection_snapshot(settings)
    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_df = pd.DataFrame(read_json(paths.clean_json))
    assert_clean_contract(baseline_df)

    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    _save_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        paths.corrupted_embeddings_json,
    )
    if corrupted_index.collection_name != settings.corrupted_collection_name:
        raise RuntimeError("Corrupted index was not written to papers-corrupted.")
    corrupted_evaluation = evaluate_pipeline(
        settings,
        corrupted_index,
        paths.eval_testset,
        paths.corrupted_metrics,
        paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        paths.corrupted_freshness_report,
    )

    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
    assert_clean_contract(repaired_df)
    _save_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        paths.repaired_embeddings_json,
    )
    if repaired_index.collection_name != settings.repaired_collection_name:
        raise RuntimeError("Repaired index was not written to papers-repaired.")
    repaired_evaluation = evaluate_pipeline(
        settings,
        repaired_index,
        paths.eval_testset,
        paths.repaired_metrics,
        paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        paths.repaired_freshness_report,
    )

    corruption_log = read_json(paths.corruption_log)
    affected_ids = sorted({
        str(change["paper_id"])
        for step in corruption_log.get("steps", [])
        for change in step.get("changes", [])
    })
    raw_ids = {record.paper_id for record in raw_records}
    corrupted_counts = corrupted_df["paper_id"].astype(str).value_counts().to_dict()
    repaired_counts = repaired_df["paper_id"].astype(str).value_counts().to_dict()
    lineage_evidence = [
        {
            "paper_id": paper_id,
            "raw_source": paths.raw_records_json.relative_to(paths.project_dir).as_posix(),
            "present_in_raw": paper_id in raw_ids,
            "corrupted_row_count": int(corrupted_counts.get(paper_id, 0)),
            "repaired_row_count": int(repaired_counts.get(paper_id, 0)),
            "restored_from_raw": paper_id in raw_ids and repaired_counts.get(paper_id, 0) == 1,
        }
        for paper_id in affected_ids
    ]

    answers_by_state = {
        "baseline": {item["id"]: item for item in read_json(paths.baseline_answers)},
        "corrupted": {item["id"]: item for item in read_json(paths.corrupted_answers)},
        "repaired": {item["id"]: item for item in read_json(paths.repaired_answers)},
    }
    common_ids = sorted(set.intersection(*(set(items) for items in answers_by_state.values())))
    case_id = next(
        (sample_id for sample_id in common_ids if answers_by_state["baseline"][sample_id].get("retrieval_hit") and not answers_by_state["corrupted"][sample_id].get("retrieval_hit") and answers_by_state["repaired"][sample_id].get("retrieval_hit")),
        common_ids[0],
    )
    case_evidence = {
        "sample_id": case_id,
        "question": answers_by_state["baseline"][case_id]["question"],
        "ground_truth_doc_ids": answers_by_state["baseline"][case_id]["ground_truth_doc_ids"],
        "states": {
            state: {
                "collection": collection,
                "retrieval_hit": answers_by_state[state][case_id]["retrieval_hit"],
                "retrieved_doc_ids": answers_by_state[state][case_id]["retrieved_doc_ids"],
                "answer": answers_by_state[state][case_id]["answer"],
            }
            for state, collection in (
                ("baseline", settings.baseline_collection_name),
                ("corrupted", settings.corrupted_collection_name),
                ("repaired", settings.repaired_collection_name),
            )
        },
    }

    changed_baseline = [
        path.relative_to(paths.project_dir).as_posix()
        for path, digest in baseline_hashes.items()
        if _sha256(path) != digest
    ]
    if changed_baseline:
        raise RuntimeError("Corruption flow mutated baseline artifacts: " + ", ".join(changed_baseline))
    post_baseline_collection = _baseline_collection_snapshot(settings)
    if post_baseline_collection != baseline_collection:
        raise RuntimeError("Corruption flow mutated the papers-baseline collection.")
    if {
        corrupted_index.collection_name,
        repaired_index.collection_name,
        settings.baseline_collection_name,
    } != {
        settings.corrupted_collection_name,
        settings.repaired_collection_name,
        settings.baseline_collection_name,
    }:
        raise RuntimeError("Baseline/corrupted/repaired collection names are not isolated.")

    write_json(
        paths.corruption_comparison_audit,
        {
            "baseline_artifacts_unchanged": True,
            "baseline_collection_unchanged": True,
            "fixed_test_set": paths.eval_testset.relative_to(paths.project_dir).as_posix(),
            "collections": {
                settings.baseline_collection_name: _collection_count(settings, settings.baseline_collection_name),
                settings.corrupted_collection_name: _collection_count(settings, settings.corrupted_collection_name),
                settings.repaired_collection_name: _collection_count(settings, settings.repaired_collection_name),
            },
            "manifests": {
                "baseline": paths.embeddings_json.relative_to(paths.project_dir).as_posix(),
                "corrupted": paths.corrupted_embeddings_json.relative_to(paths.project_dir).as_posix(),
                "repaired": paths.repaired_embeddings_json.relative_to(paths.project_dir).as_posix(),
            },
            "metrics": {
                "baseline": paths.baseline_metrics.relative_to(paths.project_dir).as_posix(),
                "corrupted": paths.corrupted_metrics.relative_to(paths.project_dir).as_posix(),
                "repaired": paths.repaired_metrics.relative_to(paths.project_dir).as_posix(),
            },
            "lineage_evidence": lineage_evidence,
            "representative_case": case_evidence,
        },
    )

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_evaluation.summary,
        repaired_evaluation.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
        lineage_evidence,
        case_evidence,
    )
    print(
        "Corruption flow complete: "
        f"baseline={len(baseline_df)}, corrupted={len(corrupted_df)}, repaired={len(repaired_df)}"
    )
    print(
        "Collections: "
        f"{settings.baseline_collection_name}, {corrupted_index.collection_name}, "
        f"{repaired_index.collection_name}"
    )
    print(f"Report: {paths.comparison_report.relative_to(paths.project_dir)}")
