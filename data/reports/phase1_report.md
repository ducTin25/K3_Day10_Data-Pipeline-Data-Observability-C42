# Phase 1 Baseline Report

## Source

- source: Crossref REST API
- raw_mode: snapshot
- query: agentic retrieval augmented generation large language model
- filter: from-pub-date:2026-02-07,has-abstract:true
- raw_records: 24
- clean_records: 24
- indexed_documents: 24
- test_samples: 24
- collection: papers-baseline

## Evaluation metrics

| Metric | Baseline |
| --- | ---: |
| samples | 24 |
| retrieval_hit_rate | 1.000 |
| mean_token_f1 | 0.575 |
| judge_accuracy | 0.542 |
| mean_judge_score | 3.083 |

## Data quality

- Overall status: **PASS**
- Total rows: 24
- Failed checks: None

## Freshness

- Status: **FRESH**
- Latest / oldest published: 2026-08-01 / 2026-02-12
- Stale rows: 0 / 24
