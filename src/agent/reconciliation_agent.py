import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.memory.memory_service import FinSightMemoryService
from src.memory.memory_models import CaseMemory
from src.memory.memory_formatter import MemoryFormatter
from src.agent.schemas import (
    AgentCaseAnalysis,
    CaseLifecycleState,
    MemoryMatchItem,
    HistoricalPattern,
    OperatorOutcomeInput
)
from src.agent.tools import ReconciliationAgentTools
from src.agent.prompts import SYSTEM_PROMPT, generate_agent_prompt

logger = logging.getLogger(__name__)

class FinancialReconciliationAgent:
    """
    FinSight AI Finance Controller: An autonomous reconciliation exception agent
    that learns from every resolved case using Hindsight persistent memory.
    """
    def __init__(
        self,
        memory_service: Optional[FinSightMemoryService] = None,
        use_gemini_if_available: bool = True
    ):
        self.memory_service = memory_service or FinSightMemoryService()
        self.tools = ReconciliationAgentTools(self.memory_service)
        self.formatter = MemoryFormatter()
        self.use_gemini = use_gemini_if_available
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")

        # Cache of active cases and their lifecycle states
        self.active_cases: Dict[str, AgentCaseAnalysis] = {}

    def analyze_discrepancy(
        self,
        discrepancy_dict: Dict[str, Any],
        merchant_name: str = "Apex Retail",
        gateway: str = "Razorpay"
    ) -> AgentCaseAnalysis:
        """
        Main reasoning pipeline:
        Deterministic Exception -> Hindsight Recall -> Historical Pattern Analysis
        -> Memory-Influenced Recommendation.
        """
        order_id = str(discrepancy_dict.get("order_id", ""))
        pay_id = str(discrepancy_dict.get("payment_id", ""))
        case_id = f"CASE-{order_id}"
        category = str(discrepancy_dict.get("discrepancy_category", "UNKNOWN"))
        gross = float(discrepancy_dict.get("gross_amount", 0.0))
        variance = float(discrepancy_dict.get("net_variance", 0.0))
        cause = str(discrepancy_dict.get("failure_cause", ""))
        baseline_action = str(discrepancy_dict.get("remediation_action", ""))

        # 1. Deterministic mathematical findings (authoritative truth)
        det_findings = {
            "order_id": order_id,
            "payment_id": pay_id,
            "bank_utr": discrepancy_dict.get("bank_utr", ""),
            "gross_amount": gross,
            "pg_net_payout": float(discrepancy_dict.get("pg_net_payout", 0.0)),
            "bank_credit_amount": float(discrepancy_dict.get("bank_credit_amount", 0.0)),
            "erp_booked_amount": float(discrepancy_dict.get("erp_booked_amount", 0.0)),
            "net_variance": variance,
            "fee_overcharge_amount": float(discrepancy_dict.get("fee_overcharge_amount", 0.0)),
            "deterministic_cause": cause,
            "baseline_action": baseline_action
        }

        # 2. Hindsight Memory Recall
        memories = self.tools.recall_similar_cases(
            discrepancy_type=category,
            gateway=gateway,
            merchant_name=merchant_name,
            failure_cause=cause,
            net_variance=variance
        )

        memory_items: List[MemoryMatchItem] = []
        pattern: Optional[HistoricalPattern] = None
        memory_influenced = False

        if memories:
            memory_influenced = True
            parsed_memories = self.formatter.parse_recalled_items(memories)
            for p in parsed_memories:
                memory_items.append(MemoryMatchItem(
                    id=p["id"],
                    summary=p["summary"],
                    outcome=p["outcome"],
                    evidence_used=p["evidence"],
                    relevance_score=0.95,
                    full_text=p["full_text"]
                ))

            # Synthesize reflection pattern
            reflection = self.tools.reflect_on_historical_resolutions(
                discrepancy_type=category,
                gateway=gateway,
                merchant_name=merchant_name
            )

            # Extract proven evidence from memory
            proven_evidence = []
            for item in memory_items:
                if item.evidence_used and item.evidence_used != "Standard":
                    for ev in item.evidence_used.split(","):
                        ev_clean = ev.strip()
                        if ev_clean and ev_clean not in proven_evidence:
                            proven_evidence.append(ev_clean)
            
            if not proven_evidence:
                proven_evidence = ["Merchant Contract Agreement", "Settlement Batch ID", "Bank Statement Narration"]

            # Only claim outcomes that can be supported by the recalled records.
            successful_count = 0
            turnaround_hours = []
            for mem in memories:
                text = str(mem.get("text", ""))
                if "Success Flag: YES" in text or "Status: RESOLVED" in text:
                    successful_count += 1
                marker = "Resolution Turnaround Time:"
                if marker in text:
                    try:
                        raw = text.split(marker, 1)[1].split("hours", 1)[0].strip()
                        turnaround_hours.append(float(raw))
                    except (ValueError, IndexError):
                        pass

            sample_count = len(memory_items)
            success_rate = round((successful_count / sample_count) * 100.0, 1) if sample_count else 0.0
            average_turnaround = (sum(turnaround_hours) / len(turnaround_hours)) if turnaround_hours else None

            pattern = HistoricalPattern(
                pattern_description=f"Observed {sample_count} prior '{category}' resolution(s) on {gateway}.",
                sample_count=sample_count,
                success_rate_pct=success_rate,
                recommended_evidence=proven_evidence,
                average_turnaround_hours=average_turnaround
            )

        # 3. Formulate Recommendation based on presence vs absence of Hindsight Memory
        if memory_influenced and pattern:
            # MEMORY INFLUENCED RECOMMENDATION:
            # Leverages proven historical evidence and vendor-specific resolutions
            evidence_text = ", ".join(pattern.recommended_evidence[:2])
            recommended_action = baseline_action or (
                f"Investigate {category} using the historical evidence package: {evidence_text}."
            )
            if category == "FEE_MISMATCH":
                recommended_action = (
                    f"Prepare a high-priority dispute to {gateway} operations referencing {evidence_text}."
                )
            elif category == "SETTLEMENT_DELAY":
                recommended_action = (
                    f"Track the {gateway} settlement batch using {evidence_text} and verify the bank credit before escalation."
                )

            turnaround_text = (
                f" Recorded cases show an average turnaround of {pattern.average_turnaround_hours:.1f}h."
                if pattern.average_turnaround_hours is not None else " No reliable turnaround time was recorded."
            )
            reasoning_summary = (
                f"Hindsight retrieved {len(memory_items)} relevant past case(s). "
                f"Historical evidence includes {evidence_text}.{turnaround_text}"
            )
            supporting_evidence = pattern.recommended_evidence
            if category == "FEE_MISMATCH":
                expected_next_step = "Await gateway dispute confirmation and verify any approved credit against the settlement ledger."
            elif category == "SETTLEMENT_DELAY":
                expected_next_step = "Verify the missing settlement appears in the next bank statement or payout batch."
            elif category == "REFUND_UNACCOUNTED":
                expected_next_step = "Verify the ERP credit memo/reversal posts and ties back to the refund transaction."
            else:
                expected_next_step = "Human operator to verify the recommended operational action against source records."
            confidence = 0.96
        else:
            # COLD MEMORY / BASELINE RECOMMENDATION:
            # No historical experience exists in Hindsight; give standard protocol
            recommended_action = baseline_action or f"Investigate discrepancy '{category}' via standard manual operations protocol."
            reasoning_summary = (
                "No prior historical cases found in Hindsight memory for this exception type. "
                "Defaulting to baseline deterministic financial protocol."
            )
            supporting_evidence = ["Standard Payment ID", "Transaction Timestamp"]
            expected_next_step = "Human operator manual audit required."
            confidence = 0.80

        # Construct AgentCaseAnalysis
        analysis = AgentCaseAnalysis(
            case_id=case_id,
            order_id=order_id,
            payment_id=pay_id,
            discrepancy_type=category,
            lifecycle_state=CaseLifecycleState.RECOMMENDATION_READY,
            current_case_summary=(
                f"Deterministic audit identified '{category}' for Order {order_id}. "
                f"Gross: INR {gross:,.2f} | Variance: INR {variance:,.2f}."
            ),
            deterministic_findings=det_findings,
            memory_matches=memory_items,
            historical_pattern=pattern,
            memory_influenced=memory_influenced,
            recommended_action=recommended_action,
            reasoning_summary=reasoning_summary,
            supporting_evidence=supporting_evidence,
            expected_next_step=expected_next_step,
            confidence=confidence,
            requires_human_review=True
        )

        self.active_cases[case_id] = analysis
        return analysis

    def record_operator_resolution(
        self,
        case_id: str,
        outcome_input: OperatorOutcomeInput,
        gateway: str = "Razorpay",
        merchant_name: str = "Apex Retail"
    ) -> Dict[str, Any]:
        """
        CRITICAL LEARNING LOOP:
        Captures human operator's final resolution, updates case state to RESOLVED,
        and retains the durable experience in Hindsight so future exceptions learn!
        """
        analysis = self.active_cases.get(case_id)
        if not analysis:
            logger.warning(f"Case {case_id} not found in active cases registry; refusing to invent financial facts.")
            return {
                "status": "error",
                "case_id": case_id,
                "retained_in_hindsight": False,
                "error": "Active case not found; analyze the discrepancy before recording an operator resolution."
            }
        else:
            order_id = analysis.order_id
            discrepancy_type = analysis.discrepancy_type
            gross_amount = analysis.deterministic_findings.get("gross_amount", 0.0)
            variance = analysis.deterministic_findings.get("net_variance", 0.0)
            cause = analysis.deterministic_findings.get("deterministic_cause", "")
            analysis.lifecycle_state = CaseLifecycleState.RESOLVED

        # Construct CaseMemory for Hindsight retention
        case_memory = CaseMemory(
            case_id=case_id,
            order_id=order_id,
            payment_id=analysis.payment_id,
            merchant_id="MERCHANT_001",
            merchant_name=merchant_name,
            gateway=gateway,
            discrepancy_type=discrepancy_type,
            gross_amount=gross_amount,
            net_variance=variance,
            deterministic_cause=cause,
            resolution_attempted=analysis.recommended_action,
            evidence_used=outcome_input.evidence_submitted or analysis.supporting_evidence,
            final_resolution=outcome_input.final_resolution,
            outcome_status=outcome_input.outcome_status,
            operator_notes=outcome_input.operator_notes,
            timestamp=datetime.now().isoformat(),
            resolution_duration_hours=24.0,
            was_successful=(outcome_input.outcome_status.upper() == "RESOLVED")
        )

        # Retain into Hindsight persistent memory!
        retain_res = self.tools.retain_resolution_experience(case_memory)
        return {
            "status": "success",
            "case_id": case_id,
            "retained_in_hindsight": True,
            "hindsight_result": retain_res,
            "memory_content": case_memory.to_hindsight_content()
        }
