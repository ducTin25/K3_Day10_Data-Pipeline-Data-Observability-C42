# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K3 |
| Tên nhóm | C42 |
| Repository | https://github.com/ducTin25/K3_Day10_Data-Pipeline-Data-Observability-C42 |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Đức Tín | 2A202601185 | Điều phối pipeline | `src/core/` · `src/pipelines/` |
| 2 | Cao Nhật Minh | 2A202601721 | Source Ingestion | `src/ingestion/crossref.py` · `data/raw/` |
| 3 | Dương Văn Vũ | 2A202601663 | Evaluation & observability | `src/evaluation/` · `src/observability/` |
| 4 | Trần Anh Thư | 2A202601611 | RAG & agent | `src/retrieval/` · `data/embeddings/` |
| 5 | Nguyễn Nam Anh | 2A202601703 | Cleaning & corruption | `src/ingestion/cleaning.py` · `corruption.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành cả baseline và corruption/repair pipeline trên snapshot Crossref gồm 24 records. Baseline tạo 24 clean records, collection `papers-baseline` gồm 24 documents và fixed test set 24 câu; đạt `retrieval_hit_rate=1.000`, `mean_token_f1=0.575`, `judge_accuracy=0.500`, `mean_judge_score=3.167`, quality PASS và freshness FRESH. Corruption flow tạo có chủ đích các lỗi drop latest, blank summary, noise, truncate title, stale date và duplicate; lưu 23 rows vào collection riêng `papers-corrupted` và evaluate bằng đúng test set baseline. Corruption làm retrieval hit rate giảm còn 0.667, token F1 còn 0.370, judge accuracy còn 0.375 và mean judge score còn 2.792; quality chuyển sang FAIL và freshness thành STALE. Repair rebuild dữ liệu từ trusted raw snapshot, tạo 24 rows trong `papers-repaired`, đưa cả retrieval, answer metrics, quality và freshness trở lại đúng baseline. Ba collection và toàn bộ manifests/answers/metrics/freshness reports dùng path riêng; flow kiểm tra hash artifact và nội dung collection baseline để phát hiện ghi đè. Giới hạn còn lại là chưa cô lập tác động của từng corruption scenario và Ragas vẫn bị tắt.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref REST API / frozen raw snapshot
    -> raw response + PaperRecord snapshot
    -> cleaning + clean-contract gate
    -> MiniLM embedding + ChromaDB papers-baseline
    -> fixed evaluation test set
    -> baseline evaluation
    -> quality + freshness
    -> phase1 Markdown report
    -> corruption/repaired datasets (đã có data-quality evidence)
    -> corrupted/repaired evaluation + comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref `/works` hoặc raw snapshot | Request, retry 429/503, parse DOI/metadata, audit lineage | `data/raw/crossref_response.json`, `crossref_records.json` | Cao Nhật Minh |
| Cleaning | `list[PaperRecord]` | Strip JATS/HTML, normalize, validate, dedupe, tính `age_days`, build embedding text | `data/clean/papers_clean.{csv,json}` | Nguyễn Nam Anh |
| Embedding/index | Clean dataframe đã qua contract | MiniLM embedding, tạo collection cosine `papers-baseline` | `data/chroma/`, `data/embeddings/papers_embeddings.json` | Trần Anh Thư |
| Evaluation | Fixed test set + baseline index | Top-k retrieval, deterministic answer extraction, token F1 và LLM judge | `data/results/baseline_{answers,metrics}.json` | Dương Văn Vũ |
| Observability | Clean dataframe | Count/null/unique/summary/freshness checks | `data/quality/baseline_quality.json`, `freshness_report.json` | Dương Văn Vũ |
| Corruption/repair | Baseline clean + trusted raw snapshot | Tạo lỗi có log; rebuild repaired clean từ raw | Corrupted/repaired clean và quality artifacts | Nguyễn Nam Anh |
| Orchestration | Settings + artifacts giữa các stage | Raw → clean gate → index → test set → evaluate → observe → report | `data/reports/phase1_report.md` | Nguyễn Đức Tín |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4o-mini` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Random seed | Không áp dụng cho baseline; test set được tạo deterministic từ 6 paper đầu sau sort |

Không ghi API key hoặc nội dung `.env` trong báo cáo.

### Lệnh cài đặt và chạy đã sử dụng

