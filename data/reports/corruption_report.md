# Data Corruption and Repair Report

## Evaluation comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| samples | 24 | 24 | 24 |
| retrieval_hit_rate | 1.000 | 0.667 | 1.000 |
| mean_token_f1 | 0.575 | 0.370 | 0.575 |
| judge_accuracy | 0.500 | 0.375 | 0.500 |
| mean_judge_score | 3.167 | 2.792 | 3.167 |

## Measured impact and recovery

- retrieval_hit_rate: baseline → corrupted -0.333; corrupted → repaired +0.333
- mean_token_f1: baseline → corrupted -0.205; corrupted → repaired +0.205
- judge_accuracy: baseline → corrupted -0.125; corrupted → repaired +0.125
- mean_judge_score: baseline → corrupted -0.375; corrupted → repaired +0.375

## Observability comparison

| State | Quality | Freshness | Stale rows |
| --- | --- | --- | ---: |
| Corrupted | FAIL | STALE / INCOMPLETE | 1 |
| Repaired | PASS | FRESH | 0 |

## Raw-to-repair lineage

- 7/7 document IDs affected by corruption are present in the frozen raw snapshot.
- 7/7 IDs are restored exactly once in repaired data, including both records dropped from corrupted data.
- Detailed evidence: `data/quality/corruption_comparison_audit.json`.

## Representative retrieval case

Question `eval-009` targets ground-truth DOI `10.1111/exsy.70341`, one of the two dropped records.

| State | Collection queried | Retrieval hit | Ground-truth retrieved | Observed result |
| --- | --- | --- | --- | --- |
| Baseline | `papers-baseline` | Yes | Yes | Correct paper summary returned |
| Corrupted | `papers-corrupted` | No | No | Answer came from a different retrieved document |
| Repaired | `papers-repaired` | Yes | Yes | Correct paper summary returned again |

This case proves the evaluator queried the state-specific collection and shows a concrete hit → miss → recovered-hit sequence.

## Interpretation limits

- All corruption scenarios run together; the aggregate metric delta cannot be attributed to one scenario without ablation.
- Judge metrics may vary between LLM calls; this comparison uses artifacts from the same completed run.
- Ragas remains disabled unless `RUN_RAGAS=1`.
