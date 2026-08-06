# RAG & agent handoff — Vai trò 4 (Nhóm 5)

Phạm vi: `src/retrieval/` · `data/embeddings/` (MiniLM, Chroma, search, lookup)

## CHECKPOINT 0 — Contract & chuẩn bị

- `src/retrieval/` (index.py, embeddings.py, agent.py, qa.py) đã implement sẵn, không có `TODO(student)`. Việc của vai trò này ở CP0/CP1 là đọc contract, chốt cấu hình và xác nhận dữ liệu đầu vào, không phải viết code mới.
- Embedding model (cố định trong `src/core/config.py`, không đọc từ `.env`): `sentence-transformers/all-MiniLM-L6-v2`
- Collection naming (tự suy ra theo `embeddings_output_path`, xem `LocalEmbeddingIndex._derive_collection_name`):
  - baseline -> `papers-baseline`
  - corrupted -> `papers-corrupted`
  - repaired -> `papers-repaired`
- Metadata tối thiểu bắt buộc trong DataFrame clean (xem `LocalEmbeddingIndex._build_documents`) — **contract với người phụ trách cleaning**:
  `paper_id, title, text_for_embedding, published, authors_joined, categories_joined, summary, abs_url, pdf_url`
- Smoke query chuẩn bị sẵn cho CP2:
  - Semantic: "What are recent papers about retrieval augmented generation for agents?", "How do LLM agents use retrieval tools?"
  - Exact lookup: theo `paper_id` (DOI) hoặc title chính xác
  - Agent factual: "Who authored '<title>'?", "When was '<title>' published?"

## CHECKPOINT 1 — Xác minh trên dữ liệu clean thật

Nguồn: `data/clean/papers_clean.csv` / `papers_clean.json` (24 records, do Vai trò 3 bàn giao).

- Đủ cả 9 cột theo contract CP0.
- `paper_id` unique: 24/24.
- `text_for_embedding`: không rỗng, không trùng lặp, độ dài 1088–2805 ký tự (trung bình ~1925), format nhất quán `Title / Authors / Summary`.
- `categories_joined` rỗng cho toàn bộ 24/24 record (Crossref không trả `categories` cho query này). Đây là tín hiệu data quality thật (đã ghi nhận ở `data/raw/crossref_handoff.md`: "Empty categories are valid optional source metadata"), không phải lỗi cleaning — không chặn việc build index, nhưng Observability nên ghi nhận trong quality report.
- Config path xác nhận khớp `src/core/config.py`:
  - `clean_csv` -> `data/clean/papers_clean.csv` (tồn tại)
  - `embeddings_json` -> `data/embeddings/papers_embeddings.json`
  - `chroma_dir` -> `data/chroma/`

### Vấn đề phát hiện — cần xử lý trước khi build baseline chính thức ở CP2

`data/embeddings/papers_embeddings.json` hiện tại (commit "Role 3 checkpoint 1") **không dùng được**:

- Chỉ index **1/24 document** thay vì đủ 24 — build dở dang/thử nghiệm, không phải bản đầy đủ.
- `persist_path` bị ghi cứng theo đường dẫn máy khác (`C:\Users\Admin\Downloads\CodeLab10\...`), không khớp máy hiện tại -> `LocalEmbeddingIndex.load()` sẽ lỗi trên máy khác trong nhóm.

**Hành động ở CP2:** rebuild lại bằng `LocalEmbeddingIndex.build()` (không dùng `.load()`) từ đủ 24 record trong `papers_clean.csv`, để `persist_path`/`collection_name` ghi đúng theo máy chạy thật.

## Trạng thái

- [x] CP0: đọc contract, chốt embedding model/collection naming/metadata, chuẩn bị smoke query
- [x] CP1: xác minh schema + chất lượng `text_for_embedding` trên dữ liệu clean thật, phát hiện và ghi nhận embeddings manifest lỗi cần rebuild
- [ ] CP2: build `papers-baseline` đầy đủ, chạy smoke test semantic search + lookup + agent (việc tiếp theo)
