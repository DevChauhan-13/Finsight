import pytest
from src.memory.memory_service import FinSightMemoryService
from src.memory.memory_models import CaseMemory, sanitize_sensitive_data

def test_sanitize_sensitive_data():
    raw_text = "Card number 4111-2222-3333-4444 and api_key='sk_live_1234567890abcdef' should be masked."
    sanitized = sanitize_sensitive_data(raw_text)
    assert "4111-2222-3333-4444" not in sanitized
    assert "CARD-****-****-****-4444" in sanitized
    assert "sk_live_1234567890abcdef" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized

def test_memory_service_case_lifecycle():
    service = FinSightMemoryService()
    service.clear_all_memories()

    case = CaseMemory(
        case_id="CASE-TEST-001",
        order_id="ORD-TEST-001",
        payment_id="pay_test_001",
        merchant_id="MERCHANT_APEX",
        merchant_name="Apex Retail",
        gateway="Razorpay",
        discrepancy_type="FEE_MISMATCH",
        gross_amount=10000.0,
        net_variance=354.0,
        deterministic_cause="Fee charged 5% instead of contracted 2%",
        resolution_attempted="Dispute ticket with Schedule B",
        evidence_used=["Merchant Contract Schedule B", "Settlement Batch ID"],
        final_resolution="Gateway acknowledged pricing bug and refunded difference.",
        outcome_status="RESOLVED",
        operator_notes="Dispute accepted in 24 hours.",
        was_successful=True
    )

    res = service.retain_case_experience(case)
    assert res["status"] == "success"

    recalls = service.recall_similar_exceptions(
        discrepancy_type="FEE_MISMATCH",
        gateway="Razorpay",
        merchant_name="Apex Retail",
        failure_cause="Fee charged 5% instead of contracted 2%"
    )

    assert len(recalls) >= 1
    assert "CASE-TEST-001" in recalls[0]["text"]
