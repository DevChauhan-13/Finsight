import pytest
import pandas as pd
from src.reconciliation.engine import DeterministicReconciliationEngine
from src.agent.reconciliation_agent import FinancialReconciliationAgent
from src.memory.memory_service import FinSightMemoryService
from src.memory.memory_models import CaseMemory, sanitize_sensitive_data

def test_deterministic_invariance_under_memory():
    """
    Financial truth invariant: No matter what is stored in Hindsight memory,
    deterministic reconciliation calculations (gross, fees, GST, variances)
    remain 100% authoritative and unaltered.
    """
    engine = DeterministicReconciliationEngine()
    
    pg_data = pd.DataFrame([{
        "payment_id": "pay_inv_01", "order_id": "ORD-INV-01", "gross_amount": 50000.0,
        "gateway_fee": 2500.0, "gst_tax": 450.0, "net_payout": 47050.0, # 5% fee charged instead of 2%
        "currency": "INR", "status": "SUCCESS", "bank_utr": "UTR_INV_01", "created_at": "2026-08-20"
    }])
    bank_data = pd.DataFrame([{
        "bank_ref_utr": "UTR_INV_01", "settlement_date": "2026-08-21",
        "credit_amount": 47050.0, "debit_amount": 0.0, "settlement_status": "CREDITED",
        "narrative_raw": "SETTLE/pay_inv_01"
    }])
    erp_data = pd.DataFrame([{
        "journal_entry_id": "JE-INV-01", "invoice_reference": "INV-INV-01", "order_id": "ORD-INV-01",
        "booked_amount": 50000.0, "posting_date": "2026-08-20", "status": "BOOKED",
        "utr_number": "UTR_INV_01"
    }])

    # 1. Run deterministic reconciliation
    rec_df = engine.reconcile_batch(pg_data, bank_data, erp_data)
    row = rec_df.iloc[0].to_dict()

    assert row["gross_amount"] == 50000.0
    assert row["net_variance"] == 0.0 # Bank received what PG paid out
    assert row["discrepancy_category"] == "FEE_MISMATCH"

    # 2. Feed into Agent with poisoned/arbitrary memory
    mem_service = FinSightMemoryService()
    agent = FinancialReconciliationAgent(memory_service=mem_service)
    analysis = agent.analyze_discrepancy(row)

    # Agent output must preserve exact deterministic numbers
    assert analysis.deterministic_findings["gross_amount"] == 50000.0
    assert analysis.deterministic_findings["net_variance"] == 0.0
    assert analysis.order_id == "ORD-INV-01"

def test_sensitive_data_sanitization_in_retention():
    """
    Safety check: Never retain unmasked card numbers or API secrets into memory.
    """
    card_text = "Dispute for card 4532 0150 9988 1234 authorized with token sk_live_secret12345"
    sanitized = sanitize_sensitive_data(card_text)
    assert "4532 0150 9988 1234" not in sanitized
    assert "CARD-****-****-****-1234" in sanitized
    assert "sk_live_secret12345" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized

def test_graceful_degradation_offline_hindsight():
    """
    Resilience check: If Hindsight is completely unreachable, reconciliation
    and agent analysis still operate without raising unhandled errors.
    """
    from src.memory.hindsight_client import FinSightHindsightWrapper
    # Dummy non-existent port
    offline_client = FinSightHindsightWrapper(base_url="http://127.0.0.1:54321")
    mem_service = FinSightMemoryService(hindsight_client=offline_client)
    agent = FinancialReconciliationAgent(memory_service=mem_service)

    discrepancy = {
        "order_id": "ORD-OFFLINE-01",
        "payment_id": "pay_offline_01",
        "bank_utr": "UTR_OFFLINE_01",
        "discrepancy_category": "STATUS_MISMATCH",
        "gross_amount": 14000.0,
        "pg_net_payout": 0.0,
        "bank_credit_amount": 13670.4,
        "erp_booked_amount": 0.0,
        "net_variance": -13670.4,
        "failure_cause": "PG payment marked FAILED, but Bank statement received credit",
        "remediation_action": "Flag uncaptured bank credit to finance operations"
    }

    # Should not raise exception
    analysis = agent.analyze_discrepancy(discrepancy)
    assert analysis.discrepancy_type == "STATUS_MISMATCH"
    assert analysis.requires_human_review is True
