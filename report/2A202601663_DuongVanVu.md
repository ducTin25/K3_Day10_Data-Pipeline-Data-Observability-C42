# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Dương Văn Vũ |
| MSSV | 2A202601663 |
| Nhóm | C42 |
| Vai trò chính | Evaluation & Observability (Role 5) |
| Repository | `ducTin25/K3_Day10_Data-Pipeline-Data-Observability-C42` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Tôi phụ trách tạo evaluation set, đánh giá retrieval/answer quality, data-quality checks, freshness monitoring và báo cáo Markdown. Input chính là cleaned dataframe; output gồm test set cố định, answer-level artifacts, metrics, quality/freshness reports và evidence audit.

| Module | File/hàm | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Evaluation set | `src/evaluation/testset.py::build_test_set` | Clean dataframe | `data/eval/test_set.json` | Hoàn thành |
| Metrics | `src/evaluation/metrics.py::evaluate_pipeline` | Index + test set | `data/results/*_answers.json`, `*_metrics.json` | Hoàn thành cho baseline/corrupted |
| Quality/freshness | `src/observability/quality.py` | Dataframe clean/corrupted | JSON reports trong `data/quality/` | Hoàn thành |
| Reporting | `src/observability/reporting.py` | Metrics + observability artifacts | Markdown reports | Hoàn thành |

## 3. Kết quả và bằng chứng

- Test set có 24 câu hỏi (`summary`, `authors`, `date`, `categories`). Mỗi `ground_truth_doc_ids` lấy trực tiếp từ `paper_id` của clean data; các ID đều tồn tại trong `papers-baseline`.
- `baseline_index_audit.json` xác nhận 24 clean rows, 24 manifest documents và 24 documents trong Chroma.
- `baseline_answers.json` và `corrupted_answers.json` có 24 answer-level records, dùng cùng một test set.
- `corrupted_evaluation_audit.json` ghi nhận 8 trường hợp retrieval từ hit sang miss và liên kết được metric degradation với corruption log, quality và freshness signals.

Các artifact tiêu biểu:

- `data/eval/test_set.json`
- `data/results/baseline_metrics.json`
- `data/results/corrupted_metrics.json`
- `data/quality/baseline_quality.json`
- `data/quality/corrupted_quality.json`
- `data/quality/corrupted_evaluation_audit.json`
- `data/reports/phase1_report.md`

## 4. Giải thích kỹ thuật

Evaluation set được tạo deterministically bằng cách sort `paper_id`, giới hạn sáu paper đại diện và tạo các câu hỏi factual. Cách này tránh tự tạo document ID, giúp retrieval-hit metric có thể so sánh giữa baseline, corrupted và repaired.

Quality checks kiểm tra row count, `paper_id` null/unique, title thiếu, summary ngắn hơn 40 ký tự và `age_days`. Freshness report tính `latest_published`, `oldest_published`, số stale rows và trạng thái freshness từ `published`/`age_days`, không dùng ngày hiện tại giả định.

`retrieval_hit_rate` đo việc ground-truth document có xuất hiện trong top-k hay không. Token F1 đo overlap token giữa reference và answer; nó có thể thấp với summary dài dù retrieval đúng. Judge accuracy và mean judge score đo correctness theo evaluator; answer artifact luôn lưu `reasoning` để nhận biết LLM judge hay fallback heuristic.

Lệnh kiểm chứng tiêu biểu:

```powershell
$env:PYTHONPATH='src'
python script/run_phase1.py
python script/run_corruption_flow.py
```

Ngoài ra, các artifact được đối chiếu theo count, ID và JSON schema trước khi ghi kết luận.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh công bằng ba trạng thái dữ liệu.
- **Phương án:** Tạo test set mới sau từng corruption, hoặc đóng băng một test set baseline.
- **Phương án chọn:** Dùng cố định `data/eval/test_set.json` cho baseline, corrupted và repaired.
- **Lý do:** Nếu câu hỏi hoặc ground truth thay đổi, metric khác biệt không còn phản ánh riêng tác động của data corruption.
- **Bằng chứng:** Audit CP5 xác nhận baseline và corrupted đều có 24 samples; corruption làm retrieval hit rate giảm từ 1.000 xuống 0.667.

