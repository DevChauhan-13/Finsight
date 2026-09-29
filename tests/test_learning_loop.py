import pytest
from src.agent.reconciliation_agent import FinancialReconciliationAgent
from src.agent.schemas import OperatorOutcomeInput
from src.memory.memory_service import FinSightMemoryService

def test_complete_learning_loop_behavioral_change():
    """
    Validates that memory genuinely changes agent behavior:
    1. Cold start: Agent gives generic advice (Memory Used = NO)
    2. Resolution is recorded and retained into Hindsight
    3. Warm case: Agent retrieves memory and provides contextual recommendation (Memory Used = YES)
    """
    mem_service = FinSightMemoryService()
    mem_service.clear_all_memories()
    agent = FinancialReconciliationAgent(memory_service=mem_service)

    # Case A: First encounter of FEE_MISMATCH
    case_a = {
        "order_id": "ORD-LEARN-01",
        "payment_id": "pay_learn_01",
        "bank_utr": "UTR_LEARN_01",
        "discrepancy_category": "FEE_MISMATCH",
        "gross_amount": 10000.0,
        "pg_net_payout": 9410.0,
        "bank_credit_amount": 9410.0,
        "erp_booked_amount": 10000.0,
        "net_variance": 354.0,
        "failure_cause": "Fee charged 5% instead of 2%",
        "remediation_action": "Raise fee dispute billing ticket with Payment Gateway."
    }

    # Step 1: Cold analysis
    analysis_cold = agent.analyze_discrepancy(case_a)
    assert analysis_cold.memory_influenced is False
    assert len(analysis_cold.memory_matches) == 0
    assert "No prior historical cases found in Hindsight" in analysis_cold.reasoning_summary

    # Step 2: Record successful human resolution and retain into Hindsight
    outcome = OperatorOutcomeInput(
        case_id=analysis_cold.case_id,
        outcome_status="RESOLVED",
        final_resolution="Gateway acknowledged billing MDR bug and credited ₹354 difference in 24 hours.",
        operator_notes="Must cite Master Merchant Agreement Schedule B and Settlement Batch ID.",
        evidence_submitted=["Master Merchant Agreement Schedule B", "Settlement Batch ID #BCH-7721"]
    )
    agent.record_operator_resolution(analysis_cold.case_id, outcome)

    # Step 3: New similar Case B arrives
    case_b = {
        "order_id": "ORD-LEARN-02",
        "payment_id": "pay_learn_02",
        "bank_utr": "UTR_LEARN_02",
        "discrepancy_category": "FEE_MISMATCH",
        "gross_amount": 25000.0,
        "pg_net_payout": 23525.0,
        "bank_credit_amount": 23525.0,
        "erp_booked_amount": 25000.0,
        "net_variance": 885.0,
        "failure_cause": "Fee charged 5% instead of 2%",
        "remediation_action": "Raise fee dispute billing ticket with Payment Gateway."
    }

    analysis_warm = agent.analyze_discrepancy(case_b)

    # Step 4: Validate behavioral difference!
    assert analysis_warm.memory_influenced is True
    assert len(analysis_warm.memory_matches) >= 1
    assert "Master Merchant Agreement Schedule B" in analysis_warm.recommended_action
    assert "Hindsight retrieved" in analysis_warm.reasoning_summary
    assert "Master Merchant Agreement Schedule B" in analysis_warm.supporting_evidence
    assert analysis_warm.confidence > analysis_cold.confidence