```bash
python -m uv sync --extra dev
python -m uv run pytest -q
python -m uv run python script/run_phase1.py
python -m uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công, exit code 0 | 2026-08-06 12:06 (Asia/Saigon) | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Test suite | Thành công, 16 tests passed | 2026-08-06 | `python -m uv run pytest -q` |
| Corruption flow | Thành công, exit code 0 | 2026-08-06 | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API, `https://api.crossref.org/works` |
| Query/filter | `agentic retrieval augmented generation large language model`; `from-pub-date:2026-02-07,has-abstract:true` |
| Thời điểm lưu snapshot gần nhất | 2026-08-06 12:06 (Asia/Saigon) |
| Số record nhận được | 24 raw items; 24 parsed `PaperRecord` |
| Cơ chế retry/backoff | Tối đa 3 retries cho HTTP 429/503; ưu tiên `Retry-After`, nếu không có dùng exponential backoff từ 1 giây |

### Raw và clean schema

| Trường | Kiểu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | string | Có | DOI chuẩn hóa, stable document ID | Raw thiếu DOI bị loại; clean gate yêu cầu không rỗng và unique |
| `title` | string | Có | Tiêu đề paper | Strip markup/whitespace; row rỗng bị loại |
| `summary` | string | Có | Abstract/description | Strip JATS/HTML; yêu cầu tối thiểu 40 ký tự |
| `authors` / `authors_joined` | list/string | Có trong contract clean | Tác giả dạng cấu trúc và chuỗi metadata | Normalize; nối bằng dấu phẩy |
| `categories` / `categories_joined` | list/string | Không | Crossref subjects | Giữ rỗng nếu source không cung cấp, không tự suy diễn |
| `published` | ISO date | Có | Ngày xuất bản | Parse `YYYY-MM-DD`; clean contract kiểm tra validity |
| `age_days` | integer | Có | Tuổi record tại ngày chạy | Tính `run_date - published`; không chấp nhận null/âm |
| `summary_chars` | integer | Có | Độ dài summary sạch | Dùng cho summary minimum-length check |
| `text_for_embedding` | string | Có | Nội dung đưa vào MiniLM | Clean gate yêu cầu không rỗng |
| `abs_url`, `pdf_url` | string | Không | DOI landing page và PDF nếu có | Giữ chuỗi rỗng khi source không cung cấp |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Strip JATS/HTML và normalize whitespace | Consistency | 24 | 24 raw summaries chứa markup; clean summaries không còn tags |
| Loại missing `paper_id`/title | Completeness | 0 | Raw lineage và clean counts |
| Loại summary dưới 40 ký tự | Validity | 0 | `baseline_quality.json` |
| Deduplicate theo `paper_id` | Uniqueness | 0 | `paper_id_unique=PASS`, 24 unique IDs |
| Tạo và kiểm tra `text_for_embedding` | Completeness | 24 được tạo, 0 rỗng | Clean contract và `papers_clean.json` |

