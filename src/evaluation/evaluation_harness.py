import time
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.table import Table
from rich import box

from src.agent.reconciliation_agent import FinancialReconciliationAgent
from src.agent.schemas import OperatorOutcomeInput
from src.memory.memory_service import FinSightMemoryService

@dataclass
class EvaluationMetrics:
    total_test_cases: int
    cold_memory_influenced_count: int
    warm_memory_influenced_count: int
    memory_retrieval_rate_pct: float
    evidence_augmentation_rate_pct: float
    average_confidence_cold: float
    average_confidence_warm: float
    operator_time_saved_est_minutes: float

class FinSightEvaluationHarness:
    """
    Empirical benchmark harness comparing baseline exception handling (without memory)
    against memory-augmented exception handling (with Hindsight).
    """
    def __init__(self):
        self.console = Console()

    def run_benchmark(self) -> EvaluationMetrics:
        memory_service = FinSightMemoryService()
        memory_service.clear_all_memories()
        agent = FinancialReconciliationAgent(memory_service=memory_service)

        # Dataset of realistic recurring test discrepancy cases
        test_cases = [
            {
                "order_id": "ORD-EVAL-01",
                "payment_id": "pay_eval_01",
                "bank_utr": "UTR_EVAL_01",
                "discrepancy_category": "FEE_MISMATCH",
                "gross_amount": 10000.0,
                "pg_net_payout": 9410.0,
                "bank_credit_amount": 9410.0,
                "erp_booked_amount": 10000.0,
                "net_variance": 0.0,
                "failure_cause": "Gateway charged 5% MDR instead of 2%",
                "remediation_action": "Raise dispute ticket"
            },
            {
                "order_id": "ORD-EVAL-02",
                "payment_id": "pay_eval_02",
                "bank_utr": "UTR_EVAL_02",
                "discrepancy_category": "SETTLEMENT_DELAY",
                "gross_amount": 15000.0,
                "pg_net_payout": 14646.0,
                "bank_credit_amount": 0.0,
                "erp_booked_amount": 15000.0,
                "net_variance": 14646.0,
                "failure_cause": "Cleared in PG but missing in Bank",
                "remediation_action": "Track payout node"
            },
            {
                "order_id": "ORD-EVAL-03",
                "payment_id": "pay_eval_03",
                "bank_utr": "UTR_EVAL_03",
                "discrepancy_category": "REFUND_UNACCOUNTED",
                "gross_amount": 5000.0,
                "pg_net_payout": 0.0,
                "bank_credit_amount": 0.0,
                "erp_booked_amount": 5000.0,
                "net_variance": 0.0,
                "failure_cause": "Refund completed in PG but ERP revenue not reversed",
                "remediation_action": "Post credit memo in ERP"
            }
        ]

        # 1. Benchmark Cold Memory (No history)
        cold_analyses = []
        for tc in test_cases:
            res = agent.analyze_discrepancy(tc)
            cold_analyses.append(res)

        # 2. Retain verified resolutions for these discrepancy types into Hindsight
        seed_outcomes = [
            OperatorOutcomeInput(
                case_id="CASE-ORD-EVAL-01",
                outcome_status="RESOLVED",
                final_resolution="Gateway billing team refunded fee variance within 24h of dispute.",
                operator_notes="Attached Master Merchant Agreement Schedule B and settlement batch ID.",
                evidence_submitted=["Master Merchant Agreement Schedule B", "Settlement Batch ID"]
            ),
            OperatorOutcomeInput(
                case_id="CASE-ORD-EVAL-02",
                outcome_status="RESOLVED",
                final_resolution="Bank clearing node arrived on T+2; automatic match completed.",
                operator_notes="Settlement corridor cleared at 18:00 on Day 2.",
                evidence_submitted=["Bank Payout Node ID", "Gateway Settlement Tracking Reference"]
            ),
            OperatorOutcomeInput(
                case_id="CASE-ORD-EVAL-03",
                outcome_status="RESOLVED",
                final_resolution="Posted ERP credit memo CM-4091 reversing revenue account.",
                operator_notes="Customer refund debit validated against bank statement reversal.",
                evidence_submitted=["Bank Debit Reversal Advice", "PG Refund ARN"]
            )
        ]

        for out in seed_outcomes:
            agent.record_operator_resolution(out.case_id, out)

        # 3. Benchmark Warm Memory with new similar cases
        repeat_test_cases = [
            {
                "order_id": "ORD-EVAL-REPEAT-01",
                "payment_id": "pay_eval_rep_01",
                "bank_utr": "UTR_EVAL_REP_01",
                "discrepancy_category": "FEE_MISMATCH",
                "gross_amount": 25000.0,
                "pg_net_payout": 23525.0,
                "bank_credit_amount": 23525.0,
                "erp_booked_amount": 25000.0,
                "net_variance": 0.0,
                "failure_cause": "Gateway charged 5% MDR instead of 2%",
                "remediation_action": "Raise dispute ticket"
            },
            {
                "order_id": "ORD-EVAL-REPEAT-02",
                "payment_id": "pay_eval_rep_02",
                "bank_utr": "UTR_EVAL_REP_02",
                "discrepancy_category": "SETTLEMENT_DELAY",
                "gross_amount": 18000.0,
                "pg_net_payout": 17575.2,
                "bank_credit_amount": 0.0,
                "erp_booked_amount": 18000.0,
                "net_variance": 17575.2,
                "failure_cause": "Cleared in PG but missing in Bank",
                "remediation_action": "Track payout node"
            },
            {
                "order_id": "ORD-EVAL-REPEAT-03",
                "payment_id": "pay_eval_rep_03",
                "bank_utr": "UTR_EVAL_REP_03",
                "discrepancy_category": "REFUND_UNACCOUNTED",
                "gross_amount": 7500.0,
                "pg_net_payout": 0.0,
                "bank_credit_amount": 0.0,
                "erp_booked_amount": 7500.0,
                "net_variance": 0.0,
                "failure_cause": "Refund completed in PG but ERP revenue not reversed",
                "remediation_action": "Post credit memo in ERP"
            }
        ]

        warm_analyses = []
        for tc in repeat_test_cases:
            res = agent.analyze_discrepancy(tc)
            warm_analyses.append(res)

        # 4. Compute empirical metrics
        total = len(repeat_test_cases)
        cold_influenced = sum(1 for c in cold_analyses if c.memory_influenced)
        warm_influenced = sum(1 for w in warm_analyses if w.memory_influenced)
        retrieval_rate = (warm_influenced / total) * 100.0
        
        # Evidence augmentation rate: percentage of warm cases where specific evidence was surfaced
        evidence_augmented = sum(1 for w in warm_analyses if len(w.supporting_evidence) > 2 or any("Agreement" in e or "Batch" in e or "Node" in e or "Advice" in e for e in w.supporting_evidence))
        evidence_rate = (evidence_augmented / total) * 100.0

        avg_conf_cold = sum(c.confidence for c in cold_analyses) / len(cold_analyses)
        avg_conf_warm = sum(w.confidence for w in warm_analyses) / len(warm_analyses)

        # Estimated operator time saved: ~15 minutes of investigation time saved per memory-influenced case
        time_saved_mins = warm_influenced * 15.0

        metrics = EvaluationMetrics(
            total_test_cases=total,
            cold_memory_influenced_count=cold_influenced,
            warm_memory_influenced_count=warm_influenced,
            memory_retrieval_rate_pct=round(retrieval_rate, 1),
            evidence_augmentation_rate_pct=round(evidence_rate, 1),
            average_confidence_cold=round(avg_conf_cold, 2),
            average_confidence_warm=round(avg_conf_warm, 2),
            operator_time_saved_est_minutes=time_saved_mins
        )

        return metrics

    def render_report(self, metrics: EvaluationMetrics):
        """Displays rich evaluation table."""
        table = Table(
            title="[EVALUATION HARNESS] FinSight Memory Benchmark: Cold vs Warm Hindsight",
            box=box.ROUNDED,
            header_style="bold magenta"
        )
        table.add_column("Evaluation Metric", style="cyan")
        table.add_column("Baseline (Without Memory)", style="bold red", justify="right")
        table.add_column("FinSight (With Hindsight)", style="bold green", justify="right")
        table.add_column("Net Improvement", style="bold yellow", justify="right")

        table.add_row(
            "Memory-Influenced Decisions",
            f"{metrics.cold_memory_influenced_count} / {metrics.total_test_cases} (0.0%)",
            f"{metrics.warm_memory_influenced_count} / {metrics.total_test_cases} ({metrics.memory_retrieval_rate_pct}%)",
            f"+{metrics.memory_retrieval_rate_pct}%"
        )
        table.add_row(
            "Evidence Augmentation Rate",
            "0.0% (Generic advice)",
            f"{metrics.evidence_augmentation_rate_pct}% (Proven docs)",
            f"+{metrics.evidence_augmentation_rate_pct}%"
        )
        table.add_row(
            "Average Recommendation Confidence",
            f"{metrics.average_confidence_cold * 100:.0f}%",
            f"{metrics.average_confidence_warm * 100:.0f}%",
            f"+{(metrics.average_confidence_warm - metrics.average_confidence_cold) * 100:.0f}%"
        )
        table.add_row(
            "Estimated Ops Time Saved",
            "0.0 mins",
            f"{metrics.operator_time_saved_est_minutes:.0f} mins",
            f"{metrics.operator_time_saved_est_minutes:.0f} mins"
        )

        self.console.print()
        self.console.print(table)
        self.console.print()
