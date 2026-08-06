import sys

from core.config import load_settings
from core.utils import read_json


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== Checkpoint 4 - Role 3 (Baseline Metrics Verification & CP5 Readiness) ===")
    settings = load_settings()

    metrics_path = settings.paths.baseline_metrics
    if not metrics_path.exists():
        print("[FAIL] Baseline metrics file missing!")
        return

    metrics = read_json(metrics_path)
    print("Baseline Metrics Audit:")
    print(f" - Samples: {metrics.get('samples')}")
    print(f" - Retrieval Hit Rate: {metrics.get('retrieval_hit_rate')}")
    print(f" - Mean Token F1: {metrics.get('mean_token_f1'):.3f}")
    print(f" - Judge Accuracy: {metrics.get('judge_accuracy'):.3f}")

    has_corruption_logic = settings.paths.project_dir / "src" / "ingestion" / "corruption.py"
    has_repair_logic = settings.paths.project_dir / "src" / "ingestion" / "repair.py"

    print(f" - Corruption module present: {has_corruption_logic.exists()}")
    print(f" - Repair module present: {has_repair_logic.exists()}")

    if metrics.get("samples", 0) > 0 and has_corruption_logic.exists() and has_repair_logic.exists():
        print("[SUCCESS] Role 3 Checkpoint 4 verification passed! Fully prepared for Checkpoint 5!")
    else:
        print("[WARN] Incomplete readiness.")


if __name__ == "__main__":
    main()
