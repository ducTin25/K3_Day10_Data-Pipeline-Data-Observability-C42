import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace, write_csv, write_json
from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = (
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
)


class CleanContractError(ValueError):
    """Raised before test-set/index work when clean data is not safe to hand off."""


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
        return pd.DataFrame(columns=CLEAN_COLUMNS)

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
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    # Deduplicate by stable paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sort by published descending, paper_id ascending
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df


def validate_clean_contract(df: pd.DataFrame) -> dict[str, Any]:
    """Validate the single schema consumed by both test-set and index stages."""
    missing_columns = sorted(set(CLEAN_COLUMNS) - set(df.columns))

    def blank_count(column: str) -> int:
        if column not in df.columns:
            return len(df)
        values = df[column]
        return int((values.isna() | values.astype(str).str.strip().eq("")).sum())

    paper_ids = df["paper_id"] if "paper_id" in df.columns else pd.Series(dtype="object")
    published = (
        pd.to_datetime(df["published"], format="%Y-%m-%d", errors="coerce")
        if "published" in df.columns
        else pd.Series(dtype="datetime64[ns]")
    )
    age_days = (
        pd.to_numeric(df["age_days"], errors="coerce")
        if "age_days" in df.columns
        else pd.Series(dtype="float64")
    )
    checks = {
        "non_empty": {"passed": len(df) > 0, "row_count": len(df)},
        "schema": {"passed": not missing_columns, "missing_columns": missing_columns},
        "paper_id_not_blank": {"passed": blank_count("paper_id") == 0, "invalid_rows": blank_count("paper_id")},
        "paper_id_unique": {
            "passed": not paper_ids.duplicated().any(),
            "duplicate_rows": int(paper_ids.duplicated(keep=False).sum()),
        },
        "title_not_blank": {"passed": blank_count("title") == 0, "invalid_rows": blank_count("title")},
        "summary_not_blank": {"passed": blank_count("summary") == 0, "invalid_rows": blank_count("summary")},
        "text_for_embedding_not_blank": {
            "passed": blank_count("text_for_embedding") == 0,
            "invalid_rows": blank_count("text_for_embedding"),
        },
        "published_valid": {
            "passed": len(published) == len(df) and not published.isna().any(),
            "invalid_rows": int(published.isna().sum()),
        },
        "age_days_valid": {
            "passed": len(age_days) == len(df) and not age_days.isna().any() and not (age_days < 0).any(),
            "invalid_rows": int(age_days.isna().sum() + (age_days < 0).sum()),
        },
    }
    return {
        "contract_version": 1,
        "columns": list(CLEAN_COLUMNS),
        "row_count": len(df),
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }


def assert_clean_contract(df: pd.DataFrame) -> dict[str, Any]:
    """Return the contract report or stop the downstream handoff."""
    report = validate_clean_contract(df)
    if not report["passed"]:
        failed = [name for name, check in report["checks"].items() if not check["passed"]]
        raise CleanContractError(
            "Clean contract failed; test-set/index handoff was stopped. "
            f"Failed checks: {', '.join(failed)}"
        )
    return report


def save_clean_artifacts(df: pd.DataFrame, settings) -> tuple[Path, Path]:
    """Save cleaned DataFrame to CSV and JSON artifacts."""
    csv_path = settings.paths.clean_csv
    json_path = settings.paths.clean_json

    write_csv(df, csv_path)
    records = df.to_dict(orient="records")
    write_json(json_path, records)

    return csv_path, json_path

