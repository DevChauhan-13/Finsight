from typing import Dict, Any, Optional

def build_recall_query_for_discrepancy(
    discrepancy_type: str,
    gateway: str = "Razorpay",
    merchant_name: str = "Apex Retail",
    failure_cause: str = "",
    net_variance: float = 0.0
) -> str:
    """
    Constructs a domain-specific, high-precision recall query for Hindsight
    to retrieve the most relevant past exception experiences.
    """
    cause_hint = f" Root cause: {failure_cause}." if failure_cause else ""
    variance_hint = f" Net financial variance: INR {net_variance:,.2f}." if abs(net_variance) > 0.01 else ""
    
    query = (
        f"Find historical resolutions for discrepancy '{discrepancy_type}' "
        f"on gateway '{gateway}' for merchant '{merchant_name}'.{cause_hint}{variance_hint} "
        f"What remediation actions, dispute evidence, or journal adjustments succeeded?"
    )
    return query

def build_reflection_query_for_discrepancy(
    discrepancy_type: str,
    gateway: str = "Razorpay",
    merchant_name: str = "Apex Retail"
) -> str:
    """
    Constructs a synthesis query for Hindsight reflect to aggregate recurring patterns,
    average turnaround times, and required dispute evidence across all historical cases.
    """
    query = (
        f"Synthesize the recurring operational patterns, gateway behavior, "
        f"and proven successful evidence for handling '{discrepancy_type}' "
        f"exceptions on gateway '{gateway}' for merchant '{merchant_name}'. "
        f"What is the recommended standard operating procedure?"
    )
    return query

def build_merchant_query(merchant_id: str) -> str:
    """Query to recall merchant contract rules, fee schedules, and prior exceptions."""
    return f"Merchant profile, contracted fee rate, and recurring exceptions for merchant ID '{merchant_id}'."

def build_gateway_query(gateway_name: str) -> str:
    """Query to recall gateway SLAs, dispute procedures, and known fee overcharges."""
    return f"Operational quirks, dispute evidence requirements, and fee bugs for gateway '{gateway_name}'."
