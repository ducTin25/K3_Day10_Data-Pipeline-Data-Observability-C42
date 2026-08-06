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

## CHECKPOINT 2 — Build baseline thật, smoke test search/lookup/agent

Đã rebuild `papers-baseline` bằng `LocalEmbeddingIndex.build()` từ đủ 24 record clean (thay cho manifest lỗi 1/24 doc trước đó).

- `data/embeddings/papers_embeddings.json`: `collection_name=papers-baseline`, `embedding_model=sentence-transformers/all-MiniLM-L6-v2`, `persist_path` đúng máy hiện tại, **24/24 document**.
- Dọn 2 folder Chroma mồ côi (`cb674a12-...` của bản build lỗi cũ, `0e31576b-...` của lần build nháp) — đã xác nhận qua bảng `segments` trong `chroma.sqlite3` rằng folder đang thật sự dùng là `6e3c438e-8b89-45c8-ad68-742e914cc6df` trước khi xoá.

**Test semantic_search** (2 query đã chuẩn bị từ CP0), trả về kết quả có điểm số và nguồn hợp lý:
- "What are recent papers about retrieval augmented generation for agents?" -> top1 `10.63646/kpqm1958` (score 0.60)
- "How do LLM agents use retrieval tools?" -> top1 `10.70121/001c.158711` (score 0.48)

**Test lookup** (exact match): theo `paper_id` -> tìm thấy; theo title chính xác -> tìm thấy; giá trị không tồn tại -> trả `None` đúng như kỳ vọng.

**Test agent** (dùng câu hỏi thật `eval-002` từ `data/eval/test_set.json`, loại `authors`):
- Câu hỏi: "Who authored the paper 'JADE-Plus...'?"
- Ground truth: `Soroush Baseri Saadi, Jonas Ver Berne, Rocharles Cavalcante Fontenele, Peter Claes, Reinhilde Jacobs`
- Agent trả lời đúng đủ cả 5 tác giả, đã gọi tool (`lookup_paper`/`semantic_search_papers`) trước khi trả lời theo đúng system prompt, không bịa ngoài corpus.

Pass criteria CP2 cho vai trò rag: **đạt** — embedding manifest + collection baseline tồn tại và đúng; semantic search, exact lookup, agent đều trả kết quả có nguồn kiểm chứng được.

### Merge conflict sau `git pull` — đã xử lý

Sau khi build lần đầu, `git pull` mang về 6 commit từ team (bao gồm bản vá `src/retrieval/index.py`: `persist_path` giờ lưu **tương đối** thay vì tuyệt đối, thêm `assert_clean_contract(df)` trước khi build — đúng fix cho vấn đề đã ghi ở CP1) và tạo conflict trên 3 artifact sinh ra từ code:

- `data/chroma/cb674a12-.../data_level0.bin, length.bin` (modify/delete)
- `data/chroma/chroma.sqlite3` (binary, không auto-merge được)
- `data/embeddings/papers_embeddings.json` (content, nhiều hunk `<<<<<<<`)

Không hand-merge JSON/binary sinh ra từ code — xoá sạch toàn bộ `data/chroma/` và `papers_embeddings.json` cũ (kể cả bản build đầu của CP2), rồi **rebuild lại từ đầu** bằng `LocalEmbeddingIndex.build()` với code `index.py` đã merge. Kết quả: `persist_path` giờ là `data/chroma` (tương đối, portable giữa các máy trong nhóm), 24/24 document, đã re-run đủ semantic search/lookup/agent smoke test ở trên và đều pass. Dọn thêm 1 folder Chroma mồ côi phát sinh giữa 2 lần build (xác nhận qua bảng `segments` trước khi xoá). Đã `git commit` hoàn tất merge (chưa `push`).

## Trạng thái

- [x] CP0: đọc contract, chốt embedding model/collection naming/metadata, chuẩn bị smoke query
- [x] CP1: xác minh schema + chất lượng `text_for_embedding` trên dữ liệu clean thật, phát hiện và ghi nhận embeddings manifest lỗi cần rebuild
- [x] CP2: build `papers-baseline` đầy đủ (24/24 doc), smoke test semantic search + lookup + agent đều pass
- [ ] CP3+: chờ baseline pipeline (`phase1.py`, do lead phụ trách) chạy end-to-end để có `baseline_metrics.json` chính thức
