# Phase 1 Baseline Report

## Source

<<<<<<< HEAD
- source_api: Crossref REST API
- source_query: agentic retrieval augmented generation large language model
- clean_rows: 24
=======
- source: Crossref REST API
- raw_mode: snapshot
- query: agentic retrieval augmented generation large language model
- filter: from-pub-date:2026-02-07,has-abstract:true
- raw_records: 24
- clean_records: 24
- indexed_documents: 24
- test_samples: 24
>>>>>>> 331be281d443b25248ca64ac4e9a1f582a169606
- collection: papers-baseline

## Evaluation metrics

| Metric | Baseline |
| --- | ---: |
| samples | 24 |
| retrieval_hit_rate | 1.000 |
| mean_token_f1 | 0.575 |
| judge_accuracy | 0.542 |
| mean_judge_score | 3.083 |

<<<<<<< HEAD
## How to read the metrics

- `retrieval_hit_rate`: proportion of questions whose retrieved documents contain a ground-truth document ID.
- `mean_token_f1`: lexical overlap between the reference answer and the generated answer; it is useful for factual fields but does not measure semantic equivalence perfectly.
- `judge_accuracy` and `mean_judge_score`: correctness and 1--5 score from the answer judge. If the LLM judge is unavailable, the evaluation falls back to a token-F1 heuristic; inspect `baseline_answers.json` for the verdict reasoning.
- Ragas: {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}

The baseline retrieval hit rate is 1.000. No retrieval misses were observed in this run.

=======
>>>>>>> 331be281d443b25248ca64ac4e9a1f582a169606
## Data quality

- Overall status: **PASS**
- Total rows: 24
- Failed checks: None

## Freshness

- Status: **FRESH**
- Latest / oldest published: 2026-08-01 / 2026-02-12
- Stale rows: 0 / 24
