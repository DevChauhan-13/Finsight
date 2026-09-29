import pytest
import pandas as pd
from src.metrics.diagnostics import ReconciliationDiagnostics

def test_diagnostics_calculation():
    rec_df = pd.DataFrame([
        {
            "order_id": "ORD-1", "payment_id": "P1", "bank_utr": "U1",
            "reconciliation_status": "RECONCILED", "discrepancy_category": "NONE",
            "gross_amount": 1000.0, "pg_net_payout": 976.4, "bank_credit_amount": 976.4,
            "erp_booked_amount": 1000.0, "net_variance": 0.0,
            "failure_cause": "", "remediation_action": ""
        },
        {
            "order_id": "ORD-2", "payment_id": "P2", "bank_utr": "U2",
            "reconciliation_status": "DISCREPANCY", "discrepancy_category": "FEE_MISMATCH",
            "gross_amount": 2000.0, "pg_net_payout": 1900.0, "bank_credit_amount": 1900.0,
            "erp_booked_amount": 2000.0, "net_variance": 0.0,
            "failure_cause": "Fee overcharge", "remediation_action": "Dispute"
        }
    ])

    diag = ReconciliationDiagnostics()
    perf, stats, exc_df = diag.compute_metrics(rec_df, norm_latency_ms=10.0, rec_latency_ms=5.0)

    assert perf.total_records == 2
    assert perf.total_pipeline_latency_ms == 15.0
    assert stats.reconciled_count == 1
    assert stats.discrepancy_count == 1
    assert stats.match_rate_pct == 50.0
    assert len(exc_df) == 1
    assert exc_df.iloc[0]["order_id"] == "ORD-2"
