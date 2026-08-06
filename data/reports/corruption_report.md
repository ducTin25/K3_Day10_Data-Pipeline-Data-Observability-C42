# Data Corruption and Repair Report

## Evaluation comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| samples | 24 | 24 | 24 |
| retrieval_hit_rate | 1.000 | 0.667 | 1.000 |
| mean_token_f1 | 0.575 | 0.370 | 0.575 |
| judge_accuracy | 0.542 | 0.375 | 0.500 |
| mean_judge_score | 3.083 | 2.792 | 3.167 |

## Measured impact and recovery

- retrieval_hit_rate: baseline → corrupted -0.333; corrupted → repaired +0.333
- mean_token_f1: baseline → corrupted -0.205; corrupted → repaired +0.205
- judge_accuracy: baseline → corrupted -0.167; corrupted → repaired +0.125
- mean_judge_score: baseline → corrupted -0.292; corrupted → repaired +0.375

## Observability comparison

| State | Quality | Freshness | Stale rows |
| --- | --- | --- | ---: |
| Corrupted | FAIL | STALE / INCOMPLETE | 1 |
| Repaired | PASS | FRESH | 0 |
