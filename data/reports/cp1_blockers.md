# CP1 blockers trước khi chạy end-to-end

Kiểm tra gần nhất: 2026-08-06.

## Trạng thái dependency đã sẵn sàng

| Dependency | Bằng chứng | Trạng thái |
| --- | --- | --- |
| Raw snapshot | `data/raw/crossref_records.json`: 24 records | Sẵn sàng |
| Clean contract | `data/clean/papers_clean.json`: 24 records; clean gate pass | Sẵn sàng |
| Evaluation fixture | `data/eval/test_set.json`: 24 samples; ground-truth IDs thuộc clean corpus | Sẵn sàng |
| Baseline manifest | `data/embeddings/papers_embeddings.json`: `papers-baseline`, 24 documents, path `data/chroma` | Sẵn sàng |
| Chroma baseline | Collection `papers-baseline`: 24 embeddings | Sẵn sàng |

## Blocker đã đóng

### BLK-CP1-001 — Baseline entrypoint chưa được orchestration — RESOLVED

- **Trạng thái:** Đã đóng ngày 2026-08-06.
- **Owner:** Role 1 — Điều phối pipeline.
- **Bằng chứng đóng:** `src/pipelines/phase1.py::main()` đã điều phối raw → clean → index → test set → evaluate → quality/freshness → report.
- **Lệnh xác minh:** `python -m uv run python script/run_phase1.py`.
- **Kết quả:** Exit code 0; tạo đủ `baseline_metrics.json`, `baseline_answers.json`, `phase1_report.md`.

### BLK-CP1-002 — Môi trường chạy chưa khớp lockfile — RESOLVED

- **Trạng thái:** Đã đóng ngày 2026-08-06.
- **Owner:** Role 1 phối hợp Role 4 — Điều phối/RAG.
- **Bằng chứng đóng:** Đã cài `uv`, chạy `python -m uv sync --extra dev`; `.venv` dùng `sentence-transformers==5.5.1` theo lockfile.
- **Kết quả:** MiniLM load thành công; rebuild `papers-baseline`; manifest và Chroma đều có 24 documents.

## Kết quả chạy baseline

| Signal | Kết quả |
| --- | ---: |
| Raw / clean / indexed | 24 / 24 / 24 |
| Test samples / answers | 24 / 24 |
| Retrieval hit rate | 1.000 |
| Mean token F1 | 0.575 |
| Judge accuracy | 0.500 |
| Mean judge score | 3.167 |
| Data quality | PASS |
| Freshness | FRESH |

**GO:** baseline end-to-end đã chạy thành công, không phát sinh traceback. Cảnh báo Hugging Face về cache symlink trên Windows chỉ làm tăng dung lượng cache, không làm pipeline thất bại.
