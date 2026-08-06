# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Anh Thư             |
| MSSV               | 2A202601611                     |
| Khóa/Lớp         | K3              |
| Tên nhóm         | C42    |
| Vai trò chính    | Vai trò 4 — RAG & agent (MiniLM, Chroma, search, lookup)                 |
| Repository         | https://github.com/ducTin25/K3_Day10_Data-Pipeline-Data-Observability-C42 |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| RAG index (MiniLM + Chroma) | `src/retrieval/index.py`, `embeddings.py` | DataFrame clean (`papers_clean*.csv`) | `data/embeddings/papers_embeddings*.json` + Chroma collection `papers-baseline`/`papers-corrupted`/`papers-repaired` | Hoàn thành |
| Search & lookup | `LocalEmbeddingIndex.search()`, `.lookup()` | Query text / paper_id-title | `SearchResult` có `paper_id`, `score`, `content`, `metadata` | Hoàn thành |
| Agent RAG | `src/retrieval/agent.py` (`build_agent`, `run_agent_question`) | Câu hỏi người dùng + index đã build | Câu trả lời có trích dẫn từ tool, từ chối nếu ngoài corpus | Hoàn thành |

Chỉ nhận ownership cho phần trực tiếp thực hiện: build/verify 3 collection (baseline/corrupted/repaired), demo search/lookup, kiểm tra và sửa hành vi agent. Không nhận ownership cho `cleaning.py`, `corruption.py`, `repair.py`, `phase1.py` — các file này do thành viên khác phụ trách, tôi chỉ đọc để dùng đúng output của họ.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Phát hiện + sửa lỗi agent trả lời ngoài corpus | `src/retrieval/agent.py` (code chung, không thuộc riêng ai) | Sửa `system_prompt`, agent không còn bịa đáp án ngoài corpus |
| Resolve merge conflict lặp lại nhiều lần (`data/chroma/`, `data/embeddings/*.json`) | Toàn nhóm — repo dùng chung, 5 người push gần như đồng thời | Rebuild lại index sạch sau mỗi lần `git pull` bị conflict thay vì hand-merge file binary/JSON sinh ra từ code |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Build `papers-baseline` từ clean data đầy đủ | `data/embeddings/papers_embeddings.json` | 24/24 document, `persist_path` tương đối, đúng `collection_name` | Script rebuild, so `paper_id` set giữa clean CSV và manifest |
| Build `papers-corrupted` riêng | `data/embeddings/papers_embeddings_corrupted.json` | 23/23 document, path/collection tách biệt baseline | So kết quả search/lookup với baseline (CP4 reference) |
| Build `papers-repaired` riêng | `data/embeddings/papers_embeddings_repaired.json` | 24/24 document | So kết quả search/lookup, xác nhận khớp lại baseline |
| Demo semantic search + exact lookup | `LocalEmbeddingIndex.search/.lookup` | Kết quả có `paper_id`, `score`, nguồn kiểm chứng được | Chạy trực tiếp trên cả 3 collection, log kết quả trong `data/embeddings/rag_handoff.md` |
| Kiểm tra + sửa agent không vượt corpus | `src/retrieval/agent.py` | Agent từ chối đúng khi câu hỏi ngoài corpus | Test trước/sau khi sửa `system_prompt` |

Một output cụ thể: `data/embeddings/rag_handoff.md` — nhật ký đầy đủ từ CP0 đến CP6 của vai trò RAG, gồm quyết định cấu hình (embedding model, collection naming, metadata contract), kết quả kiểm thử từng checkpoint, và bảng so sánh retrieval baseline/corrupted/repaired dùng chung một bộ query cố định.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần RAG cần biến dữ liệu đã clean thành vector index để phục vụ semantic search, exact lookup và agent trả lời có trích dẫn nguồn. Vì lab yêu cầu so sánh baseline/corrupted/repaired trên cùng một kiến trúc, index phải tái lập được độc lập cho cả ba trạng thái mà không ghi đè lẫn nhau.

### Cách triển khai

