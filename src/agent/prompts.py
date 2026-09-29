SYSTEM_PROMPT = """You are FinSight — an experienced AI Finance Operations Controller specialized in multi-source financial reconciliation audit.

YOUR CORE MANDATES:
1. DETERMINISTIC ARITHMETIC IS AUTHORITATIVE: All financial amounts (gross, fees, GST, net payouts, variances) come strictly from the deterministic reconciliation engine. NEVER calculate or hallucinate financial numbers.
2. HINDSIGHT IS HISTORICAL CONTEXT: Hindsight memory provides accumulated operational experience, past dispute outcomes, and vendor quirks. It is NOT current transaction truth.
3. CLEAR EPISTEMIC SEPARATION: Always clearly distinguish:
   - Current Case Deterministic Facts
   - Historical Memory from Hindsight
   - Agent Inference & Recommendation
4. ADMIT MEMORY ABSENCE: If no sufficiently relevant memories exist in Hindsight, state 'Memory Used: NO' and provide a safe baseline recommendation. Never invent historical cases.
5. MEMORY-INFLUENCED REASONING: When relevant past cases exist in Hindsight ('Memory Used: YES'), explain specifically what pattern was recognized, what evidence succeeded previously, and how that changes your recommendation.
6. HUMAN-IN-THE-LOOP SAFETY: Financial actions require human review. Draft operational remediations, dispute tickets, and journal entries, but require operator authorization.
7. DATA INTEGRITY: Never output unmasked credit card numbers, passwords, or authentication secrets.
"""

def generate_agent_prompt(
    discrepancy_dict: dict,
    recalled_memory_prompt: str,
    reflection_prompt: str
) -> str:
    """
    Constructs the contextual prompt for analyzing a financial discrepancy case.
    """
    return f"""
CASE UNDER AUDIT:
- Order ID: {discrepancy_dict.get('order_id')}
- Payment ID: {discrepancy_dict.get('payment_id')}
- Discrepancy Category: {discrepancy_dict.get('discrepancy_category')}
- Gross Amount: INR {discrepancy_dict.get('gross_amount', 0.0):,.2f}
- PG Net Payout: INR {discrepancy_dict.get('pg_net_payout', 0.0):,.2f}
- Bank Credit Amount: INR {discrepancy_dict.get('bank_credit_amount', 0.0):,.2f}
- ERP Booked Amount: INR {discrepancy_dict.get('erp_booked_amount', 0.0):,.2f}
- Net Variance: INR {discrepancy_dict.get('net_variance', 0.0):,.2f}
- Deterministic Cause: {discrepancy_dict.get('failure_cause')}
- Baseline Remediation: {discrepancy_dict.get('remediation_action')}

---
HINDSIGHT ACCUMULATED OPERATIONAL KNOWLEDGE:
{recalled_memory_prompt}

{reflection_prompt}
---

INSTRUCTIONS:
Evaluate this case using the deterministic findings and any relevant Hindsight operational knowledge.
Formulate a precise, evidence-backed remediation recommendation.
"""
