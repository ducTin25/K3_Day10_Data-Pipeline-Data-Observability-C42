from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate various data corruption scenarios on a clean DataFrame.

    Pseudo-code:
    1. Drop some latest records.
    2. Blank summary on some rows.
    3. Inject noise into text.
    4. Truncate titles.
    5. Make published date old or invalid.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Write corruption log to output_log_path.
    """
    if df.empty:
        write_json(Path(output_log_path), {"initial_rows": 0, "final_rows": 0, "steps": []})
        return df.copy()

    corrupted = df.copy()
    steps_log: list[dict[str, Any]] = []

    # Step 1: Drop a subset of the latest records
    if len(corrupted) > 5:
        before_count = len(corrupted)
        # Sort by published descending if available
        if "published" in corrupted.columns:
            corrupted = corrupted.sort_values(by="published", ascending=False)
        dropped_ids = corrupted.iloc[:2]["paper_id"].tolist()
        corrupted = corrupted.iloc[2:].reset_index(drop=True)
        steps_log.append(
            {
                "step": "drop_latest_records",
                "parameter": {"records": 2, "selection": "latest published"},
                "count": len(dropped_ids),
                "before_count": before_count,
                "after_count": len(corrupted),
                "dropped_paper_ids": dropped_ids,
                "changes": [{"paper_id": paper_id, "before": "present", "after": None} for paper_id in dropped_ids],
            }
        )

    # Step 2: Blank summary on some rows
    blank_indices = list(range(min(2, len(corrupted))))
    blanked_ids = corrupted.iloc[blank_indices]["paper_id"].tolist()
    blank_before = corrupted.iloc[blank_indices]["summary"].astype(str).tolist()
    corrupted.loc[blank_indices, "summary"] = ""
    steps_log.append(
        {
            "step": "blank_summary",
            "parameter": {"records": 2, "field": "summary", "replacement": ""},
            "count": len(blanked_ids),
            "before_count": len(corrupted),
            "after_count": len(corrupted),
            "affected_paper_ids": blanked_ids,
            "changes": [{"paper_id": paper_id, "before": before, "after": ""} for paper_id, before in zip(blanked_ids, blank_before, strict=True)],
        }
    )

    # Step 3: Inject noise into text/summary on some rows
    if len(corrupted) > 3:
        noise_indices = [2, 3]
        noise_ids = corrupted.iloc[noise_indices]["paper_id"].tolist()
        noise_before = corrupted.iloc[noise_indices]["summary"].astype(str).tolist()
        for idx in noise_indices:
            corrupted.loc[idx, "summary"] = (
                "[CORRUPTED NOISE: GARBLED TEXT] " + str(corrupted.loc[idx, "summary"])[:50]
            )
        steps_log.append(
            {
                "step": "inject_noise",
                "parameter": {"records": 2, "prefix": "[CORRUPTED NOISE: GARBLED TEXT]"},
                "count": len(noise_ids),
                "before_count": len(corrupted),
                "after_count": len(corrupted),
                "affected_paper_ids": noise_ids,
                "changes": [{"paper_id": paper_id, "before": before, "after": str(corrupted.loc[idx, "summary"])} for paper_id, before, idx in zip(noise_ids, noise_before, noise_indices, strict=True)],
            }
        )

    # Step 4: Truncate title on some rows
    if len(corrupted) > 4:
        trunc_indices = [3, 4]
        trunc_ids = corrupted.iloc[trunc_indices]["paper_id"].tolist()
        trunc_before = corrupted.iloc[trunc_indices]["title"].astype(str).tolist()
        for idx in trunc_indices:
            title_val = str(corrupted.loc[idx, "title"])
            corrupted.loc[idx, "title"] = title_val[:8] if len(title_val) > 8 else "Trunc"
        steps_log.append(
            {
                "step": "truncate_title",
                "parameter": {"records": 2, "max_chars": 8},
                "count": len(trunc_ids),
                "before_count": len(corrupted),
                "after_count": len(corrupted),
                "affected_paper_ids": trunc_ids,
                "changes": [{"paper_id": paper_id, "before": before, "after": str(corrupted.loc[idx, "title"])} for paper_id, before, idx in zip(trunc_ids, trunc_before, trunc_indices, strict=True)],
            }
        )

    # Step 5: Make published date old or invalid
    if len(corrupted) > 1:
        date_indices = [1]
        date_ids = corrupted.iloc[date_indices]["paper_id"].tolist()
        date_before = corrupted.iloc[date_indices][["published", "age_days"]].to_dict(orient="records")
        for idx in date_indices:
            corrupted.loc[idx, "published"] = "1970-01-01"
            corrupted.loc[idx, "age_days"] = 20000
        steps_log.append(
            {
                "step": "old_published_date",
                "parameter": {"records": 1, "published": "1970-01-01", "age_days": 20000},
                "count": len(date_ids),
                "before_count": len(corrupted),
                "after_count": len(corrupted),
                "affected_paper_ids": date_ids,
                "changes": [{"paper_id": paper_id, "before": before, "after": {"published": "1970-01-01", "age_days": 20000}} for paper_id, before in zip(date_ids, date_before, strict=True)],
            }
        )

    # Step 6: Add duplicate rows
    if len(corrupted) > 0:
        before_count = len(corrupted)
        dup_row = corrupted.iloc[[0]].copy()
        dup_id = dup_row.iloc[0]["paper_id"]
        corrupted = pd.concat([corrupted, dup_row], ignore_index=True)
        steps_log.append(
            {
                "step": "add_duplicate_rows",
                "parameter": {"records": 1, "selection": "first remaining row"},
                "count": 1,
                "before_count": before_count,
                "after_count": len(corrupted),
                "duplicated_paper_ids": [dup_id],
                "changes": [{"paper_id": dup_id, "before": "one row", "after": "two rows"}],
            }
        )

    # Step 7: Rebuild text_for_embedding & summary_chars for all rows
    for idx in range(len(corrupted)):
        row = corrupted.iloc[idx]
        title = str(row.get("title", ""))
        authors_joined = str(row.get("authors_joined", ""))
        categories_joined = str(row.get("categories_joined", ""))
        summary = str(row.get("summary", ""))

        parts = []
        if title:
            parts.append(f"Title: {title}")
        if authors_joined:
            parts.append(f"Authors: {authors_joined}")
        if categories_joined:
            parts.append(f"Categories: {categories_joined}")
        if summary:
            parts.append(f"Summary: {summary}")
        
        corrupted.loc[idx, "summary_chars"] = len(summary)
        corrupted.loc[idx, "text_for_embedding"] = "\n".join(parts)

    # Step 8: Write corruption log
    log_payload = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "initial_rows": len(df),
        "final_rows": len(corrupted),
        "steps": steps_log,
    }
    write_json(Path(output_log_path), log_payload)

    return corrupted

