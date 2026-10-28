"""Unit tests for the generation quality evaluation harness."""

from pathlib import Path
from evaluation.run_generation_eval import evaluate_generation


def test_evaluate_generation_quality(tmp_path):
    dataset_file = Path("backend/evaluation/dataset.json")
    out_file = tmp_path / "gen_results.json"
    docs_file = tmp_path / "GENERATION_EVALUATION.md"

    results = evaluate_generation(
        dataset_path=dataset_file,
        output_path=out_file,
        docs_output_path=docs_file,
    )

    metrics = results["summary_metrics"]
    assert metrics["total_queries"] == 32
    assert metrics["answerable_queries"] == 24
    assert metrics["unanswerable_queries"] == 8

    # Groundedness and citation checks
    assert metrics["faithfulness_rate"] >= 0.90, "Faithfulness should be at least 90%"
    assert metrics["hallucination_rate"] <= 0.10, "Hallucination rate should be at most 10%"
    assert metrics["citation_accuracy"] == 1.0, "Citation accuracy should be 100%"
    assert metrics["abstention_accuracy"] == 1.0, "Abstention accuracy should be 100%"

    assert out_file.exists()
    assert docs_file.exists()
