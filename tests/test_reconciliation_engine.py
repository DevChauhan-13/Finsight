import pytest
import pandas as pd
from src.reconciliation.engine import DeterministicReconciliationEngine

def test_reconcile_clean_record():
    pg_data = pd.DataFrame([{
        "payment_id": "pay_01", "order_id": "ORD-01", "gross_amount": 10000.0,
        "gateway_fee": 200.0, "gst_tax": 36.0, "net_payout": 9764.0,
        "currency": "INR", "status": "SUCCESS", "bank_utr": "UTR01", "created_at": "2026-08-20"
    }])

    bank_data = pd.DataFrame([{
        "bank_ref_utr": "UTR01", "settlement_date": "2026-08-21",
        "credit_amount": 9764.0, "debit_amount": 0.0, "settlement_status": "CREDITED",
        "narrative_raw": "SETTLE/pay_01"
    }])

    erp_data = pd.DataFrame([{
        "journal_entry_id": "JE-01", "invoice_reference": "INV-01", "order_id": "ORD-01",
        "booked_amount": 10000.0, "posting_date": "2026-08-20", "status": "BOOKED",
        "utr_number": "UTR01"
    }])

    engine = DeterministicReconciliationEngine()
    result_df = engine.reconcile_batch(pg_data, bank_data, erp_data)

    assert len(result_df) == 1
    row = result_df.iloc[0]
    assert row["reconciliation_status"] == "RECONCILED"
    assert row["discrepancy_category"] == "NONE"
    assert row["net_variance"] == 0.0

def test_fee_mismatch():
    pg_data = pd.DataFrame([{
        "payment_id": "pay_02", "order_id": "ORD-02", "gross_amount": 10000.0,
        "gateway_fee": 500.0, "gst_tax": 90.0, "net_payout": 9410.0, # 5% fee charged instead of 2%
        "currency": "INR", "status": "SUCCESS", "bank_utr": "UTR02", "created_at": "2026-08-20"
    }])

    bank_data = pd.DataFrame([{
        "bank_ref_utr": "UTR02", "settlement_date": "2026-08-21",
        "credit_amount": 9410.0, "debit_amount": 0.0, "settlement_status": "CREDITED",
        "narrative_raw": "SETTLE/pay_02"
    }])

    erp_data = pd.DataFrame([{
        "journal_entry_id": "JE-02", "invoice_reference": "INV-02", "order_id": "ORD-02",
        "booked_amount": 10000.0, "posting_date": "2026-08-20", "status": "BOOKED",
        "utr_number": "UTR02"
    }])

    engine = DeterministicReconciliationEngine()
    result_df = engine.reconcile_batch(pg_data, bank_data, erp_data)

    assert len(result_df) == 1
    row = result_df.iloc[0]
    assert row["reconciliation_status"] == "DISCREPANCY"
    assert row["discrepancy_category"] == "FEE_MISMATCH"
    assert "Gateway fee charged" in row["failure_cause"]

def test_missing_bank_reference_is_not_misclassified_as_settlement_delay():
    import pandas as pd
    from src.reconciliation.engine import DeterministicReconciliationEngine

    pg = pd.DataFrame([{
        "payment_id": "pay_ref_01", "order_id": "ORD-REF-01", "gross_amount": 8500.0,
        "gateway_fee": 170.0, "gst_tax": 30.6, "net_payout": 8299.4,
        "status": "SUCCESS", "bank_utr": "UTR_EXPECTED_01", "created_at": "2026-08-21 02:00:00"
    }])
    bank = pd.DataFrame([{
        "bank_ref_utr": "MISSING_N/A", "credit_amount": 8299.4, "debit_amount": 0.0,
        "settlement_status": "CREDITED", "narrative_raw": "CMS/BULK_PAYOUT_UNKNOWN_REF"
    }])
    erp = pd.DataFrame([{
        "order_id": "ORD-REF-01", "booked_amount": 8500.0, "posting_date": "2026-08-21", "status": "BOOKED"
    }])

    result = DeterministicReconciliationEngine().reconcile_batch(pg, bank, erp).iloc[0]
    assert result["discrepancy_category"] == "MISSING_BANK_REF"


def test_fee_overcharge_is_exposed_separately_from_bank_variance():
    import pandas as pd
    from src.reconciliation.engine import DeterministicReconciliationEngine

    pg = pd.DataFrame([{
        "payment_id": "pay_fee_01", "order_id": "ORD-FEE-01", "gross_amount": 20000.0,
        "gateway_fee": 1000.0, "gst_tax": 180.0, "net_payout": 18820.0,
        "status": "SUCCESS", "bank_utr": "UTR_FEE_01", "created_at": "2026-08-21 02:00:00"
    }])
    bank = pd.DataFrame([{
        "bank_ref_utr": "UTR_FEE_01", "credit_amount": 18820.0, "debit_amount": 0.0,
        "settlement_status": "CREDITED"
    }])
    erp = pd.DataFrame([{
        "order_id": "ORD-FEE-01", "booked_amount": 20000.0, "posting_date": "2026-08-21", "status": "BOOKED"
    }])

    result = DeterministicReconciliationEngine().reconcile_batch(pg, bank, erp).iloc[0]
    assert result["discrepancy_category"] == "FEE_MISMATCH"
    assert result["net_variance"] == 0.0
    assert result["fee_overcharge_amount"] == 708.0


def test_seeded_exception_set_matches_expected_categories():
    import json
    import pandas as pd
    from src.normalization.schema_normalizer import (
        normalize_pg_dataset,
        normalize_bank_dataset,
        normalize_erp_dataset,
    )
    from src.reconciliation.engine import DeterministicReconciliationEngine

    pg = normalize_pg_dataset(pd.read_csv("data/pg_transactions.csv"))
    bank = normalize_bank_dataset(pd.read_csv("data/bank_settlements.csv"))
    erp = normalize_erp_dataset(json.load(open("data/erp_ledger.json", encoding="utf-8")))
    result = DeterministicReconciliationEngine().reconcile_batch(pg, bank, erp)

    expected = {
        "ORD-2026-0046": "FEE_MISMATCH",
        "ORD-2026-0047": "SETTLEMENT_DELAY",
        "ORD-2026-0048": "MISSING_BANK_REF",
        "ORD-2026-0049": "ERP_AMOUNT_MISMATCH",
        "ORD-2026-0050": "REFUND_UNACCOUNTED",
        "ORD-2026-0051": "STATUS_MISMATCH",
        "ORD-2026-0052": "PARTIAL_HOLD",
        "ORD-2026-0053": "DUPLICATE_ENTRY",
        "ORD-2026-0055": "TIMING_OUT_OF_PERIOD",
    }

    for order_id, category in expected.items():
        matches = result[result["order_id"] == order_id]
        assert not matches.empty
        assert (matches["discrepancy_category"] == category).any(), order_id

    fee_row = result[result["order_id"] == "ORD-2026-0046"].iloc[0]
    assert fee_row["net_variance"] == 0.0
    assert fee_row["fee_overcharge_amount"] == 708.0

    dup_rows = result[result["order_id"] == "ORD-2026-0053"]
    assert (dup_rows["discrepancy_category"] == "DUPLICATE_ENTRY").any()
