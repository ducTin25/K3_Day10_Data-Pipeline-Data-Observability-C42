import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace, write_csv, write_json
from ingestion.crossref import PaperRecord


def strip_html_tags(text: str) -> str:
    """Remove HTML/JATS tags and normalize whitespace."""
    if not text:
        return ""
    clean_text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(clean_text)


def build_clean_dataframe(
    records: list[PaperRecord],
    run_date: datetime,
) -> pd.DataFrame:
    """Clean raw records into a structured DataFrame ready for embedding and evaluation.

    Steps:
    1. Normalize title, summary, authors, categories (strip HTML/JATS tags & extra spaces).
    2. Parse published/updated dates and compute age_days.
    3. Construct helper columns (authors_joined, categories_joined, summary_chars, text_for_embedding).
    4. Filter invalid rows (missing paper_id/title, summary < 40 chars) and deduplicate by paper_id.
    5. Sort dataframe by published date descending and return.
    """
    if not records:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "categories",
                "primary_category",
                "published",
                "updated",
                "abs_url",
                "pdf_url",
                "comment",
                "authors_joined",
                "categories_joined",
                "summary_chars",
                "age_days",
                "text_for_embedding",
            ]
        )

    cleaned_rows: list[dict[str, Any]] = []
    run_dt = run_date.date() if isinstance(run_date, datetime) else run_date

    for rec in records:
        paper_id = rec.paper_id.strip().lower()
        if not paper_id:
            continue

        title = strip_html_tags(rec.title)
        if not title:
            continue

        summary = strip_html_tags(rec.summary)
        if len(summary) < 40:
            continue

        authors = [strip_html_tags(a) for a in rec.authors if strip_html_tags(a)]
        categories = [strip_html_tags(c) for c in rec.categories if strip_html_tags(c)]
        authors_joined = compact_join(authors, sep=", ")
        categories_joined = compact_join(categories, sep=", ")

        published = rec.published.strip()
        age_days = None
        if published:
            try:
                pub_date = datetime.strptime(published, "%Y-%m-%d").date()
                age_days = (run_dt - pub_date).days
            except ValueError:
                age_days = None

        updated = rec.updated.strip()

        parts = []
        if title:
            parts.append(f"Title: {title}")
        if authors_joined:
            parts.append(f"Authors: {authors_joined}")
        if categories_joined:
            parts.append(f"Categories: {categories_joined}")
        if summary:
            parts.append(f"Summary: {summary}")
        text_for_embedding = "\n".join(parts)

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": rec.primary_category,
                "published": published,
                "updated": updated,
                "abs_url": rec.abs_url,
                "pdf_url": rec.pdf_url,
                "comment": rec.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(cleaned_rows)
    if df.empty:
        return df

    # Deduplicate by stable paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sort by published descending, paper_id ascending
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df


def save_clean_artifacts(df: pd.DataFrame, settings) -> tuple[Path, Path]:
    """Save cleaned DataFrame to CSV and JSON artifacts."""
    csv_path = settings.paths.clean_csv
    json_path = settings.paths.clean_json

    write_csv(df, csv_path)
    records = df.to_dict(orient="records")
    write_json(json_path, records)

    return csv_path, json_path

