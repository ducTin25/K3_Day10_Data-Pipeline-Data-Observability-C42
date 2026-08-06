import sys

from core.config import load_settings
from core.utils import read_json


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== Checkpoint 2 - Role 3 (Cleaning & Data Model Contract Audit) ===")
    settings = load_settings()

    clean_data = read_json(settings.paths.clean_json)
    test_data = read_json(settings.paths.eval_testset)

    print(f"Total Clean Records Loaded: {len(clean_data)}")

    paper_ids = [d["paper_id"] for d in clean_data]
    duplicate_ids = [pid for pid in set(paper_ids) if paper_ids.count(pid) > 1]
    empty_embeddings = [d["paper_id"] for d in clean_data if not str(d.get("text_for_embedding", "")).strip()]

    print(f"1. Duplicate paper_id count: {len(duplicate_ids)}")
    print(f"2. Empty text_for_embedding count: {len(empty_embeddings)}")

    clean_id_set = set(paper_ids)
    invalid_test_samples = [
        sample["id"] for sample in test_data if not set(sample["ground_truth_doc_ids"]).issubset(clean_id_set)
    ]

    print(f"3. Evaluation samples with missing ground truth IDs: {len(invalid_test_samples)}")

    required_schema_fields = {
        "paper_id",
        "title",
        "summary",
        "published",
        "authors_joined",
        "categories_joined",
        "text_for_embedding",
    }
    missing_fields = [
        d["paper_id"] for d in clean_data if not required_schema_fields.issubset(set(d.keys()))
    ]
    print(f"4. Records with missing schema fields: {len(missing_fields)}")

    is_valid = (
        len(duplicate_ids) == 0
        and len(empty_embeddings) == 0
        and len(invalid_test_samples) == 0
        and len(missing_fields) == 0
    )

    if is_valid:
        print("[SUCCESS] Role 3 Checkpoint 2 contract verification passed 100%!")
    else:
        print("[FAIL] Schema contract issues detected.")


if __name__ == "__main__":
    main()

