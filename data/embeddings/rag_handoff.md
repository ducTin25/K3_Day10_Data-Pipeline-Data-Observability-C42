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

## CHECKPOINT 3 — Xác nhận baseline, demo search/lookup, kiểm tra agent không vượt corpus

Việc riêng của vai trò rag ở CP3 không phụ thuộc ai (tách biệt với pass-criteria chung của cả checkpoint — xem phần "Dependency" bên dưới).

1. **Xác nhận `papers-baseline` khớp clean dataset:** so `paper_id` set giữa `papers_clean.csv` (24 dòng) và `documents` trong `papers_embeddings.json` — khớp 100%. `embedding_model` và `collection_name` đúng theo `settings`.
2. **Demo semantic search + exact lookup** (dùng cho team):
   - Semantic: "What are recent papers about retrieval augmented generation for agents?" -> top1 `10.63646/kpqm1958` "The Age of Autonomous Agents..." (score 0.60)
   - Exact lookup: `paper_id=10.1111/exsy.70341` -> tìm đúng title/authors/published.
3. **Kiểm tra agent không vượt corpus:**
   - Câu hỏi trong corpus ("Who authored 'JADE-Plus...'?") -> agent trả lời đúng 5/5 tác giả, dùng tool.
   - Câu hỏi ngoài corpus ("What is the capital city of France?") -> **phát hiện lỗi**: agent trả lời thẳng "Paris" bằng kiến thức nền LLM, không gọi tool, không từ chối. Vi phạm system prompt cũ ("Use tools before answering factual questions" — không đủ chặt, LLM tự quyết câu hỏi không cần tool).

   **Đã sửa** `src/retrieval/agent.py` system_prompt: bắt buộc gọi tool cho MỌI câu hỏi kể cả câu có vẻ ngoài corpus, chỉ dùng thông tin tool trả về, từ chối rõ ràng nếu tool không hỗ trợ. Re-test sau khi sửa: agent trả lời đúng "The indexed corpus does not cover the question about the capital city of France." — đạt.

### Dependency của cả CHECKPOINT 3 (không chỉ việc của rag)

Pass-criteria CP3 cấp team (`baseline_metrics.json`, `answers`, quality/freshness, `phase1_report.md`) phụ thuộc vào Vai trò 1 (lead) implement + chạy `uv run python script/run_phase1.py`. Tại thời điểm ghi nhận, `src/pipelines/phase1.py::main()` **vẫn còn `NotImplementedError`** — 3 việc riêng của rag ở trên không bị chặn, nhưng checkpoint chưa "xong" ở cấp team. Sau khi lead chạy `phase1.py` (có thể tự rebuild lại index), cần re-run script xác nhận CP2/CP3 để đảm bảo `papers-baseline` vẫn khớp.

## CHECKPOINT 4 — Nghỉ 15 phút; lưu ví dụ query baseline để đối chiếu

Không phụ thuộc ai. Chốt lại bộ ví dụ baseline dùng chung cho CP5 (corrupted) và CP6 (repaired) — chạy lại đúng các query này trên `papers-corrupted`/`papers-repaired` sau này để so sánh, không đổi query giữa các trạng thái.

**Semantic search** — Query: `"What are recent papers about retrieval augmented generation for agents?"`

| Rank | score | paper_id | title |
|---|---|---|---|
| 1 | 0.6037 | `10.63646/kpqm1958` | The Age of Autonomous Agents: A Bibliometric Review of Agentic AI Architectures... |
| 2 | 0.5383 | `10.32473/flairs.39.1.141782` | An Exploratory Study of Agentic Retrieval Augmented Generation for Mental Health... |
| 3 | 0.5184 | `10.70121/001c.158711` | The Role of Retrieval-Augmented Generation in Improving Factual Accuracy for Medical... |

**Exact lookup** — `paper_id = "10.1111/exsy.70341"` -> found, title "Hi‐RAG: A Hierarchical Retrieval‐Augmented Generation Framework...", authors "Wei Tian, Yuhao Zhou", published `2026-08-01`.

**Agent (trong corpus)** — Q: `"Who authored the paper 'JADE-Plus...'?"` -> đúng đủ 5 tác giả, khớp `ground_truth` của `eval-002` trong `test_set.json`.

**Agent (ngoài corpus, guard)** — Q: `"What is the capital city of France?"` -> `"The indexed corpus does not cover the question about the capital city of France."` (đúng sau khi sửa system prompt ở CP3).

