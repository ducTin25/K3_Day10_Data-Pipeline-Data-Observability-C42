from __future__ import annotations

from typing import Any

from core.utils import write_text


def _format(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def _metrics_table(*states: tuple[str, dict[str, Any]]) -> str:
    lines = [f"| Metric | {' | '.join(name for name, _ in states)} |", f"| --- | {' | '.join('---:' for _ in states)} |"]
    for metric in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        lines.append(f"| {metric} | {' | '.join(_format(values.get(metric, 'n/a')) for _, values in states)} |")
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    source = "\n".join(f"- {key}: {_format(value)}" for key, value in source_summary.items()) or "- No source metadata supplied."
    failures = ", ".join(name for name, check in quality.get("checks", {}).items() if not check.get("passed")) or "None"
    write_text(report_path, f"""# Phase 1 Baseline Report

## Source

{source}

## Evaluation metrics

{_metrics_table(('Baseline', metrics))}

## How to read the metrics

- `retrieval_hit_rate`: proportion of questions whose retrieved documents contain a ground-truth document ID.
- `mean_token_f1`: lexical overlap between the reference answer and the generated answer; it is useful for factual fields but does not measure semantic equivalence perfectly.
- `judge_accuracy` and `mean_judge_score`: correctness and 1--5 score from the answer judge. If the LLM judge is unavailable, the evaluation falls back to a token-F1 heuristic; inspect `baseline_answers.json` for the verdict reasoning.
- Ragas: {_format(metrics.get('ragas', 'n/a'))}

The baseline retrieval hit rate is {_format(metrics.get('retrieval_hit_rate', 'n/a'))}. {'No retrieval misses were observed in this run.' if metrics.get('retrieval_hit_rate') == 1.0 else 'Review retrieval misses in `baseline_answers.json` before comparing later runs.'}

## Data quality

- Overall status: **{'PASS' if quality.get('passed') else 'FAIL'}**
- Total rows: {quality.get('total_rows', 'n/a')}
- Failed checks: {failures}

## Freshness

- Status: **{'FRESH' if freshness.get('is_fresh') else 'STALE / INCOMPLETE'}**
- Latest / oldest published: {freshness.get('latest_published', 'n/a')} / {freshness.get('oldest_published', 'n/a')}
- Stale rows: {freshness.get('stale_rows', 'n/a')} / {freshness.get('total_rows', 'n/a')}
""")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    def delta(metric: str, before: dict[str, Any], after: dict[str, Any]) -> str:
        try:
            return f"{float(after[metric]) - float(before[metric]):+.3f}"
        except (KeyError, TypeError, ValueError):
            return "n/a"

    impact = "\n".join(
        f"- {metric}: baseline → corrupted {delta(metric, baseline_metrics, corrupted_metrics)}; corrupted → repaired {delta(metric, corrupted_metrics, repaired_metrics)}"
        for metric in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    )
    write_text(report_path, f"""# Data Corruption and Repair Report

## Evaluation comparison

{_metrics_table(('Baseline', baseline_metrics), ('Corrupted', corrupted_metrics), ('Repaired', repaired_metrics))}

## Measured impact and recovery

{impact}

## Observability comparison

| State | Quality | Freshness | Stale rows |
| --- | --- | --- | ---: |
| Corrupted | {'PASS' if corrupted_quality.get('passed') else 'FAIL'} | {'FRESH' if corrupted_freshness.get('is_fresh') else 'STALE / INCOMPLETE'} | {corrupted_freshness.get('stale_rows', 'n/a')} |
| Repaired | {'PASS' if repaired_quality.get('passed') else 'FAIL'} | {'FRESH' if repaired_freshness.get('is_fresh') else 'STALE / INCOMPLETE'} | {repaired_freshness.get('stale_rows', 'n/a')} |
""")
