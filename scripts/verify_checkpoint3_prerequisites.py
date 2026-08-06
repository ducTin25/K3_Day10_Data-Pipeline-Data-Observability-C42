import sys

from core.config import load_settings
from core.utils import read_json


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== Auditing Checkpoint 3 Prerequisites for Role 3 (Cleaning & Data Foundation) ===")
    settings = load_settings()

    raw_records = read_json(settings.paths.raw_records_json)
    clean_records = read_json(settings.paths.clean_json)

    quality_path = settings.paths.quality_dir / "baseline_quality.json"
    quality_report = read_json(quality_path) if quality_path.exists() else {}

    freshness_path = settings.paths.freshness_report
    freshness_report = read_json(freshness_path) if freshness_path.exists() else {}

    print(f"1. Raw Records Count: {len(raw_records)} | Clean Records Count: {len(clean_records)}")
    has_required_columns = all("age_days" in r and "text_for_embedding" in r for r in clean_records)
    print(f"2. Clean schema contains age_days & text_for_embedding: {has_required_columns}")
    print(f"3. Data Quality Gate (baseline_quality.json) passed: {quality_report.get('passed')}")
    print(f"4. Data Freshness Gate (freshness_report.json) is_fresh: {freshness_report.get('is_fresh')}")

    is_ready = (
        len(raw_records) == len(clean_records)
        and has_required_columns
        and quality_report.get("passed") is True
        and freshness_report.get("is_fresh") is True
    )

    if is_ready:
        print("[SUCCESS] Role 3 Checkpoint 3 prerequisites are 100% READY!")
    else:
        print("[WARN] Prerequisites incomplete.")


if __name__ == "__main__":
    main()
