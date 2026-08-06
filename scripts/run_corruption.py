from datetime import UTC, datetime
import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks


def main():
    print("=== Running Checkpoint 5 (Role 3: Corruption Flow) ===")
    settings = load_settings()

    clean_json_path = settings.paths.clean_json
    if clean_json_path.exists():
        print(f"Loading clean dataset from: {clean_json_path}")
        records_json = read_json(clean_json_path)
        df_clean = pd.DataFrame(records_json)
    else:
        print("Clean dataset not found. Re-building from raw records...")
        raw_records = load_raw_records(settings.paths.raw_records_json)
        df_clean = build_clean_dataframe(raw_records, datetime.now(UTC))

    print(f"Baseline clean record count: {len(df_clean)}")

    log_path = settings.paths.corruption_log
    df_corrupted = corrupt_clean_dataframe(df_clean, log_path)

    corrupted_csv_path = settings.paths.corrupted_clean_csv
    corrupted_json_path = settings.paths.corrupted_clean_json

    write_csv(df_corrupted, corrupted_csv_path)
    write_json(corrupted_json_path, df_corrupted.to_dict(orient="records"))

    print(f"Corrupted DataFrame count: {len(df_corrupted)}")
    print(f"Saved corrupted CSV: {corrupted_csv_path}")
    print(f"Saved corrupted JSON: {corrupted_json_path}")
    print(f"Saved corruption log: {log_path}")

    q_report = run_data_quality_checks(df_corrupted, settings, "corrupted")
    print(f"Corrupted Data Quality Check passed: {q_report['passed']}")
    for check_name, details in q_report["checks"].items():
        status = "PASSED" if details.get("passed") else "FAILED"
        print(f" - [{status}] {check_name}: {details}")

    print("=== Corruption Flow Completed Successfully! ===")


if __name__ == "__main__":
    main()
