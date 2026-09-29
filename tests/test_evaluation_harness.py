import pytest
from src.evaluation.evaluation_harness import FinSightEvaluationHarness

def test_evaluation_benchmark_execution():
    harness = FinSightEvaluationHarness()
    metrics = harness.run_benchmark()

    assert metrics.total_test_cases == 3
    assert metrics.cold_memory_influenced_count == 0
    assert metrics.warm_memory_influenced_count == 3
    assert metrics.memory_retrieval_rate_pct == 100.0
    assert metrics.evidence_augmentation_rate_pct == 100.0
    assert metrics.average_confidence_warm > metrics.average_confidence_cold
    assert metrics.operator_time_saved_est_minutes > 0.0
