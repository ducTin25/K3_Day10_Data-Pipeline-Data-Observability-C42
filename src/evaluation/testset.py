from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import normalize_whitespace, write_json
from ingestion.cleaning import assert_clean_contract


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create a deterministic, factual evaluation set from clean paper records.

    Every ground-truth document ID comes directly from ``paper_id`` so that
    retrieval-hit scoring is always aligned with the indexed clean corpus.
    """
    assert_clean_contract(df)

    def as_text(value: Any) -> str:
        if value is None or (not isinstance(value, (list, tuple, set)) and pd.isna(value)):
            return ""
        if isinstance(value, (list, tuple, set)):
            return normalize_whitespace(", ".join(str(item) for item in value if item is not None))
        return normalize_whitespace(str(value))

    def value(row: pd.Series, joined_column: str, list_column: str) -> str:
        return as_text(row.get(joined_column)) or as_text(row.get(list_column))

    records = df.copy()
    records["paper_id"] = records["paper_id"].map(as_text)
    records["title"] = records["title"].map(as_text)
    records["summary"] = records["summary"].map(as_text)
    records = records[(records["paper_id"] != "") & (records["title"] != "") & (records["summary"] != "")]
    records = records.sort_values("paper_id").drop_duplicates("paper_id")
    if records.empty:
        raise ValueError("Cannot create an evaluation set from an empty cleaned dataframe.")

    samples: list[dict[str, Any]] = []

    def add(question_type: str, question: str, ground_truth: str, paper_id: str) -> None:
        if not ground_truth:
            return
        samples.append(
            {
                "id": f"eval-{len(samples) + 1:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    # Limit the fixture to six papers: enough variety while keeping evaluation cheap.
    for _, row in records.head(6).iterrows():
        paper_id, title, summary = row["paper_id"], row["title"], row["summary"]
        authors = value(row, "authors_joined", "authors")
        categories = value(row, "categories_joined", "categories")
        published = as_text(row.get("published"))
        add("summary", f"What does the paper '{title}' discuss?", summary, paper_id)
        add("authors", f"Who authored the paper '{title}'?", authors, paper_id)
        add("date", f"When was the paper '{title}' published?", published, paper_id)
        add("categories", f"What categories are assigned to the paper '{title}'?", categories, paper_id)

    if not samples:
        raise ValueError("No valid evaluation samples could be generated from the cleaned dataframe.")
    write_json(output_path, samples)
    return samples
