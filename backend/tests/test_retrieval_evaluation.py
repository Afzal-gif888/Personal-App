"""Unit tests for the retrieval evaluation dataset and harness."""

import json
from pathlib import Path
from evaluation.run_retrieval_eval import run_evaluation


def test_dataset_structure_and_constraints():
    dataset_file = Path("backend/evaluation/dataset.json")
    assert dataset_file.exists(), "Dataset file must exist"
    
    with open(dataset_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "corpus" in data
    assert "queries" in data

    chunks = [c for doc in data["corpus"] for c in doc["chunks"]]
    assert len(chunks) >= 20, "Corpus must have at least 20 chunks"

    queries = data["queries"]
    assert len(queries) >= 30, f"Expected at least 30 queries, got {len(queries)}"

    ans_queries = [q for q in queries if q["is_answerable"]]
    unans_queries = [q for q in queries if not q["is_answerable"]]

    assert len(unans_queries) >= 8, f"Expected at least 8 unanswerable queries, got {len(unans_queries)}"
    assert len(ans_queries) >= 20, f"Expected at least 20 answerable queries, got {len(ans_queries)}"

    chunk_ids = {c["chunk_id"] for c in chunks}
    for q in ans_queries:
        assert q["expected_chunk_id"] in chunk_ids, f"Expected chunk {q['expected_chunk_id']} not found in corpus"


def test_run_retrieval_eval_harness(tmp_path):
    dataset_file = Path("backend/evaluation/dataset.json")
    out_file = tmp_path / "results.json"
    docs_file = tmp_path / "RETRIEVAL_EVALUATION.md"

    results = run_evaluation(
        dataset_path=dataset_file,
        output_path=out_file,
        docs_output_path=docs_file,
        provider_name="calibrated",
        similarity_floor=0.65,
    )

    metrics = results["summary_metrics"]
    assert "hit_at_1" in metrics
    assert "hit_at_3" in metrics
    assert "hit_at_5" in metrics
    assert "mrr" in metrics
    assert "unanswerable_rejection_at_floor" in metrics
    assert metrics["hit_at_1"] > 0.8
    assert metrics["mrr"] > 0.8

    sweep = results["threshold_sweep"]
    assert len(sweep) == 7  # 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80
    assert sweep[0]["threshold"] == 0.50
    assert sweep[-1]["threshold"] == 0.80

    assert out_file.exists()
    assert docs_file.exists()
