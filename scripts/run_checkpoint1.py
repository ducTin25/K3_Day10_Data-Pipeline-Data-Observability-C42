from datetime import UTC, datetime
from core.config import load_settings
from ingestion.cleaning import build_clean_dataframe, save_clean_artifacts
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks


def main():
    print("=== Running Checkpoint 1 (Role 3: Data Cleaning & Quality Gates) ===")
    settings = load_settings()

    print(f"Loading raw records from: {settings.paths.raw_records_json}")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    print(f"Loaded {len(raw_records)} raw records.")

    run_date = datetime.now(UTC)
    df_clean = build_clean_dataframe(raw_records, run_date)
    print(f"Cleaned DataFrame produced {len(df_clean)} records.")

    csv_path, json_path = save_clean_artifacts(df_clean, settings)
    print(f"Saved clean CSV artifact: {csv_path}")
    print(f"Saved clean JSON artifact: {json_path}")

    q_report = run_data_quality_checks(df_clean, settings, "baseline")
    print(f"Data Quality Report passed: {q_report['passed']}")
    for check_name, details in q_report["checks"].items():
        status = "PASSED" if details.get("passed") else "FAILED"
        print(f" - [{status}] {check_name}: {details}")

    f_report = build_freshness_report(df_clean, settings, settings.paths.freshness_report)
    print(f"Freshness Report is_fresh: {f_report['is_fresh']}")
    print("=== Checkpoint 1 Completed Successfully! ===")


if __name__ == "__main__":
    main()
