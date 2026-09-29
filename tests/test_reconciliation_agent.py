import pytest
from src.agent.reconciliation_agent import FinancialReconciliationAgent
from src.agent.schemas import OperatorOutcomeInput
from src.memory.memory_service import FinSightMemoryService

def test_agent_cold_analysis():
    mem_service = FinSightMemoryService()
    mem_service.clear_all_memories()
    agent = FinancialReconciliationAgent(memory_service=mem_service)

    discrepancy = {
        "order_id": "ORD-COLD-01",
        "payment_id": "pay_cold_01",
        "bank_utr": "UTR_COLD_01",
        "discrepancy_category": "SETTLEMENT_DELAY",
        "gross_amount": 12000.0,
        "pg_net_payout": 11716.8,
        "bank_credit_amount": 0.0,
        "erp_booked_amount": 12000.0,
        "net_variance": 11716.8,
        "failure_cause": "Cleared in PG but missing in Bank statement",
        "remediation_action": "Track payout node for T+2 settlement arrival"
    }

    analysis = agent.analyze_discrepancy(discrepancy)
    assert analysis.case_id == "CASE-ORD-COLD-01"
    assert analysis.memory_influenced is False
    assert len(analysis.memory_matches) == 0
    assert "No prior historical cases found in Hindsight" in analysis.reasoning_summary
    assert analysis.requires_human_review is True

def test_agent_record_resolution_loop():
    mem_service = FinSightMemoryService()
    mem_service.clear_all_memories()
    agent = FinancialReconciliationAgent(memory_service=mem_service)

    discrepancy = {
        "order_id": "ORD-LOOP-01",
        "payment_id": "pay_loop_01",
        "bank_utr": "UTR_LOOP_01",
        "discrepancy_category": "FEE_MISMATCH",
        "gross_amount": 20000.0,
        "pg_net_payout": 18820.0,
        "bank_credit_amount": 18820.0,
        "erp_booked_amount": 20000.0,
        "net_variance": 708.0,
        "failure_cause": "Gateway fee 5% instead of 2%",
        "remediation_action": "Raise billing dispute"
    }

    analysis = agent.analyze_discrepancy(discrepancy)

    outcome = OperatorOutcomeInput(
        case_id=analysis.case_id,
        outcome_status="RESOLVED",
        final_resolution="Gateway credited variance back to merchant settlement account.",
        operator_notes="Dispute approved using Master Agreement Schedule B.",
        evidence_submitted=["Master Agreement Schedule B", "Settlement Batch ID #9981"]
    )

    rec_result = agent.record_operator_resolution(analysis.case_id, outcome)
    assert rec_result["status"] == "success"
    assert rec_result["retained_in_hindsight"] is True
