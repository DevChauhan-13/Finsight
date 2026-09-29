import re
import os
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import pandas as pd

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Unified Schema Models
# -------------------------------------------------------------------

class NormalizedPGRecord(BaseModel):
    payment_id: str
    order_id: str
    gross_amount: float
    gateway_fee: float
    gst_tax: float
    net_payout: float
    currency: str = "INR"
    status: str
    bank_utr: str
    created_at: str

class NormalizedBankRecord(BaseModel):
    bank_ref_utr: str
    settlement_date: str
    credit_amount: float
    debit_amount: float
    settlement_status: str
    narrative_raw: str

class NormalizedERPRecord(BaseModel):
    journal_entry_id: str
    invoice_reference: str
    order_id: str
    booked_amount: float
    posting_date: str
    status: str
    utr_number: str

# -------------------------------------------------------------------
# Helper Parsing Functions (Rule-based & Cleaning)
# -------------------------------------------------------------------



def _first_present(mapping: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first non-null/non-NaN value, preserving legitimate zeros."""
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


def parse_currency_amount(val: Any) -> float:
    """
    Parses messy amount formats:
    - 1600000 paise -> 16000.0
    - '₹16,000.00' -> 16000.0
    - '$100.00' -> 100.0
    - 16000.0 -> 16000.0
    """
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    
    # Check for paise suffix or pattern
    if "paise" in val_str.lower():
        num_str = re.sub(r"[^\d.]", "", val_str)
        try:
            return round(float(num_str) / 100.0, 2)
        except ValueError:
            return 0.0

    # Remove currency symbols and commas
    cleaned = re.sub(r"[^\d.-]", "", val_str)
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0

# -------------------------------------------------------------------
# LLM Schema Normalizer Class
# -------------------------------------------------------------------

class LLMSchemaNormalizer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.llm_available = bool(self.api_key)

    def normalize_pg_record(self, raw_row: Dict[str, Any]) -> NormalizedPGRecord:
        """
        Normalizes a raw Payment Gateway record using LLM or rule-based fallback.
        """
        if self.llm_available:
            try:
                return self._normalize_pg_llm(raw_row)
            except Exception as e:
                logger.warning(f"LLM normalization failed, using fallback: {e}")
        
        return self._normalize_pg_rule(raw_row)

    def _normalize_pg_rule(self, raw_row: Dict[str, Any]) -> NormalizedPGRecord:
        pay_id = str(raw_row.get("payment_id") or raw_row.get("pay_id") or raw_row.get("tx_id") or "")
        order_id = str(raw_row.get("order_id") or raw_row.get("order_no") or raw_row.get("ref_order") or "")
        
        gross = parse_currency_amount(_first_present(raw_row, "gross_amount", "amount", default=0.0))
        fee = parse_currency_amount(_first_present(raw_row, "gateway_fee", "fee", default=0.0))
        gst = parse_currency_amount(_first_present(raw_row, "gst_tax", "tax", default=0.0))
        net = parse_currency_amount(_first_present(raw_row, "net_payout", "net_amount", default=(gross - fee - gst)))
        
        utr = str(raw_row.get("bank_utr") or raw_row.get("utr") or raw_row.get("reference_id") or "")
        status = str(raw_row.get("status") or "SUCCESS").upper()
        created_at = str(raw_row.get("created_at") or raw_row.get("timestamp") or "")

        return NormalizedPGRecord(
            payment_id=pay_id,
            order_id=order_id,
            gross_amount=gross,
            gateway_fee=fee,
            gst_tax=gst,
            net_payout=net,
            currency=str(raw_row.get("currency", "INR")).upper(),
            status=status,
            bank_utr=utr,
            created_at=created_at
        )

    def _normalize_pg_llm(self, raw_row: Dict[str, Any]) -> NormalizedPGRecord:
        """
        LLM schema normalization using Gemini API if key is present.
        """
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
Extract and normalize the following payment gateway record into a standardized JSON object matching this schema:
{{
    "payment_id": str,
    "order_id": str,
    "gross_amount": float (in INR),
    "gateway_fee": float (in INR),
    "gst_tax": float (in INR),
    "net_payout": float (in INR),
    "currency": str,
    "status": str (SUCCESS/FAILED/REFUNDED),
    "bank_utr": str,
    "created_at": str
}}

Note: Convert paise amounts to INR float by dividing by 100. Remove currency symbols.

Raw input record:
{json.dumps(raw_row)}

Return ONLY valid JSON.
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean potential markdown ```json blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].strip()
            
        data = json.loads(text)
        return NormalizedPGRecord(**data)

    def normalize_bank_record(self, raw_row: Dict[str, Any]) -> NormalizedBankRecord:
        utr = str(raw_row.get("bank_ref_utr") or raw_row.get("utr") or raw_row.get("reference_id") or raw_row.get("ref_no") or "")
        date_str = str(raw_row.get("settlement_date") or raw_row.get("date") or "")
        credit = parse_currency_amount(_first_present(raw_row, "credit_amount", "credit", default=0.0))
        debit = parse_currency_amount(_first_present(raw_row, "debit_amount", "debit", default=0.0))
        status = str(raw_row.get("settlement_status") or raw_row.get("status") or "CREDITED").upper()
        narrative = str(raw_row.get("narrative_raw") or raw_row.get("description") or "")

        return NormalizedBankRecord(
            bank_ref_utr=utr,
            settlement_date=date_str,
            credit_amount=credit,
            debit_amount=debit,
            settlement_status=status,
            narrative_raw=narrative
        )

    def normalize_erp_record(self, raw_row: Dict[str, Any]) -> NormalizedERPRecord:
        je_id = str(raw_row.get("journal_entry_id") or raw_row.get("entry_id") or "")
        inv_ref = str(raw_row.get("invoice_reference") or raw_row.get("invoice_no") or "")
        order_id = str(raw_row.get("order_id") or raw_row.get("ref_order") or "")
        amount = parse_currency_amount(_first_present(raw_row, "booked_amount", "amount", default=0.0))
        posting_date = str(raw_row.get("posting_date") or raw_row.get("date") or "")
        status = str(raw_row.get("status") or "BOOKED").upper()
        utr = str(raw_row.get("utr_number") or raw_row.get("utr") or "")

        return NormalizedERPRecord(
            journal_entry_id=je_id,
            invoice_reference=inv_ref,
            order_id=order_id,
            booked_amount=amount,
            posting_date=posting_date,
            status=status,
            utr_number=utr
        )

# -------------------------------------------------------------------
# DataFrame Batch Normalizers
# -------------------------------------------------------------------

def normalize_pg_dataset(pg_df: pd.DataFrame, use_llm: bool = False) -> pd.DataFrame:
    normalizer = LLMSchemaNormalizer()
    if not use_llm:
        normalizer.llm_available = False
        
    records = []
    for _, row in pg_df.iterrows():
        norm = normalizer.normalize_pg_record(row.to_dict())
        records.append(norm.model_dump())
    return pd.DataFrame(records)

def normalize_bank_dataset(bank_df: pd.DataFrame, use_llm: bool = False) -> pd.DataFrame:
    normalizer = LLMSchemaNormalizer()
    records = []
    for _, row in bank_df.iterrows():
        norm = normalizer.normalize_bank_record(row.to_dict())
        records.append(norm.model_dump())
    return pd.DataFrame(records)

def normalize_erp_dataset(erp_json_data: dict, use_llm: bool = False) -> pd.DataFrame:
    normalizer = LLMSchemaNormalizer()
    entries = erp_json_data.get("entries", erp_json_data if isinstance(erp_json_data, list) else [])
    records = []
    for row in entries:
        norm = normalizer.normalize_erp_record(row)
        records.append(norm.model_dump())
    return pd.DataFrame(records)