**Baseline metrics tham chiếu** (`data/results/baseline_metrics.json`, sau lần evaluator chạy cuối): `retrieval_hit_rate=1.0`, `mean_token_f1=0.575`, `judge_accuracy=0.542`, `mean_judge_score=3.08`.

Nếu ở CP5/CP6 chạy lại đúng các query trên mà `paper_id`/score đổi khác hẳn, hoặc agent bắt đầu bịa đáp án — đó là bằng chứng trực tiếp cho thấy corruption ảnh hưởng tới RAG.

## CHECKPOINT 5 — Build `papers-corrupted`, đo impact so với baseline

Nguồn: `data/clean/papers_clean_corrupted.csv` (23 dòng, do Vai trò 3 bàn giao — xem `data/results/corruption_log.json`: drop 2 record mới nhất, blank summary 2, inject noise 2, truncate title 2, sửa ngày cũ 1, thêm 1 duplicate; 24 -> 23 dòng).

1. **Build `papers-corrupted` riêng** — path/collection tách biệt hoàn toàn với baseline (`corrupted_embeddings_json`, không ghi đè `embeddings_json`). 23/23 document, `collection_name=papers-corrupted` đúng như config.

2. **Chạy lại ĐÚNG query baseline (CP4) trên `papers-corrupted`** — quan sát retrieval đổi:
   - Semantic search cùng query: rank #2 **đổi hẳn** — một paper mới xuất hiện (`10.2196/preprints.106157`, score 0.558) chen vào top-3, đẩy `10.70121/001c.158711` (baseline #3) ra khỏi top-3. Paper mới này chính là 1 trong 2 record bị `inject_noise` theo corruption log — noise làm tăng điểm tương đồng giả tạo, gây lệch retrieval ranking. **Đây là bằng chứng cụ thể corruption ảnh hưởng RAG.**
   - Exact lookup `paper_id=10.1111/exsy.70341` (paper bị `drop_latest_records`) -> `found=False` đúng như kỳ vọng — record biến mất khỏi corpus sau corruption.
   - Exact lookup `paper_id=10.1007/s10278-026-02086-9` (JADE-Plus, bị `blank_summary` + `add_duplicate_rows`) -> vẫn tìm thấy (title/authors còn nguyên), nhưng summary trong `text_for_embedding` đã rỗng — câu hỏi dạng "What does the paper discuss?" (loại `summary` trong test set) sẽ suy giảm chất lượng câu trả lời dù record vẫn tồn tại.

3. **Kiểm tra `papers-baseline` không bị mutate** — reload lại baseline sau khi build corrupted:
   - Vẫn đủ 24/24 document, `collection_name=papers-baseline`.
   - Lookup `10.1111/exsy.70341` trên baseline vẫn `found=True` (paper này chỉ mất trên corrupted, baseline không đổi).
   - Semantic search baseline chạy lại cho đúng top-3 y hệt CP4 (`10.63646/kpqm1958, 10.32473/flairs.39.1.141782, 10.70121/001c.158711`).
   - **Đạt** — build corrupted không hề đụng tới path/collection baseline.

Pass criteria CP5 cho vai trò rag: **đạt** — `papers-corrupted` build riêng, có bằng chứng retrieval thay đổi (rank #2 chen vào do noise, 1 record biến mất do drop), baseline nguyên vẹn không bị ghi đè.

## Trạng thái

- [x] CP0: đọc contract, chốt embedding model/collection naming/metadata, chuẩn bị smoke query
- [x] CP1: xác minh schema + chất lượng `text_for_embedding` trên dữ liệu clean thật, phát hiện và ghi nhận embeddings manifest lỗi cần rebuild
- [x] CP2: build `papers-baseline` đầy đủ (24/24 doc), smoke test semantic search + lookup + agent đều pass
- [x] CP3: xác nhận baseline khớp clean data, demo search/lookup, phát hiện + sửa lỗi agent trả lời ngoài corpus. Lead đã chạy xong `phase1.py` end-to-end: `data/results/baseline_metrics.json`, `baseline_answers.json` và `data/reports/phase1_report.md` đã tồn tại.
- [x] CP4: nghỉ; đã chốt bộ ví dụ query baseline (semantic/lookup/agent) làm tham chiếu cho CP5-CP6
- [x] CP5: build `papers-corrupted` (23/23 doc) từ dữ liệu Vai trò 3 bàn giao, chứng minh được retrieval thay đổi (noise chen top-3, record bị drop mất khỏi lookup), xác nhận baseline không bị mutate
- [ ] CP6+: build `papers-repaired` sau khi Vai trò 3 repair từ raw, chạy lại đúng bộ query để đo mức phục hồi
