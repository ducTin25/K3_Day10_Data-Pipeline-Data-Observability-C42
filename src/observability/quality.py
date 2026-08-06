from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate the clean-data contract and save an auditable JSON result."""
    row_count = len(df)

    def column(name: str) -> pd.Series:
        return df[name] if name in df.columns else pd.Series(None, index=df.index, dtype="object")

    def blank(values: pd.Series) -> pd.Series:
        return values.isna() | values.astype(str).str.strip().eq("")

    paper_ids, titles, summaries = column("paper_id"), column("title"), column("summary")
    ages = pd.to_numeric(column("age_days"), errors="coerce")
    missing_ids = int(blank(paper_ids).sum())
    duplicate_rows = int(paper_ids.loc[~blank(paper_ids)].duplicated(keep=False).sum())
    missing_titles = int(blank(titles).sum())
    short_summaries = int((summaries.fillna("").astype(str).str.strip().str.len() < 40).sum())
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    missing_ages = int(ages.isna().sum())
    checks = {
        "row_count": {"passed": row_count > 0, "value": row_count, "expected": "> 0"},
        "paper_id_not_null": {"passed": missing_ids == 0, "invalid_rows": missing_ids},
        "paper_id_unique": {"passed": duplicate_rows == 0, "duplicate_rows": duplicate_rows},
        "title_not_null": {"passed": missing_titles == 0, "invalid_rows": missing_titles},
        "summary_min_length": {"passed": short_summaries == 0, "min_chars": 40, "invalid_rows": short_summaries},
        "freshness": {"passed": stale_rows == 0 and missing_ages == 0, "threshold_days": settings.freshness_threshold_days, "stale_rows": stale_rows, "missing_age_days": missing_ages},
    }
    result = {"report_name": report_name, "generated_at": now_utc().isoformat(), "total_rows": row_count, "passed": all(check["passed"] for check in checks.values()), "checks": checks}
    write_json(settings.paths.quality_dir / f"{report_name}_quality.json", result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    published = pd.to_datetime(
        df["published"] if "published" in df.columns else pd.Series(None, index=df.index),
        errors="coerce",
        utc=True,
    )
    ages = pd.to_numeric(df["age_days"] if "age_days" in df.columns else pd.Series(None, index=df.index), errors="coerce")
    latest, oldest = published.max(), published.min()
    stale_rows, missing_dates = int((ages > settings.freshness_threshold_days).sum()), int(published.isna().sum())
    result = {
        "generated_at": now_utc().isoformat(), "threshold_days": settings.freshness_threshold_days,
        "latest_published": latest.date().isoformat() if pd.notna(latest) else None,
        "oldest_published": oldest.date().isoformat() if pd.notna(oldest) else None,
        "stale_rows": stale_rows, "missing_published_rows": missing_dates, "total_rows": len(df),
        "is_fresh": len(df) > 0 and stale_rows == 0 and missing_dates == 0,
    }
    write_json(report_path, result)
    return result