`src/retrieval/index.py` đã có sẵn (không phải phần tôi code mới), dùng `sentence-transformers/all-MiniLM-L6-v2` để embed `text_for_embedding`, lưu vào ChromaDB persistent client (cosine similarity). Ba trạng thái dùng chung một `persist_path` (`data/chroma/`) nhưng tách biệt hoàn toàn qua `collection_name` (`papers-baseline` / `papers-corrupted` / `papers-repaired`), tự suy ra từ đường dẫn file manifest đầu ra. Việc của tôi là xác nhận đúng contract dữ liệu đầu vào (9 cột bắt buộc trong DataFrame clean), build lần lượt cả ba collection từ đúng file clean tương ứng, và kiểm chứng bằng truy vấn thật thay vì chỉ tin script chạy xong không lỗi.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | DataFrame clean với 9 cột: `paper_id, title, text_for_embedding, published, authors_joined, categories_joined, summary, abs_url, pdf_url` |
| Output                         | Chroma collection + `data/embeddings/papers_embeddings*.json` (`backend`, `embedding_model`, `persist_path`, `collection_name`, `documents`) |
| Module phụ thuộc             | `src/ingestion/cleaning.py` (baseline), `corruption.py` (corrupted), `repair.py` (repaired) — cung cấp file clean CSV đầu vào |
| Module sử dụng output        | `src/retrieval/agent.py`, `src/retrieval/qa.py`, `src/evaluation` (evaluator dùng index để tính `retrieval_hit_rate` v.v.) |
| Điều kiện lỗi cần xử lý | Manifest cũ chỉ index 1/24 document (build dở dang); `persist_path` tuyệt đối không portable giữa các máy trong nhóm |

### Cách xác minh

```bash
uv run python cp2_rag_smoke_test.py   # build + search + lookup + agent trên baseline
uv run python cp5_rag_corrupted.py    # build papers-corrupted, so sanh voi baseline
uv run python cp6_rag_repaired.py     # build papers-repaired, so sanh voi corrupted
```

