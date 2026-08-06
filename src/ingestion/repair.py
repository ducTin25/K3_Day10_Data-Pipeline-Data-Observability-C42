from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import read_json, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records


def repair_data_from_raw(
    settings: Settings,
    run_date: datetime | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Recover the clean dataset by re-running the cleaning pipeline directly from raw records.

    Rules:
    - Never manually edit answers or metrics JSON files.
    - Always rebuild clean schema from trusted raw source snapshot.
    """
    raw_records_path = settings.paths.raw_records_json
    raw_records = load_raw_records(raw_records_path)

    run_dt = run_date or datetime.now(UTC)
    df_repaired = build_clean_dataframe(raw_records, run_dt)

    repaired_csv_path = settings.paths.repaired_clean_csv
    repaired_json_path = settings.paths.repaired_clean_json

    write_csv(df_repaired, repaired_csv_path)
    records = df_repaired.to_dict(orient="records")
    write_json(repaired_json_path, records)

    # Compare with corrupted dataset if present
    corrupted_count = None
    if settings.paths.corrupted_clean_json.exists():
        try:
            corrupted_data = read_json(settings.paths.corrupted_clean_json)
            corrupted_count = len(corrupted_data)
        except Exception:
            corrupted_count = None

    # Compare with baseline dataset if present
    baseline_count = None
    if settings.paths.clean_json.exists():
        try:
            baseline_data = read_json(settings.paths.clean_json)
            baseline_count = len(baseline_data)
        except Exception:
            baseline_count = None

    report = {
        "timestamp": run_dt.isoformat().replace("+00:00", "Z"),
        "source_raw_path": str(raw_records_path),
        "repaired_record_count": len(df_repaired),
        "corrupted_record_count": corrupted_count,
        "baseline_record_count": baseline_count,
        "recovery_status": "FULL_RECOVERY" if baseline_count == len(df_repaired) else "PARTIAL_RECOVERY",
        "notes": "Dataset fully reconstructed from trusted raw records snapshot.",
    }

    write_json(settings.paths.repaired_metrics, report)
    return df_repaired, report
