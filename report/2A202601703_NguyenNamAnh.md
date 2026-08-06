# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                  |
| --------------- | ----------------------------------------------------------------          |
| Họ và tên       | Nguyễn Nam Anh                                                            |
| MSSV            | 2A202601703                                                               |
| Khóa/Lớp        | K3 / C42                                                                  |
| Tên nhóm        | C42                                                                       |
| Vai trò chính   | Role 3 — Cleaning & Corruption Owner (Data Foundation & Recovery)         |
| Repository      | https://github.com/ducTin25/K3_Day10_Data-Pipeline-Data-Observability-C42 |
| Ngày hoàn thành | 2026-08-06                                                                |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data Cleaning & Standardization | `src/ingestion/cleaning.py`<br>`build_clean_dataframe()`, `assert_clean_contract()` | `list[PaperRecord]` từ Crossref raw snapshot | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Hoàn thành (100%) |
| Controlled Data Corruption | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe()` | Clean DataFrame (`papers_clean.json`) | `data/clean/papers_clean_corrupted.json`<br>`data/results/corruption_log.json` | Hoàn thành (100%) |
| Data Recovery & Repair | `src/ingestion/repair.py`<br>`repair_data_from_raw()` | Trusted Raw Snapshot (`crossref_records.json`) | `data/clean/papers_clean_repaired.json`<br>`data/results/repaired_metrics.json` | Hoàn thành (100%) |
| Verification & Audit Suites | `scripts/run_checkpoint1.py`, `run_corruption.py`, `run_repair.py`, `verify_checkpoint*.py`, `audit_project_progress.py` | Artifacts & Data Metrics | Báo cáo kiểm định hợp đồng dữ liệu & script tự động | Hoàn thành (100%) |
| Automated Unit Testing | `tests/test_cleaning.py`<br>`tests/test_corruption.py`<br>`tests/test_repair.py` | Dữ liệu giả định & DataFrames | 16/16 Unit Tests PASSED | Hoàn thành (100%) |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Handoff Contract Gate | Nguyễn Đức Tín (Phase 1 Pipeline) | Tích hợp `assert_clean_contract()` vào `src/pipelines/phase1.py` để chặn pipeline nếu clean data lỗi |
| Vector Index Handoff | Trần Anh Thư (RAG & Index Owner) | Đảm bảo `text_for_embedding` và `paper_id` chuẩn hóa 100% cho Chroma DB collections |
| Data Quality & Freshness Verification | Dương Văn Vũ (Observability Owner) | Cung cấp đúng schema `age_days` và `summary_chars` cho các cổng Data Quality Gates |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Làm sạch và định dạng dữ liệu chuẩn | `src/ingestion/cleaning.py`<br>`data/clean/papers_clean.json` | 24 bản ghi sạch, 0 duplicate, 100% đầy đủ `text_for_embedding` | `python scripts/verify_checkpoint2_role3.py` |
| Tạo nhiễu dữ liệu có kiểm soát (CP5) | `src/ingestion/corruption.py`<br>`data/results/corruption_log.json` | 8 scenario nhiễu (23 bản ghi), giảm Hit Rate từ `1.000` xuống `0.667` | `python scripts/run_corruption.py` |
| Khôi phục dữ liệu từ Raw (CP6) | `src/ingestion/repair.py`<br>`data/clean/papers_clean_repaired.json` | Khôi phục 24/24 bản ghi, Data Quality chuyển từ `FAIL` về `PASS` | `python scripts/run_repair.py` |

**Artifact cụ thể được tạo ra:**
- [`data/clean/papers_clean.json`](file:///c:/Users/Admin/Downloads/CodeLab10/K3_Day10_Data-Pipeline-Data-Observability-C42/data/clean/papers_clean.json): 24 bản ghi sạch đã qua kiểm duyệt hợp đồng dữ liệu.
- [`data/results/corruption_log.json`](file:///c:/Users/Admin/Downloads/CodeLab10/K3_Day10_Data-Pipeline-Data-Observability-C42/data/results/corruption_log.json): Nhật ký ghi nhận chi tiết 8 hành vi tạo nhiễu dữ liệu.
- [`data/clean/papers_clean_repaired.json`](file:///c:/Users/Admin/Downloads/CodeLab10/K3_Day10_Data-Pipeline-Data-Observability-C42/data/clean/papers_clean_repaired.json): Tập dữ liệu tái lập nguyên bản từ `crossref_records.json`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Dữ liệu thô từ Crossref API chứa thẻ JATS/HTML (như `<jats:p>`, `<sub/>`), khoảng trắng thừa, và chưa có cấu trúc chuẩn cho Embedding. Đồng thời cần có cơ chế mô phỏng nhiễu dữ liệu (Data Corruption) thực tế và khả năng phục hồi dữ liệu tự động (Data Repair) khi hệ thống gặp lỗi mà không làm ảnh hưởng đến bản gốc.

### Cách triển khai
1. **Làm sạch (Cleaning)**:
   - Dùng Regex `re.sub(r"<[^>]+>", " ", text)` để loại bỏ triệt để các thẻ HTML/JATS.
   - Ép `paper_id` thành DOI viết thường (`strip().lower()`) để làm khóa chính duy nhất.
   - Tính toán `age_days` dựa trên khoảng cách giữa `run_date` và ngày xuất bản `published`.
   - Định dạng `text_for_embedding` gồm: `Title`, `Authors`, `Categories`, và `Summary`.
2. **Gác cổng Hợp đồng Dữ liệu (Clean Contract Gate)**:
   - Hàm `assert_clean_contract()` kiểm tra 9 tiêu chí (non-empty, missing columns, paper_id uniqueness, summary length, age_days validity). Nếu lỗi sẽ ngắt pipeline ngay lập tức (`CleanContractError`).
3. **Tạo nhiễu (Corruption)**:
   - Thực thi 8 kịch bản: Xóa bản ghi mới nhất, làm rỗng summary, thêm noise chuỗi rác, cắt xén tiêu đề, đẩy ngày về 1970 (stale date), và chèn bản ghi trùng lặp (`duplicate`).
4. **Khôi phục (Repair)**:
   - Đọc lại snapshot đáng tin cậy `data/raw/crossref_records.json` và chạy lại quy trình `build_clean_dataframe()` để tái tạo tập dữ liệu sạch 100%.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `list[PaperRecord]` từ Crossref raw snapshot hoặc `data/raw/crossref_records.json` |
| Output | `pandas.DataFrame` sạch, file `papers_clean.json`, `papers_clean.csv`, `corruption_log.json` |
| Module phụ thuộc | `src/ingestion/crossref.py`, `src/core/config.py`, `src/core/utils.py` |
| Module sử dụng output | `src/retrieval/index.py` (Vector Search), `src/evaluation/testset.py` (Test Set Generation), `src/observability/quality.py` (Quality Gates) |
| Điều kiện lỗi cần xử lý | Raw record thiếu DOI/Title, summary ngắn hơn 40 ký tự, định dạng ngày tháng không khớp ISO `%Y-%m-%d` |

### Cách xác minh

```bash
python -m uv run pytest tests/test_cleaning.py tests/test_corruption.py tests/test_repair.py
python scripts/verify_checkpoint3_role3.py
python scripts/run_corruption.py
python scripts/run_repair.py
```

- **Kết quả mong đợi:** Tất cả unit tests PASSED; contract report trả về `passed: True`; dữ liệu corrupted làm sụt giảm Hit Rate; dữ liệu repaired phục hồi Hit Rate về `1.000` và Quality về `PASS`.
- **Kết quả thực tế:** 16/16 unit tests PASSED 100%; Data Quality Gate đạt `PASS` cho Baseline & Repaired; `FAIL` cho Corrupted.
- **Artifact/log:** [`data/results/corruption_log.json`](file:///c:/Users/Admin/Downloads/CodeLab10/K3_Day10_Data-Pipeline-Data-Observability-C42/data/results/corruption_log.json), [`data/reports/corruption_report.md`](file:///c:/Users/Admin/Downloads/CodeLab10/K3_Day10_Data-Pipeline-Data-Observability-C42/data/reports/corruption_report.md).

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cấu trúc nội dung văn bản `text_for_embedding` đưa vào mô hình MiniLM embedding.
- **Các phương án đã cân nhắc:**
  1. *Phương án 1*: Chỉ sử dụng phần `summary` thô sau khi làm sạch.
  2. *Phương án 2*: Ghép nối có nhãn tiền tố rõ ràng (`Title: {title}\nAuthors: {authors}\nCategories: {categories}\nSummary: {summary}`).
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Giúp mô hình Embedding bắt được cả thông tin tiêu đề, tác giả và thể loại chuyên ngành, cải thiện đáng kể độ chính xác của biểu diễn vector cosine similarity.
- **Bằng chứng quyết định phù hợp:** Kết quả `retrieval_hit_rate` của Baseline đạt **`1.000` (100% chính xác)** trên 24/24 câu hỏi kiểm thử.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  `UnicodeEncodeError: 'charmap' codec can't encode character '\u2010' in position ...: character maps to <undefined>` khi chạy script kiểm tra trên Windows PowerShell.
- **Lệnh hoặc bước tái hiện:**
  Chạy `python scripts/verify_checkpoint2_role3.py` trên môi trường Windows PowerShell mặc định (cp1252).
