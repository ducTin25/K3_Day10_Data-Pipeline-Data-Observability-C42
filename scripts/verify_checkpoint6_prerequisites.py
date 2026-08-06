import sys

from core.config import load_settings


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== Checkpoint 6 Prerequisites Audit - Role 3 (Repair & Comparison) ===")
    settings = load_settings()

    raw_exists = settings.paths.raw_records_json.exists()
    corrupted_exists = settings.paths.corrupted_clean_json.exists()
    log_exists = settings.paths.corruption_log.exists()
    baseline_metrics_exists = settings.paths.baseline_metrics.exists()
    corrupted_metrics_exists = settings.paths.corrupted_metrics.exists()

    print(f"1. Raw Records Snapshot present: {raw_exists}")
    print(f"2. Corrupted Dataset present: {corrupted_exists}")
    print(f"3. Corruption Log present: {log_exists}")
    print(f"4. Baseline Metrics present: {baseline_metrics_exists}")
    print(f"5. Corrupted Metrics present: {corrupted_metrics_exists}")

    is_ready = raw_exists and corrupted_exists and log_exists and baseline_metrics_exists and corrupted_metrics_exists

    if is_ready:
        print("[SUCCESS] Role 3 Checkpoint 6 prerequisites are 100% READY!")
    else:
        print("[WARN] Prerequisites incomplete.")


if __name__ == "__main__":
    main()
