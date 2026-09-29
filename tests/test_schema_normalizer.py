import pytest
import pandas as pd
from src.normalization.schema_normalizer import (
    parse_currency_amount,
    LLMSchemaNormalizer,
    normalize_pg_dataset,
    normalize_bank_dataset,
    normalize_erp_dataset
)

def test_parse_currency_amount():
    assert parse_currency_amount("1600000 paise") == 16000.0
    assert parse_currency_amount("₹15,450.50") == 15450.50
    assert parse_currency_amount("$100.00") == 100.0
    assert parse_currency_amount(2500) == 2500.0
    assert parse_currency_amount(None) == 0.0

def test_rule_normalizer():
    normalizer = LLMSchemaNormalizer()
    normalizer.llm_available = False # Force rule-based fallback

    raw_pg = {
        "pay_id": "pay_test123",
        "order_no": "ORD-TEST-01",
        "amount": "100000 paise", # 1000 INR
        "fee": 20.0,
        "tax": 3.6,
        "utr": "UTR123456",
        "status": "success",
        "timestamp": "2026-08-20 10:00:00"
    }

    norm = normalizer.normalize_pg_record(raw_pg)
    assert norm.payment_id == "pay_test123"
    assert norm.order_id == "ORD-TEST-01"
    assert norm.gross_amount == 1000.0
    assert norm.gateway_fee == 20.0
    assert norm.gst_tax == 3.6
    assert norm.net_payout == 976.4
    assert norm.status == "SUCCESS"

def test_zero_amount_fields_are_not_replaced_by_fallback_values():
    from src.normalization.schema_normalizer import LLMSchemaNormalizer
    record = LLMSchemaNormalizer().normalize_pg_record({
        "payment_id": "p-zero",
        "order_id": "o-zero",
        "gross_amount": 1000,
        "gateway_fee": 0.0,
        "fee": 25.0,
        "gst_tax": 0.0,
        "tax": 4.5,
        "net_payout": 1000.0,
        "net_amount": 970.5,
        "status": "FAILED",
    })
    assert record.gateway_fee == 0.0
    assert record.gst_tax == 0.0
    assert record.net_payout == 1000.0
