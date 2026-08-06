# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Cao Nhật Minh |
| MSSV | 2A202601721 |
| Nhóm | C42 |
| Vai trò | Thành viên 2 — Source Ingestion / Raw Lineage |
| Phạm vi chính | `src/ingestion/crossref.py` và `data/raw/` |
| Repository | `K3_Day10_Data-Pipeline-Data-Observability-C42` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Phạm vi công việc

Tôi phụ trách đưa dữ liệu paper từ Crossref vào pipeline theo cách có thể truy vết và tái lập. Trọng tâm không chỉ là lấy được dữ liệu, mà còn phải giữ được raw snapshot để cả nhóm có thể audit nguồn, đối chiếu DOI và repair dữ liệu mà không gọi lại API làm thay đổi baseline.

| Deliverable | Input | Xử lý phụ trách | Output bàn giao |
| --- | --- | --- | --- |
| Crossref ingestion | Crossref REST API `/works`, Settings | Gọi API, retry 429/503, parse JSON nested | `list[PaperRecord]` |
| Raw lineage | HTTP payload và PaperRecord | Lưu raw trước parse, audit DOI/ID, load lại snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| Source evidence | `paper_id`, raw/clean/index artifacts | Trace một DOI xuyên suốt, cung cấp evidence khi retrieval/answer sai | lineage audit và source evidence từ raw snapshot |
| Hỗ trợ repair | `corruption_log.json`, repaired dataset | Chứng minh record bị drop có trong raw và được phục hồi | evidence raw → corrupted → repaired |

Các phần cleaning/corruption, RAG/Chroma, evaluation/observability và orchestration thuộc owner tương ứng; tôi chỉ kiểm tra contract và lineage tại các điểm handoff.

## 3. Kết quả theo checkpoint

| Checkpoint | Công việc của tôi | Kết quả và evidence |
| --- | --- | --- |
| CP0 | Chốt stable ID, parse/fetch/load Crossref, raw artifacts, retry/backoff | DOI canonicalized là `paper_id`; lấy 24 records; lưu raw response và parsed records |
| CP1 | Đối chiếu raw response ↔ PaperRecord snapshot | 24 raw items = 24 parsed records; không DOI thiếu/trùng; raw đủ field để cleaning xử lý |
| CP2 | Kiểm tra `paper_id` raw → clean → index metadata, không refresh nguồn | 24 IDs khớp ở raw, clean, embedding manifest và Chroma baseline; baseline dùng snapshot |
| CP3 | Kiểm chứng baseline không thay đổi source | `raw_mode: snapshot`, 24 raw → 24 clean → 24 indexed documents |
| CP5 | Kiểm tra raw nguyên vẹn trước corruption, chọn record repair | Chọn `10.1111/exsy.70341`; có trong raw, bị drop ở corrupted; corruption flow không gọi Crossref |
| CP6 | Chứng minh repair từ raw và hỗ trợ kiểm tra secret | Hai record bị drop xuất hiện lại ở repaired; `.env` không được Git track |

## 4. Thiết kế kỹ thuật và data contract

### 4.1 Stable paper ID

`paper_id` được tạo từ DOI của Crossref theo quy tắc:

```text
paper_id = DOI.strip().lower()
```

Ví dụ DOI `10.47576/2949-1894.2026.7.7.023` trở thành chính `paper_id` đó. Record thiếu DOI bị loại ở ingestion vì không thể deduplicate, trace qua index hoặc repair một cách đáng tin cậy.

DOI được chọn thay cho title/URL vì title có thể trùng hoặc thay đổi cách viết; DOI là định danh chuẩn và có thể dùng làm khóa xuyên suốt raw, clean, Chroma metadata, evaluation ground truth và corruption log.

### 4.2 Raw lineage

```text
Crossref REST API
  → data/raw/crossref_response.json       (payload gốc để audit nguồn)
  → parse_crossref_payload()
  → data/raw/crossref_records.json        (PaperRecord phẳng để tái lập)
  → cleaning / embedding / evaluation
```