## 6. Lỗi/blocker đã xử lý

- **Triệu chứng:** `baseline_answers.json` không parse được JSON do chứa marker `<<<<<<<`, `=======`, `>>>>>>>` sau merge Git.
- **Nguyên nhân gốc:** Generated answer artifact bị merge theo text trong khi nội dung contexts lớn và có thay đổi từ nhiều nhánh.
- **Cách xử lý:** Tái tạo baseline answers/metrics từ baseline index và test set cố định, thay vì sửa tay answer hoặc metric.
- **Xác minh:** JSON parse thành công với 24 records; baseline artifact tiếp tục dùng đúng `papers-baseline` và test set cố định.
- **Bài học:** Generated Chroma/answer artifacts cần quy trình rebuild rõ ràng; không nên hand-merge binary database hoặc JSON evaluation lớn.

## 7. Hiểu biết end-to-end

Crossref response được parse thành raw records, sau đó cleaning chuẩn hóa field, loại row lỗi, tạo stable `paper_id`, `age_days` và `text_for_embedding`. Clean dataframe được đưa vào Chroma index; test set dùng `paper_id` làm ground truth để đo retrieval và answer quality.

Quality monitoring kiểm tra tính đầy đủ, uniqueness và validity của dữ liệu. Freshness monitoring kiểm tra độ mới thông qua published date/age. Cùng test set phải được dùng cho ba trạng thái để metric có ý nghĩa so sánh. Repair chỉ được xem là thành công khi dataset/index được rebuild từ raw snapshot, quality/freshness phục hồi và metrics được chạy lại; không chỉnh tay answers hoặc metrics.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.667 | Chưa xác minh lại từ metrics file hiện tại | Corruption giảm 0.333; có 8 hit-to-miss cases |
| `mean_token_f1` | 0.575 | 0.370 | Chưa xác minh lại từ metrics file hiện tại | Giảm 0.205 |
| `judge_accuracy` | 0.500 | 0.375 | Chưa xác minh lại từ metrics file hiện tại | Giảm 0.125 |
| `mean_judge_score` | 3.167 | 2.792 | Chưa xác minh lại từ metrics file hiện tại | Giảm 0.375 |
| Quality checks | PASS | FAIL | Có `repaired_quality.json` PASS | Duplicate và summary lỗi bị phát hiện |
| Freshness | FRESH | STALE | Có repaired freshness FRESH | Corrupted có 1 stale row |

Chuỗi bằng chứng thứ nhất: drop/latest records, blank summary, duplicate và old date tạo quality `FAIL`/freshness `STALE`; đồng thời retrieval hit rate giảm 0.333 và token F1 giảm 0.205.

Chuỗi thứ hai: repaired quality/freshness artifacts cho thấy data-level recovery. Tuy nhiên, tại thời điểm viết báo cáo, `data/results/repaired_metrics.json` đang chứa repair metadata thay vì schema metrics. Vì vậy tôi không dùng file đó để khẳng định numerical recovery; cần regenerate repaired evaluation metrics trước khi nộp bản cuối.

## 9. Điều học được và hướng cải thiện

1. Data quality phải được kiểm tra trước khi index, vì duplicate/blank summary có thể ảnh hưởng trực tiếp retrieval.
2. Freshness là tín hiệu riêng: schema có thể hợp lệ nhưng corpus vẫn stale.
3. Cùng một test set giúp tách tác động data corruption khỏi thay đổi evaluation prompt/ground truth.

Nếu có thêm thời gian, tôi sẽ bổ sung distribution checks cho title/summary và chạy ablation từng corruption scenario riêng lẻ để định lượng lỗi nào gây tác động lớn nhất.

## 10. Cam kết

- [x] Nội dung phản ánh đúng phần việc Evaluation & Observability của tôi.
- [x] Các kết luận baseline/corrupted đều có artifact để đối chiếu.
- [x] Không ghi API key, token hoặc `.env` trong báo cáo.
- [x] Đã nêu rõ blocker repaired metrics chưa đúng schema hiện tại.

**Họ và tên:** Dương Văn Vũ  
**Ngày xác nhận:** 2026-08-06
