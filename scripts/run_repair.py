from core.config import load_settings
from ingestion.repair import repair_data_from_raw
from observability.quality import run_data_quality_checks


def main():
    print("=== Running Checkpoint 6 (Role 3: Data Repair & Quality Verification) ===")
    settings = load_settings()

    df_repaired, report = repair_data_from_raw(settings)

    print(f"Re-processed raw records. Repaired DataFrame count: {len(df_repaired)}")
    print(f"Saved repaired CSV: {settings.paths.repaired_clean_csv}")
    print(f"Saved repaired JSON: {settings.paths.repaired_clean_json}")
    print(f"Saved repaired metrics report: {settings.paths.repaired_metrics}")

    q_report = run_data_quality_checks(df_repaired, settings, "repaired")
    print(f"Repaired Data Quality Check passed: {q_report['passed']}")
    for check_name, details in q_report["checks"].items():
        status = "PASSED" if details.get("passed") else "FAILED"
        print(f" - [{status}] {check_name}: {details}")

    print("=== Data Repair Completed Successfully! ===")


if __name__ == "__main__":
    main()