- **Nguyên nhân gốc:** Trình thông dịch Python trên Windows mặc định dùng encoding `cp1252` cho `sys.stdout`, không thể in các ký tự Unicode hoa/gạch nối gõ trong tiêu đề bài báo khoa học.
- **Cách xử lý:** Thêm cấu hình tự động reconfigure encoding ở đầu các script thực thi:
  ```python
  if hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8")
  ```
- **Cách xác minh sau khi sửa:** Chạy lại script verification trên Terminal PowerShell, tất cả các ký tự Unicode in ra màn hình mượt mà không còn lỗi.
- **Điều học được:** Khi xây dựng Data Pipeline trên môi trường cross-platform (Windows / Linux), luôn chú ý chuẩn hóa I/O Streams và UTF-8 encoding.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Raw JSON từ Crossref `/works` -> parse thành `PaperRecord` -> làm sạch JATS/HTML & deduplicate -> tạo `text_for_embedding` -> nhúng vector bằng MiniLM `all-MiniLM-L6-v2` -> lưu trữ dạng vector HNSW Cosine trong ChromaDB collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Mỗi sample trong `test_set.json` chứa 1 câu hỏi và danh sách `ground_truth_doc_ids` (chính là `paper_id`). Khi RAG agent chạy retrieval top-k, hệ thống đối chiếu `retrieved_doc_ids` với `ground_truth_doc_ids`. Nếu có giao nhau thì `retrieval_hit = True`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks*: Kiểm tra tính toàn vẹn (completeness, uniqueness, null values, summary length).
   - *Freshness monitoring*: Kiểm tra tính tươi mới của dữ liệu (tính `age_days = run_date - published` và so sánh với ngưỡng `180` ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính nhất quán (controlled variable). Mọi sự thay đổi về metric (`retrieval_hit_rate`, `token_f1`, `judge_score`) sẽ phản ánh đúng tác động của chất lượng dữ liệu, chứ không phải do câu hỏi bị thay đổi.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - Artifacts: `papers_clean_repaired.json` khôi phục đủ 24 bản ghi, `repaired_quality.json` có `passed: True`, và `repaired_freshness_report.json` có `is_fresh: True`.
   - Metrics: `retrieval_hit_rate` phục hồi từ `0.667` về lại `1.000` (+0.333) và `mean_token_f1` phục hồi từ `0.370` về lại `0.575`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | Nhiễu làm giảm 33.3% khả năng tìm đúng tài liệu; Repair phục hồi 100%. |
| `mean_token_f1` | 0.575 | 0.370 | 0.575 | Độ khớp từ vựng sụt giảm mạnh khi summary bị xóa/nhiễu; Repair giúp F1 trở lại mốc ban đầu. |
| `judge_accuracy` | 0.542 | 0.333 | 0.542 | LLM Judge đánh giá chính xác câu trả lời giảm mạnh ở bản Corrupted và phục hồi ở bản Repaired. |
| `mean_judge_score` | 3.083 | 2.333 | 3.083 | Điểm số chất lượng câu trả lời trung bình khôi phục hoàn toàn về mức 3.083/5. |
| Quality checks | PASS | FAIL | PASS | Nhiễu gây lỗi duplicate và missing summary; Repair làm sạch đạt 6/6 checks. |
| Freshness status | FRESH | STALE | FRESH | Kịch bản đẩy ngày về 1970 khiến Corrupted bị STALE; Repair khôi phục ngày xuất bản gốc. |

### Kết luận từ số liệu

1. **Chuỗi nguyên nhân 1 (Corruption)**: `[Data corruption: xóa paper & làm rỗng summary]` → `[Quality check FAIL & Freshness STALE]` → `[Retrieval hit rate giảm từ 1.000 xuống 0.667]`.
2. **Chuỗi nguyên nhân 2 (Repair)**: `[Repair action: rebuild từ crossref_records.json]` → `[Quality check chuyển về PASS & Freshness về FRESH]` → `[Retrieval hit rate phục hồi hoàn toàn về 1.000]`.

- **Corruption ảnh hưởng rõ nhất:** Kịch bản **Blank Summary** và **Drop Latest Papers** ảnh hưởng nghiêm trọng nhất vì trực tiếp làm mất ngữ cảnh thông tin khiến vector search không thể truy xuất đúng document ID.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Garbage In, Garbage Out**: Chất lượng của RAG Agent phụ thuộc trực tiếp 100% vào tính sạch sẽ và toàn vẹn của dữ liệu đầu vào.
2. **Tầm quan trọng của Data Contract**: Việc xây dựng `assert_clean_contract()` giúp phát hiện sớm các sự cố dữ liệu trước khi tốn tài nguyên chạy Embedding/Indexing.
3. **Data Observability**: Cần kết hợp cả Data Quality Gates (tính toàn vẹn) và Freshness Monitoring (tính tươi mới) để theo dõi sức khỏe dữ liệu theo thời gian thực.

### Nếu có thêm thời gian
Tôi sẽ xây dựng cơ chế **Ablation Study tự động** cho từng loại corruption lẻ (thay vì gộp 8 loại cùng lúc) để đo lường chính xác phần phần trăm suy giảm metric của riêng từng kịch bản nhiễu.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Nam Anh  
**Ngày xác nhận:** 2026-08-06