Raw response được ghi **trước parse**. Vì vậy nếu parser hoặc cleaning tạo kết quả bất thường, nhóm có thể đối chiếu lại payload gốc thay vì phỏng đoán dữ liệu nguồn. `load_raw_records()` cho phép chạy lại từ snapshot offline.

### 4.3 Mapping chính từ Crossref sang `PaperRecord`

| `PaperRecord` | Nguồn Crossref | Quy tắc |
| --- | --- | --- |
| `paper_id` | `DOI` | trim + lowercase; thiếu DOI thì loại record |
| `title` | `title[0]` | chuẩn hóa whitespace tối thiểu |
| `summary` | `abstract` hoặc `description` | giữ JATS/HTML ở raw; cleaning mới strip markup |
| `authors` | `author[]` | ghép `given` + `family` hoặc dùng `literal` |
| `categories` | `subject[]` | optional, không tự suy diễn khi rỗng |
| `published` | `published-print` / `published-online` / `issued` | chuẩn hóa ISO date |
| `abs_url`, `pdf_url` | `URL`, `link[]` | PDF chỉ lấy link có `application/pdf` |

### 4.4 Retry và tính tái lập

Request Crossref retry tối đa 3 lần với HTTP `429` và `503`. Nếu có header `Retry-After` thì ưu tiên giá trị đó; nếu không dùng exponential backoff từ 1 giây. Baseline chỉ dùng raw snapshot khi `REFRESH_SOURCE=false`; không refresh API trong lúc baseline/corruption/repair để giữ corpus cố định.

## 5. Cách xác minh phần việc

Các artifact chính:

- `data/raw/crossref_response.json`: raw HTTP payload, 24 items.
- `data/raw/crossref_records.json`: 24 `PaperRecord` đã parse.
- `data/raw/crossref_lineage_report.json`: đối chiếu raw response với snapshot parsed.
- `data/quality/corruption_comparison_audit.json`: xác nhận baseline artifacts/index không bị ghi đè và test set cố định.
- `data/results/corruption_log.json`: record và loại corruption có chủ đích.

Các kiểm tra đã thực hiện:

```powershell
# Kiểm tra raw lineage, raw/clean ID và source refresh
python -c "from core.config import load_settings; from ingestion.crossref import audit_raw_lineage; print(audit_raw_lineage(load_settings()))"

# Chạy baseline và corruption/repair flow
python script/run_phase1.py
python script/run_corruption_flow.py
```

Kết quả kiểm chứng thực tế:

- Raw response parse lại khớp `crossref_records.json`: 24/24 records.
- Raw và clean có cùng 24 `paper_id`.
- Baseline collection `papers-baseline` có 24 documents; corrupted có 23; repaired có 24.
- Comparison audit xác nhận baseline artifacts và collection baseline không bị mutate.

## 6. Evidence repair từ raw snapshot

Hai record bị drop có chủ đích trong `corruption_log.json` là:

| `paper_id` | Raw | Corrupted | Repaired |
| --- | --- | --- | --- |
| `10.1111/exsy.70341` | Có | Không có | Có lại |
| `10.2118/234689-pa` | Có | Không có | Có lại |

Ví dụ record `10.1111/exsy.70341` có DOI URL `https://doi.org/10.1111/exsy.70341` trong raw source. Việc nó biến mất khỏi corrupted dataset nhưng trở lại repaired dataset chứng minh repair rebuild từ `data/raw/crossref_records.json`, thay vì copy tay baseline hoặc gọi API mới.

Raw snapshot được kiểm tra bằng SHA-256 trong quá trình handoff:

```text
crossref_response.json: 2308f5abc3e5...
crossref_records.json:  d7bbe997c969...
```

## 7. Phân tích kết quả toàn pipeline

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | Corruption làm giảm 0.333; repair phục hồi về baseline |
| `mean_token_f1` | 0.575 | 0.370 | 0.575 | Giảm 0.205 do corpus bị thiếu/nhiễu; repair phục hồi |
| `judge_accuracy` | 0.500 | 0.375 | 0.500 | Giảm 0.125 rồi trở lại baseline |
| `mean_judge_score` | 3.167 | 2.792 | 3.167 | Giảm 0.375 rồi phục hồi |
| Data quality | PASS | FAIL | PASS | Corruption bị phát hiện và repair khôi phục contract |
| Freshness | FRESH | STALE / INCOMPLETE | FRESH | Stale date bị loại bỏ khi rebuild từ raw |