`text_for_embedding` ghép các phần có dữ liệu theo format `Title`, `Authors`, `Categories`, `Summary`. Document ID dùng DOI đã strip và lowercase. `age_days` là số ngày giữa thời điểm chạy và `published`. Clean gate chạy trước cả index lẫn test-set handoff; nếu schema/content không đạt thì pipeline dừng.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 24 |
| `question_type` | `summary`, `authors`, `date`, `categories` — mỗi loại 6 câu |
| Ground-truth document ID | Lấy trực tiếp từ clean `paper_id`; toàn bộ IDs là subset của baseline index |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB persistent, cosine HNSW, `papers-baseline`, 24 documents |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenAI / `gpt-4o-mini` |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`; 24 samples được dùng nguyên vẹn cho cả ba evaluations |

Giữ nguyên test set giúp mọi thay đổi metric phản ánh thay đổi dataset/index thay vì thay đổi câu hỏi hoặc ground truth. Đây là điều kiện bắt buộc trước khi so sánh baseline, corrupted và repaired.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | 24 records, lineage audit pass |
| Cleaned dataset | `data/clean/papers_clean.{csv,json}` | Có | 24 records, clean contract pass |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | `papers-baseline`, 24 documents, relative path |
| Evaluation set | `data/eval/test_set.json` | Có | 24 fixed samples |
| Baseline metrics/answers | `data/results/baseline_{metrics,answers}.json` | Có | 24 answer-level records |
| Quality/freshness | `data/quality/` | Có | Baseline PASS/FRESH |
| Baseline report | `data/reports/phase1_report.md` | Có | Sinh từ JSON artifacts thực tế |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.000 | Cả 24 câu đều retrieve được ground-truth document trong top-4 |
| `mean_token_f1` | 0.575 | Mức overlap token trung bình giữa answer và reference; thấp hơn hit rate vì answer extraction thường ngắn hơn ground truth summary |
| `judge_accuracy` | 0.500 | 12/24 answers được LLM judge đánh giá materially correct |
| `mean_judge_score` | 3.167/5 | Chất lượng answer trung bình theo judge |
| Ragas | N/A | Bỏ qua theo cấu hình; chỉ chạy khi `RUN_RAGAS=1` |

## 8. Data quality và freshness

### Quality checks

| Check | Dimension | Ngưỡng | Baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| Row count | Volume | `> 0` | PASS: 24 | `baseline_quality.json` |
| `paper_id` not null | Completeness | 0 invalid | PASS: 0 | `baseline_quality.json` |
| `paper_id` unique | Uniqueness | 0 duplicate | PASS: 0 | `baseline_quality.json` |
| Title not null | Completeness | 0 invalid | PASS: 0 | `baseline_quality.json` |
| Summary minimum length | Validity | ≥40 chars | PASS: 0 invalid | `baseline_quality.json` |
| Freshness | Timeliness | `age_days ≤ 180`, không missing | PASS: 0 stale, 0 missing | `baseline_quality.json` |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Clean dataframe `data/clean/papers_clean.json` |
| Timestamp mới nhất / cũ nhất | 2026-08-01 / 2026-02-12 |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | FRESH |
| Lý do | 24 records, 0 stale rows và 0 missing published dates |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal thực tế | Tác động agent | Repair |
| --- | --- | ---: | --- | --- | --- |
| Drop latest | Xóa hai paper mới nhất | 2 | Row count 24 → 23 sau khi cộng một duplicate | Đo trong tác động tổng hợp, chưa cô lập scenario | Rebuild từ raw snapshot |
| Blank summary | Làm rỗng summary | 2 | Summary check FAIL; tổng 3 rows dưới ngưỡng | Đo trong tác động tổng hợp, chưa cô lập scenario | Re-clean từ raw |
| Inject noise | Thêm nhiễu vào embedding text | 2 | Không có check chuyên biệt | Đo trong tác động tổng hợp, chưa cô lập scenario | Re-clean từ raw |
| Truncate title | Cắt ngắn title | 2 | Title vẫn non-null nên check hiện tại không bắt được | Đo trong tác động tổng hợp, chưa cô lập scenario | Re-clean từ raw |
| Old publication date | Làm cũ ngày xuất bản | 1 | Freshness FAIL, 1 stale row | Đo trong tác động tổng hợp, chưa cô lập scenario | Re-clean từ raw |
| Duplicate row | Thêm một row trùng ID | 1 | Uniqueness FAIL, 2 duplicate rows | Đo trong tác động tổng hợp, chưa cô lập scenario | Re-clean/dedupe từ raw |

Corruption log tồn tại tại `data/results/corruption_log.json` và ghi loại lỗi, count, affected paper IDs. Repaired dataset có 24 records, `repaired_quality.json` đạt PASS và `repaired_metrics.json` chứa RAG evaluation metrics chuẩn. Repair được thực hiện bằng cách rebuild từ `data/raw/crossref_records.json`, không chỉnh tay corrupted answers hay metrics.

Log còn ghi parameter, count trước/sau và giá trị before/after cho từng record. Audit lineage xác nhận 7/7 IDs chịu corruption đều có trong frozen raw snapshot và được phục hồi đúng một lần trong repaired dataset. Case `eval-009` là bằng chứng hit → miss → recovered hit: DOI `10.1111/exsy.70341` được retrieve từ `papers-baseline`, biến mất ở `papers-corrupted` sau drop, rồi xuất hiện lại khi truy vấn `papers-repaired`.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.667 | 1.000 | Corruption −0.333; repair +0.333, phục hồi hoàn toàn |
| `mean_token_f1` | 0.575 | 0.370 | 0.575 | Corruption −0.205; repair +0.205, phục hồi hoàn toàn |
| `judge_accuracy` | 0.500 | 0.375 | 0.500 | Corruption −0.125; repair +0.125, phục hồi về baseline |
| `mean_judge_score` | 3.167 | 2.792 | 3.167 | Corruption −0.375; repair +0.375, phục hồi về baseline |
| Quality | PASS | FAIL | PASS | Data-level corruption được phát hiện và repair |
| Freshness signal | FRESH: 0/24 stale | STALE: 1/23 stale | FRESH: 0/24 stale | Có report riêng cho baseline, corrupted và repaired trong `data/quality/` |

Kết luận được artifact hỗ trợ: (1) corruption làm mất/biến dạng corpus, đồng thời tạo duplicate, summary lỗi và stale date → quality/freshness chuyển PASS/FRESH thành FAIL/STALE → retrieval hit rate giảm 0.333, token F1 giảm 0.205, judge accuracy giảm 0.125 và mean judge score giảm 0.375; (2) rebuild từ trusted raw snapshot → row count/uniqueness/freshness trở lại baseline → cả bốn metrics phục hồi về mức baseline trong comparison run ngày 2026-08-06. Judge metrics vẫn phụ thuộc LLM evaluator, vì vậy kết luận chỉ áp dụng cho bộ artifacts cùng lượt chạy này.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Merge Git tạo conflict trên `phase1.py`, metrics/report JSON/Markdown và binary `chroma.sqlite3`; một trạng thái resolve tạm thời còn đưa `phase1.py` về `NotImplementedError` và report có metric trùng.
- **Nguyên nhân:** Nhiều nhánh cùng sửa orchestration và commit generated Chroma/evaluation artifacts; binary SQLite không thể merge theo dòng.
- **Cách xử lý:** Giữ orchestration end-to-end, không hand-merge SQLite; dọn các Chroma segments mồ côi, rebuild `papers-baseline` từ clean dataset rồi regenerate metrics/quality/report.
- **Cách xác minh:** `python -m uv run pytest -q` đạt 16 tests; baseline và corruption entrypoints hoàn tất; manifest, Chroma và clean đều có 24 IDs/documents ở baseline/repaired; `corruption_comparison_audit.json` xác nhận baseline không bị ghi đè.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Nhiều corruption được áp dụng cùng lúc | Không cô lập được scenario nào gây giảm metric nhiều nhất | Chạy ablation: mỗi lần chỉ bật một corruption và dùng cùng test set/evaluator |
| Ragas bị tắt | Chưa có faithfulness/context precision/recall | Chạy `RUN_RAGAS=1`, lưu kết quả và chi phí/thời gian |
| 24/24 records thiếu categories từ Crossref | Category questions có ít ground truth hoặc bị bỏ qua tùy record | Thêm query/source có subject hoặc báo coverage theo question type |
| Quality checks chưa bắt noise/truncated title | Một số corruption không tạo signal trực tiếp | Thêm distribution/length/outlier checks và kiểm tra thay đổi so với baseline |
| Chroma binary được commit | Dễ conflict khi nhiều nhánh cùng rebuild | Cân nhắc ignore generated DB, rebuild bằng manifest/command trong CI |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả hiện có.
- [x] Baseline đã được chạy lại trên phiên bản hiện tại.
- [x] Baseline, corrupted và repaired đã được evaluate bằng cùng test set.
- [x] Bảng ba trạng thái khớp với `data/results/` và comparison report.
- [x] Baseline quality/freshness conclusions khớp `data/quality/`.
- [x] Các đường dẫn baseline và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (hiện có 1/5: Nguyễn Đức Tín).
- [x] Đã chạy secret scan cuối cùng; chỉ có placeholder `GOOGLE_API_KEY=your_key_here` trong README, không có key thật hoặc `.env` được track.

### CP5/CP6 completion evidence

- [x] Corruption log có type, parameter, ID, before/after và before/after count.
- [x] Corrupted, baseline và repaired dùng collection/path riêng; audit xác nhận baseline không bị mutate.
- [x] Repair re-clean từ frozen raw snapshot; 7/7 affected IDs có lineage và phục hồi đúng một lần.
- [x] Ba trạng thái dùng cùng fixed test set và có metrics/quality/freshness delta.
- [x] Có case-level evidence `eval-009` với collection, ground-truth ID và hit/miss/recovery.
- [x] Report ghi rõ giới hạn: corruption chạy gộp, judge có dao động và Ragas đang tắt.