- **Kết quả mong đợi:** cả 3 collection build đủ số document đúng với clean data tương ứng; search/lookup trả kết quả có nguồn; agent dùng tool trước khi trả lời.
- **Kết quả thực tế:** baseline 24/24, corrupted 23/23, repaired 24/24 — đúng như clean data đầu vào. Semantic search trên corrupted bị lệch top-3 do noise injection, phục hồi đúng thứ tự baseline sau repair.
- **Artifact/log:** `data/embeddings/papers_embeddings.json`, `papers_embeddings_corrupted.json`, `papers_embeddings_repaired.json`, chi tiết log trong `data/embeddings/rag_handoff.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Ở CP3, khi test agent với câu hỏi ngoài phạm vi corpus ("What is the capital city of France?"), agent trả lời thẳng "Paris" bằng kiến thức nền của LLM thay vì dùng tool hoặc từ chối — vi phạm yêu cầu "agent không vượt corpus" của lab.
- **Các phương án đã cân nhắc:**
  1. Sửa `system_prompt` trong `agent.py`: bắt buộc gọi tool cho mọi câu hỏi, chỉ dùng thông tin tool trả về, từ chối rõ ràng nếu tool không hỗ trợ.
  2. Thêm lớp hậu kiểm (post-hoc filter) bên ngoài agent để chặn câu trả lời không trích dẫn `paper_id` từ tool.
- **Phương án đã chọn:** (1) — sửa `system_prompt`.
- **Lý do:** Phương án 1 sửa đúng gốc vấn đề (agent tự quyết không cần tool), chỉ đổi 1 đoạn text, không thêm logic/dependency mới, không đổi contract tool hay schema câu trả lời mà `qa.py`/evaluator đang phụ thuộc. Phương án 2 phức tạp hơn và có rủi ro false positive (chặn nhầm câu trả lời hợp lệ có trích dẫn gián tiếp).
- **Bằng chứng quyết định phù hợp:** Test lại đúng câu hỏi cũ sau khi sửa — agent trả lời: *"The indexed corpus does not cover the question about the capital city of France."* thay vì "Paris". Câu hỏi trong corpus (tác giả JADE-Plus) vẫn trả lời đúng, không bị ảnh hưởng bởi thay đổi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `data/embeddings/papers_embeddings.json` (commit trước đó của thành viên khác) chỉ chứa `1` document trong mảng `documents` thay vì `24`, và trường `persist_path` là đường dẫn tuyệt đối trên máy khác (dạng `C:\Users\<user khác>\Downloads\CodeLab10\...`), không tồn tại trên máy của tôi.
- **Lệnh hoặc bước tái hiện:** Đọc file `data/embeddings/papers_embeddings.json`, so `len(payload["documents"])` với số dòng thật trong `data/clean/papers_clean.csv` (24) — lệch nhau; gọi `LocalEmbeddingIndex.load()` với `persist_path` đó sẽ lỗi vì thư mục không tồn tại trên máy này.
- **Nguyên nhân gốc:** Có người đã chạy thử `LocalEmbeddingIndex.build()` sớm, trên dữ liệu clean chưa hoàn chỉnh (hoặc dừng giữa chừng), rồi commit thẳng manifest đó lên repo dùng chung; đồng thời code cũ của `build()` lưu `persist_path` dạng tuyệt đối nên không portable giữa các máy trong nhóm.
- **Cách xử lý:** Gọi lại `LocalEmbeddingIndex.build()` từ đủ 24 dòng trong `papers_clean.csv` để tạo manifest đúng. Về sau team cũng tự vá `index.py` để lưu `persist_path` dạng tương đối so với `project_dir`, giải quyết tận gốc vấn đề portability.
- **Cách xác minh sau khi sửa:** Script rebuild in ra `n documents: 24`, và so `set(paper_id)` giữa `papers_clean.csv` và `documents` trong manifest — khớp 100%.
- **Điều học được:** Artifact sinh ra từ code (embedding index, vector DB) không nên tin tưởng chỉ vì file tồn tại — luôn kiểm tra số lượng document và tính portable của path trước khi coi là "đã build xong". Đây cũng là lý do các file `data/chroma/*` và `data/embeddings/*.json` liên tục bị conflict khi nhiều người cùng build và push — nên xử lý bằng cách xoá và build lại từ dữ liệu nguồn (`papers_clean*.csv`, deterministic), không hand-merge file nhị phân/JSON sinh ra từ code.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** Crossref trả về JSON raw, được lưu nguyên vẹn vào `data/raw/` trước khi parse thành `PaperRecord`. Bước cleaning chuẩn hoá schema, tạo `text_for_embedding` (ghép title/authors/summary) và `age_days`, ghi ra `data/clean/papers_clean.csv`. Vai trò của tôi bắt đầu từ đây: đọc DataFrame clean, dùng MiniLM (`SentenceTransformer`) embed `text_for_embedding`, nạp vào ChromaDB persistent collection, ghi manifest JSON để tái lập lại index mà không cần embed lại từ đầu.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `test_set.json` chứa câu hỏi (`question`) kèm `ground_truth` (đáp án đúng) và `ground_truth_doc_ids` (paper_id đúng phải được retrieval trả về). Evaluator chạy từng câu hỏi qua pipeline retrieval + answer, so `retrieved_doc_ids` với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, so câu trả lời với `ground_truth` để tính `mean_token_f1` và dùng LLM-judge để tính `judge_accuracy`/`mean_judge_score`.

3. **Quality checks khác freshness monitoring ở điểm nào?** Quality check (`data/quality/*_quality.json`) kiểm tra tính toàn vẹn cấu trúc dữ liệu tại một thời điểm: số dòng, `paper_id` có null/trùng không, title/summary có rỗng không. Freshness (`freshness_report.json`) kiểm tra tính "mới" theo thời gian: `published` có nằm trong ngưỡng `freshness_threshold_days` không, có bao nhiêu `stale_rows`. Một dataset có thể "quality PASS" (cấu trúc đúng) nhưng vẫn "STALE" (dữ liệu cũ), hoặc ngược lại.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để phép so sánh có ý nghĩa — nếu đổi câu hỏi giữa các trạng thái thì chênh lệch metric có thể do câu hỏi khác nhau chứ không phải do chất lượng dữ liệu thay đổi. Giữ nguyên `test_set.json` đảm bảo mọi khác biệt về `retrieval_hit_rate`/`mean_token_f1`/`judge_accuracy` chỉ phản ánh đúng tác động của corruption/repair.

5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên `data/results/repaired_metrics.json` (`recovery_status: "FULL_RECOVERY"`, `repaired_record_count: 24` khớp `baseline_record_count: 24`) và bảng so sánh trong `data/reports/corruption_report.md`: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` của repaired quay lại đúng bằng giá trị baseline (1.000 / 0.575 / 0.542 / 3.083), đồng thời quality chuyển từ FAIL (corrupted) về PASS và freshness từ STALE về FRESH. Ở phía RAG, tôi xác nhận thêm bằng chứng độc lập: semantic search top-3 trên `papers-repaired` khớp lại y hệt `papers-baseline`, record bị drop tìm lại được, summary bị blank đã điền lại.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |    1.000 |     0.667 |    1.000 | Giảm 0.333 khi corrupt (do 1 record bị drop + noise làm lệch ranking), phục hồi hoàn toàn sau repair |
| `mean_token_f1`      |    0.575 |     0.370 |    0.575 | Giảm mạnh nhất về mặt tỉ lệ; phục hồi đúng bằng baseline |
| `judge_accuracy`     |    0.542 |     0.333 |    0.542 | LLM-judge đánh giá câu trả lời kém hẳn khi dữ liệu lỗi, phục hồi đúng |
| `mean_judge_score`   |    3.083 |     2.333 |    3.083 | Giảm ~0.75 điểm/5 khi corrupted, phục hồi đúng |
| Quality checks         |     PASS |      FAIL | PASS | Corrupted fail vì `paper_id_unique` (do `add_duplicate_rows`) |
| Freshness status       |    FRESH |     STALE | FRESH | Corrupted có 1 stale row do `old_published_date`, repaired về 0 |

### Kết luận từ số liệu

1. **Data corruption → quality/freshness signal thay đổi → agent metric thay đổi:** `corrupt_clean_dataframe` xoá 1 record mới nhất, inject noise vào 2 record, blank summary 2 record, làm cũ ngày publish 1 record, thêm 1 duplicate (24→23 dòng) → quality check chuyển PASS→FAIL (`paper_id_unique` fail vì duplicate), freshness chuyển FRESH→STALE (1 stale row) → `retrieval_hit_rate` giảm từ 1.000 xuống 0.667, `mean_judge_score` giảm từ 3.083 xuống 2.333. Từ góc nhìn RAG, tôi quan sát trực tiếp cơ chế: 1 paper biến mất khỏi index (lookup trả `None`), 1 paper khác bị noise đẩy nhầm vào top-3 semantic search — đây là nguyên nhân kỹ thuật cụ thể phía sau con số `retrieval_hit_rate` giảm.
2. **Repair action → quality/freshness signal phục hồi → agent metric phục hồi:** Repair chạy lại từ raw records (`source_raw_path` trong `repaired_metrics.json`), không sửa tay từ dữ liệu corrupted → khôi phục đủ 24 record, `paper_id` unique trở lại, freshness về 0 stale row → toàn bộ 4 metric retrieval/answer quay lại đúng bằng baseline (khớp đến 3 chữ số thập phân). Về phía RAG, index rebuild lại từ file clean repaired cho kết quả semantic search/lookup giống hệt baseline.

Corruption ảnh hưởng rõ nhất là **`drop_latest_records`** kết hợp **`inject_noise`**: không chỉ làm mất 1 record (giảm hit-rate trực tiếp) mà noise còn làm lệch cả ranking của các record còn nguyên vẹn — tức là corruption trên 1 record có thể ảnh hưởng gián tiếp đến kết quả truy vấn cho các record khác, không chỉ giới hạn ở bản thân record bị lỗi.

Kết quả không khác kỳ vọng ban đầu: tôi kỳ vọng repair sẽ phục hồi phần lớn nhưng không chắc phục hồi *hoàn toàn* (vì corrupted record bị xoá hẳn, không chỉ bị sửa lỗi tại chỗ) — thực tế repair chạy lại từ raw nên phục hồi 100% chứ không phải "vá" dữ liệu corrupted, nên các metric khớp baseline tuyệt đối thay vì chỉ cải thiện một phần.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Artifact sinh ra từ code (vector index, embedding manifest) không nên commit như dữ liệu tĩnh khi nhiều người cùng build độc lập — dễ conflict và dễ chứa lỗi âm thầm (như manifest 1/24 document) nếu không kiểm tra kỹ trước khi coi là "xong".
2. **Data quality/observability:** Quality check và freshness monitoring đo hai chiều khác nhau (cấu trúc vs. thời gian) và cần chạy song song — một dataset có thể pass chiều này nhưng fail chiều kia, và cả hai đều cần thiết để phát hiện corruption trước khi nó lan tới người dùng cuối.
3. **Ảnh hưởng của data đến RAG agent:** Corruption trên một phần nhỏ dữ liệu (2/24 record bị inject noise) có thể ảnh hưởng đến kết quả truy vấn của các record khác thông qua ranking, không chỉ ảnh hưởng cục bộ đến bản thân record lỗi — nên đánh giá tác động data quality không thể chỉ nhìn vào record bị lỗi trực tiếp.

### Nếu có thêm thời gian

Sẽ thêm một bộ smoke-test tự động (thay vì script thủ công chạy tay mỗi lần) chạy ngay sau `LocalEmbeddingIndex.build()` để tự động kiểm tra document count khớp clean data và `persist_path` hợp lệ trước khi cho phép commit — đo cải thiện bằng việc giảm số lần phải rebuild lại do phát hiện muộn (đã xảy ra ít nhất 2 lần trong buổi vì manifest lỗi không bị phát hiện ngay).

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Anh Thư
**Ngày xác nhận:** 2026-08-06
