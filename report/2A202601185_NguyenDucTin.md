# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Đức Tín |
| MSSV | 2A202601185 |
| Khóa/Lớp | K3 |
| Tên nhóm | C42 |
| Vai trò chính | Điều phối pipeline / Pipeline integration & evidence owner |
| Repository | https://github.com/ducTin25/K3_Day10_Data-Pipeline-Data-Observability-C42 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Handoff và clean gate | `docs/pipeline-handoff.md`, `prepare_clean_handoff()` trong `src/pipelines/phase1.py` | Raw `PaperRecord`, settings, run date | Clean dataframe đã khóa contract, baseline index và fixed test set | Hoàn thành |
| Baseline orchestration | `main()` trong `src/pipelines/phase1.py` | Raw snapshot Crossref hoặc dữ liệu fetch mới | Raw → clean → index → test set → evaluate → quality/freshness → report | Hoàn thành |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py` | Baseline clean data, trusted raw snapshot và fixed test set | Corrupted/repaired datasets, index, metrics, quality/freshness và comparison report | Hoàn thành |
| Cấu hình artifact isolation | `src/core/config.py`, `src/retrieval/index.py` | Trạng thái baseline/corrupted/repaired | Collection và manifest riêng cho từng trạng thái | Hoàn thành |
| Evidence và báo cáo tích hợp | `report/group_report.md`, `data/reports/` | Artifacts và metrics thực tế | Báo cáo baseline/corruption có thể đối chiếu | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Khóa clean contract trước handoff | Cleaning, evaluation-set và retrieval modules | Test set/index chỉ được tạo sau khi schema và document IDs hợp lệ |
| Rà soát raw → clean lineage | Ingestion/cleaning | Xác minh 24 raw records → 24 clean records và lưu handoff/blocker evidence |
| Tích hợp và xử lý conflict | Toàn nhóm | Hợp nhất các nhánh, rebuild generated artifacts thay vì vá tay ChromaDB/JSON |
| Bổ sung validation tests | Cleaning, handoff và index contract | Test suite xác minh schema, path/collection và document identity |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Mô tả luồng handoff end-to-end | `docs/pipeline-handoff.md` | Sơ đồ raw → clean → index → evaluate → report, contract và điều kiện dừng | Đọc tài liệu và đối chiếu `phase1.py` |
| Khóa clean schema trước downstream | `prepare_clean_handoff()`, `assert_clean_contract()` | Không index/test set nếu thiếu field, ID không unique hoặc embedding text rỗng | `python -m uv run pytest -q` |
| Chạy baseline orchestration | `src/pipelines/phase1.py`, `script/run_phase1.py` | 24 raw → 24 clean → 24 indexed → 24 test samples | `python -m uv run python script/run_phase1.py` |
| Hoàn thiện corruption/repair flow | `src/pipelines/corruption_flow.py` | 23 corrupted rows và 24 repaired rows được evaluate trên cùng test set | `python -m uv run python script/run_corruption_flow.py` |
| Cô lập index/artifacts | `src/core/config.py`, `data/quality/corruption_comparison_audit.json` | `papers-baseline`, `papers-corrupted`, `papers-repaired`; baseline không bị ghi đè | Audit ghi `baseline_artifacts_unchanged=true`, `baseline_collection_unchanged=true` |
| Hoàn thiện evidence report | `report/group_report.md`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Bảng metrics và giới hạn kỹ thuật dựa trên artifact | So sánh với JSON trong `data/results/` và `data/quality/` |

Output tiêu biểu của phần việc là `data/quality/corruption_comparison_audit.json`: artifact này chứng minh ba collection được tách riêng với số documents lần lượt là 24, 23 và 24; fixed test set được giữ nguyên; các file baseline và collection baseline không bị corruption flow ghi đè.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các module ingestion, cleaning, retrieval, evaluation và observability đã có quan hệ phụ thuộc chặt nhưng cần một orchestration rõ ràng để không đưa dữ liệu sai contract xuống index. Đồng thời, pipeline corruption phải đo được tác động trên cùng test set mà không làm thay đổi baseline, sau đó repair từ nguồn raw đáng tin cậy và tạo đủ bằng chứng so sánh.

### Cách triển khai

Trong baseline flow, pipeline chọn raw snapshot hoặc fetch mới theo cấu hình, audit lineage rồi gọi `prepare_clean_handoff()`. Hàm này build clean dataframe, chạy `assert_clean_contract()`, lưu clean artifacts, build baseline index và so khớp count/ID giữa clean và index. Test set chỉ được tạo hoặc đọc sau clean gate; toàn bộ ground-truth document IDs phải là subset của index. Sau evaluation, pipeline chạy quality/freshness và sinh báo cáo; trạng thái quality/freshness fail làm entrypoint dừng bằng lỗi rõ ràng.

Trong corruption flow, pipeline chụp SHA-256 của các baseline artifacts và snapshot collection baseline trước khi mutate dữ liệu. Corrupted data được lưu, index và evaluate ở collection riêng. Repair không chỉnh tay JSON kết quả mà rebuild clean dataframe từ trusted raw snapshot, tạo repaired collection rồi evaluate lại bằng chính `data/eval/test_set.json`. Cuối flow, hash và collection baseline được kiểm tra lại; nếu thay đổi thì flow fail.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `list[PaperRecord]`, raw snapshot JSON, `Settings`, fixed evaluation set |
| Output | Clean/corrupted/repaired CSV+JSON, ba Chroma collections, answers/metrics, quality/freshness và Markdown reports |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `retrieval.index`, `evaluation.metrics`, `observability.quality` |
| Module sử dụng output | Evaluation, observability, reporting và corruption comparison |
| Điều kiện lỗi cần xử lý | Raw lineage fail; clean schema sai; document IDs lệch; test-set ID không thuộc index; collection sai tên; baseline bị ghi đè; quality/freshness baseline fail |

### Cách xác minh

```bash
python -m uv run pytest -q
python -m uv run python script/run_phase1.py
python -m uv run python script/run_corruption_flow.py
```

- Kết quả mong đợi: test pass; baseline có 24 records/documents/samples; corruption và repair dùng collection riêng; audit xác nhận baseline không đổi.
- Kết quả thực tế: test suite gần nhất đạt 16 tests; baseline retrieval hit rate đạt 1.000; corruption giảm xuống 0.667; repair trở lại 1.000.
- Artifact/log: `data/results/*_metrics.json`, `data/quality/*.json`, `data/reports/*.md`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Corruption flow cần rebuild Chroma index và sinh artifacts mới nhưng không được làm mất baseline dùng làm đối chứng.
- **Các phương án đã cân nhắc:** tái sử dụng/ghi đè collection baseline rồi rebuild lại; hoặc tách collection và manifest theo từng trạng thái.
- **Phương án đã chọn:** dùng ba collection `papers-baseline`, `papers-corrupted`, `papers-repaired` và các path artifact riêng.
- **Lý do:** giữ phép so sánh reproducible, giảm nguy cơ mất đối chứng và cho phép audit trực tiếp count/hash/ID. Chi phí là ChromaDB sinh thêm dữ liệu và cần quản lý generated artifacts cẩn thận.
- **Bằng chứng quyết định phù hợp:** `corruption_comparison_audit.json` xác nhận baseline artifacts/collection không đổi và count ba collection là 24/23/24.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Git conflict lặp lại ở `data/chroma/chroma.sqlite3`, Chroma segment binaries và một số generated JSON/Markdown.
- **Lệnh hoặc bước tái hiện:** merge các nhánh cùng rebuild persistent ChromaDB và cùng commit generated artifacts.
- **Nguyên nhân gốc:** SQLite/HNSW là binary state, không thể merge theo dòng; generated results từ nhiều lần chạy cũng có timestamp/judge output khác nhau.
- **Cách xử lý:** không hand-merge database hoặc vá JSON metrics; giữ code/data contract đúng, chọn collection/path riêng và rebuild artifacts từ clean/raw source bằng entrypoint.
- **Cách xác minh sau khi sửa:** kiểm tra không còn unmerged path, chạy tests và entrypoint; đối chiếu manifest/collection/audit.
- **Điều học được:** generated vector-store state không phù hợp để nhiều nhánh cùng chỉnh sửa; nên ưu tiên manifest + lệnh rebuild và cân nhắc loại DB binary khỏi Git.

## 7. Hiểu biết về luồng end-to-end

1. Crossref `/works` trả raw response; ingestion parse thành `PaperRecord` và lưu snapshot/lineage. Cleaning chuẩn hóa markup, trường dữ liệu và identity, tạo `text_for_embedding`; clean gate pass thì MiniLM encode văn bản và Chroma lưu vector với DOI chuẩn hóa làm `paper_id`.
2. Mỗi evaluation sample chứa question, ground truth và `ground_truth_doc_ids`. Retrieval hit kiểm tra ground-truth ID có trong top-k; answer quality được đo bằng token F1 và LLM judge so với ground truth.
3. Quality checks đo volume, completeness, uniqueness và validity của dataset. Freshness monitoring tập trung vào thời gian xuất bản, số record stale/missing và ngưỡng 180 ngày.
4. Cùng test set giữ biến số câu hỏi và ground truth cố định; nhờ vậy thay đổi metric chủ yếu phản ánh thay đổi corpus/index thay vì thay đổi benchmark.
5. Repair thành công khi repaired clean/index trở về count và contract hợp lệ, quality PASS, freshness FRESH, baseline không bị mutate và metrics phục hồi. Trong lần chạy được lưu, retrieval hit rate và token F1 phục hồi đúng baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | Corruption làm mất hit ở 8/24 câu; repair phục hồi hoàn toàn |
| `mean_token_f1` | 0.575 | 0.370 | 0.575 | Giảm 0.205 rồi phục hồi đúng baseline |
| `judge_accuracy` | 0.500 | 0.375 | 0.500 | Artifact corruption report cho thấy giảm 0.125 và phục hồi 0.125 |
| `mean_judge_score` | 3.167 | 2.792 | 3.167 | Giảm 0.375 và phục hồi về baseline trong cùng comparison run |
| Quality checks | PASS | FAIL | PASS | Corrupted có 2 duplicate rows, 3 summary ngắn và 1 stale row |
| Freshness status | FRESH | STALE | FRESH | Corrupted có ngày cũ nhất 1970-01-01; repaired trở lại snapshot hợp lệ |

### Kết luận từ số liệu

1. Drop/blank/noise/truncate/stale/duplicate → quality FAIL và freshness STALE → retrieval hit rate giảm từ 1.000 xuống 0.667, token F1 giảm từ 0.575 xuống 0.370.
2. Rebuild từ trusted raw snapshot → count/uniqueness/summary/freshness trở lại PASS/FRESH → retrieval hit rate và token F1 phục hồi về 1.000 và 0.575.

Corruption ảnh hưởng rõ nhất ở cấp retrieval là drop record kết hợp với biến dạng text/index: ground-truth documents bị thiếu hoặc embedding không còn đại diện tốt, khiến 8 câu không retrieve được đúng document trong top-4. Tuy nhiên flow hiện áp dụng nhiều corruption cùng lúc nên chưa thể quy toàn bộ mức giảm cho riêng một scenario; cần ablation để kết luận nhân quả chi tiết.

Điểm đáng chú ý là judge metric có thể thay đổi giữa các lần gọi LLM dù retrieval và token F1 deterministic. Vì vậy phân tích comparison dùng bộ artifacts cùng một lần chạy và không diễn giải dao động judge là bằng chứng duy nhất về chất lượng data.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Handoff phải có contract và điều kiện dừng rõ ràng; chỉ kiểm tra file tồn tại là chưa đủ, cần so count và stable document IDs giữa các stage.
2. Observability có giá trị khi signal gắn với artifact và failure mode cụ thể; PASS/FAIL phải truy ngược được tới duplicate, summary invalid hoặc stale rows.
3. Để đánh giá tác động dữ liệu lên RAG, cần giữ test set, model, top-k và evaluator nhất quán, đồng thời tách baseline/corrupted/repaired state.

### Nếu có thêm thời gian

Tôi sẽ tách từng corruption thành một ablation run riêng và bổ sung check noise/title-length distribution. Mỗi scenario sẽ có collection, metrics delta và report riêng; mức cải thiện được đo bằng khả năng định danh chính xác corruption nào gây giảm retrieval/answer quality. Tôi cũng sẽ đưa Chroma runtime DB ra khỏi Git và kiểm tra khả năng rebuild trong CI để loại bỏ binary conflict.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đức Tín  
**Ngày xác nhận:** 2026-08-06