Chuỗi bằng chứng chính là:

```text
drop / blank summary / noise / stale date / duplicate
  → quality FAIL và freshness STALE
  → retrieval + answer metrics giảm
  → reload raw snapshot + re-run cleaning/index/evaluation
  → quality/freshness và metrics quay lại baseline
```

Do các dạng corruption được áp dụng đồng thời, kết quả hiện tại chứng minh tác động tổng hợp; chưa đủ để kết luận riêng từng loại lỗi có mức ảnh hưởng lớn nhất.

## 8. Một vấn đề đã phát hiện và xử lý

Trong giai đoạn handoff CP2, embedding manifest từng chỉ chứa một document test (`10.1000/182`) nên không thể trace `paper_id` từ raw/clean vào index. Đây là artifact baseline không hợp lệ, không phải lỗi Crossref parser.

Nguyên nhân là manifest/index thử nghiệm được tạo trước khi baseline index được rebuild từ clean dataset thật. Cách xử lý là rebuild `papers-baseline` từ 24 clean records và kiểm tra tập `paper_id` ở raw, clean, manifest và Chroma metadata. Sau xử lý, cả bốn tầng đều có cùng 24 IDs; CP2 được thông qua.

Bài học: không dùng artifact generated mẫu để evaluate, và không hand-merge binary Chroma. Cần rebuild index từ clean dataset/manifest trên môi trường đang chạy.

## 9. Hiểu biết end-to-end

1. Crossref trả payload JSON; ingestion lưu payload gốc, parse về `PaperRecord` với DOI làm khóa. Cleaning bỏ markup, chuẩn hóa field và tạo `text_for_embedding`; RAG owner tạo MiniLM embeddings và Chroma collection từ clean dataset.
2. Evaluation set dùng `ground_truth_doc_ids` là các `paper_id` của clean/index. Giữ nguyên test set giúp chênh lệch metric phản ánh dữ liệu/index, không phải thay đổi câu hỏi.
3. Quality kiểm tra tính đầy đủ, uniqueness và độ hợp lệ của dataset; freshness đo độ mới dựa vào `published`/`age_days`. Hai nhóm signal trả lời các câu hỏi khác nhau.
4. Baseline, corrupted và repaired phải dùng cùng test set, evaluator và top-k để so sánh công bằng.
5. Repair thành công khi record bị corrupt/drop có thể truy vết lại raw snapshot, repaired schema/quality trở lại đạt và metrics repaired quay về baseline trên cùng evaluation set.

## 10. Điều học được và hướng cải thiện

1. Raw lineage là điều kiện cần để repair có thể kiểm chứng; chỉ giữ clean dataset sẽ không đủ để xác minh nguồn dữ liệu.
2. `paper_id` ổn định là cầu nối giữa data quality, vector metadata, evaluation ground truth và corruption log.
3. Một pipeline chạy không lỗi chưa chứng minh chất lượng: cần artifact, hash, quality/freshness signals và metrics cho cả ba trạng thái.

Nếu có thêm thời gian, tôi sẽ bổ sung một report lineage tự động cho nhiều `paper_id` và ablation test: mỗi lần chỉ bật một corruption scenario. Khi đó có thể đo riêng tác động của missing records, blank summaries, noise, stale date và duplicates.

## 11. Cam kết

- [x] Báo cáo phản ánh đúng vai trò Source Ingestion / Raw Lineage của tôi.
- [x] Các kết luận đều tham chiếu artifact hoặc metric thực tế.
- [x] Không ghi `.env`, API key, token hoặc secret.
- [x] Không nhận ownership cho cleaning, RAG, evaluation hay orchestration của thành viên khác.

**Họ và tên:** Cao Nhật Minh  
**MSSV:** 2A202601721  
**Ngày xác nhận:** 2026-08-06
