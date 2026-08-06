# Crossref raw-lineage handoff

- Raw API snapshot: `D:\AI20K\codelabs\K3_Day10_Data-Pipeline-Data-Observability-C42\data\raw\crossref_response.json`
- Parsed PaperRecord snapshot: `D:\AI20K\codelabs\K3_Day10_Data-Pipeline-Data-Observability-C42\data\raw\crossref_records.json`
- Lineage audit: `D:\AI20K\codelabs\K3_Day10_Data-Pipeline-Data-Observability-C42\data\raw\crossref_lineage_report.json`
- Snapshot matches reparse: `True`
- Cleaning input ready: `True`
- `paper_id` is the canonicalized DOI; use it as the stable key for repair and comparison.
- `summary` may contain JATS/HTML; strip markup only in cleaning, never in raw artifacts.
- Empty categories are valid optional source metadata; do not infer categories.

## Sample PaperRecord

```json
{
  "paper_id": "10.47576/2949-1894.2026.7.7.023",
  "title": "Снижение рисков применения LLM (Large Language Model) в сфере экономической безопасности предприятий молочной промышленности на основе подхода RAG (Retrieval-Augmented Generation)",
  "summary": "<jats:p>В статье проведено исследование особенностей снижения рисков применения LLM (Large Language Model) в сфере экономической безопасности предприятий молочной промышленности на основе подхода RAG (Retrieval-Augmented Generation) в современных условиях. Рассмотрены риски применения LLM в сфере экономической безопасности предприятий молочной промышленности. Подробно разобраны сценарии применения LLM+RAG в российской молочной промышленности – с описанием процесса, задействованных данных, решаемых рисков и достигнутых результатов. Показано, что в результате интеграция RAG с LLM трансформирует генеративную модель из потенциально опасного инструмента в надежный механизм поддержки принятия решений – от мониторинга угроз фальсификации до прогнозирования экономических показателей с учетом отраслевой специфики.</jats:p> <jats:p>The article examines the features of reducing the risks of using LLM (Large Language Model) in the field of economic security of dairy industry enterprises based on the RAG (Retrieval-Augmented Generation) approach in modern conditions. The risks of using LLM in the field of economic security of dairy industry enterprises are considered. The scenarios of LLM+RAG application in the Russian dairy industry are analyzed in detail, describing the process, the data involved, the risks to be solved and the results achieved. It is shown that as a result, the integration of RAG with LLM transforms the generative model from a potentially dangerous tool into a reliable decision support mechanism, from monitoring fraud threats to forecasting economic indicators based on industry specifics.</jats:p>",
  "authors": [
    "И.В. Ермаков",
    "В.В. Филатов"
  ],
  "categories": [],
  "primary_category": "",
  "published": "2026-06-15",
  "updated": "",
  "abs_url": "https://doi.org/10.47576/2949-1894.2026.7.7.023",
  "pdf_url": "",
  "comment": "Reducing the risks of using LLM (Large Language Model) in the field of economic security of dairy enterprises based on the RAG (Retrieval-Augmented Generation) approach"
}
```
