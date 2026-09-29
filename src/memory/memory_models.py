import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

def sanitize_sensitive_data(text: str) -> str:
    """
    Sanitizes PII, authentication tokens, and credit card numbers from text
    prior to persisting to Hindsight memory banks.
    """
    if not text:
        return ""
    # Mask 16-digit card numbers (preserving last 4 digits)
    text = re.sub(r"\b(?:\d{4}[-\s]?){3}(\d{4})\b", r"CARD-****-****-****-\1", text)
    # Mask API keys / secrets / auth tokens
    text = re.sub(r"(?i)(api[_-]?key|secret|token|password)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", r"\1: [REDACTED_SECRET]", text)
    # Mask customer phone numbers (10 digits)
    text = re.sub(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b", r"[REDACTED_PHONE]", text)
    return text

class CaseMemory(BaseModel):
    """
    Structured domain memory representing a financial discrepancy case
    and its eventual operational resolution.
    """
    case_id: str
    order_id: str
    payment_id: str
    merchant_id: str = "MERCHANT_DEFAULT"
    merchant_name: str = "Apex Retail"
    gateway: str = "Razorpay"
    discrepancy_type: str  # FEE_MISMATCH, SETTLEMENT_DELAY, etc.
    gross_amount: float
    net_variance: float
    deterministic_cause: str
    resolution_attempted: str
    evidence_used: List[str] = Field(default_factory=list)
    final_resolution: str
    outcome_status: str = "RESOLVED"  # RESOLVED, UNSUCCESSFUL, ESCALATED
    operator_notes: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    resolution_duration_hours: float = 24.0
    was_successful: bool = True

    def to_hindsight_content(self) -> str:
        """
        Serializes into a rich, structured natural language experience document
        optimized for Hindsight retain & TEMPR recall.
        """
        evidence_str = ", ".join(self.evidence_used) if self.evidence_used else "None"
        content = (
            f"Financial Discrepancy Case Experience:\n"
            f"- Case ID: {self.case_id}\n"
            f"- Order Reference: {self.order_id}\n"
            f"- Merchant: {self.merchant_name} (ID: {self.merchant_id})\n"
            f"- Payment Gateway: {self.gateway}\n"
            f"- Discrepancy Category: {self.discrepancy_type}\n"
            f"- Gross Transaction Amount: INR {self.gross_amount:,.2f}\n"
            f"- Financial Variance: INR {self.net_variance:,.2f}\n"
            f"- Deterministic Root Cause: {self.deterministic_cause}\n"
            f"- Remediation Strategy Attempted: {self.resolution_attempted}\n"
            f"- Supporting Evidence Submitted: {evidence_str}\n"
            f"- Resolution Outcome: {self.final_resolution} (Status: {self.outcome_status})\n"
            f"- Operator Notes: {self.operator_notes}\n"
            f"- Success Flag: {'YES' if self.was_successful else 'NO'}\n"
            f"- Resolution Turnaround Time: {self.resolution_duration_hours} hours\n"
        )
        return sanitize_sensitive_data(content)

    def to_tags(self) -> List[str]:
        return [
            f"discrepancy:{self.discrepancy_type.lower()}",
            f"gateway:{self.gateway.lower()}",
            f"merchant:{self.merchant_id.lower()}",
            f"status:{self.outcome_status.lower()}",
            "domain:reconciliation"
        ]

class MerchantMemory(BaseModel):
    """
    Durable knowledge regarding a specific merchant's contract and patterns.
    """
    merchant_id: str
    merchant_name: str
    contracted_fee_rate: float = 0.02
    contracted_gst_rate: float = 0.18
    known_quirks: List[str] = Field(default_factory=list)
    recurring_discrepancies: List[str] = Field(default_factory=list)
    preferred_dispute_evidence: List[str] = Field(default_factory=list)

    def to_hindsight_content(self) -> str:
        quirks_str = "; ".join(self.known_quirks) if self.known_quirks else "None recorded"
        evidence_str = ", ".join(self.preferred_dispute_evidence) if self.preferred_dispute_evidence else "Standard invoice"
        content = (
            f"Merchant Profile Knowledge:\n"
            f"- Merchant: {self.merchant_name} ({self.merchant_id})\n"
            f"- Contracted MDR: {self.contracted_fee_rate * 100:.1f}%\n"
            f"- Statutory GST: {self.contracted_gst_rate * 100:.0f}%\n"
            f"- Known Operational Quirks: {quirks_str}\n"
            f"- Recurring Exception Types: {', '.join(self.recurring_discrepancies)}\n"
            f"- Preferred Dispute Evidence: {evidence_str}\n"
        )
        return sanitize_sensitive_data(content)

class GatewayMemory(BaseModel):
    """
    Durable operational memory regarding payment gateway behaviors.
    """
    gateway_name: str
    known_pricing_anomalies: List[str] = Field(default_factory=list)
    settlement_sla_days: int = 2
    dispute_contact_channel: str = "merchant-support@gateway.com"
    required_dispute_fields: List[str] = Field(default_factory=list)

    def to_hindsight_content(self) -> str:
        anomalies_str = "; ".join(self.known_pricing_anomalies) if self.known_pricing_anomalies else "None"
        fields_str = ", ".join(self.required_dispute_fields) if self.required_dispute_fields else "Standard batch ID"
        content = (
            f"Payment Gateway Operational Profile:\n"
            f"- Gateway: {self.gateway_name}\n"
            f"- Settlement SLA: T+{self.settlement_sla_days} business days\n"
            f"- Known Recurring Anomalies: {anomalies_str}\n"
            f"- Required Dispute Fields: {fields_str}\n"
            f"- Escalation Channel: {self.dispute_contact_channel}\n"
        )
        return sanitize_sensitive_data(content)
