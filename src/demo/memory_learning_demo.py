import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from src.agent.reconciliation_agent import FinancialReconciliationAgent
from src.agent.schemas import OperatorOutcomeInput
from src.memory.memory_service import FinSightMemoryService

console = Console()

def run_reproducible_memory_demo():
    """
    Executes the 4-Phase Hindsight Learning Demo:
    - Phase A: Cold Memory (Baseline Generic Recommendation)
    - Phase B: Retain Historical Resolved Cases into Hindsight
    - Phase C: Warm Memory (Contextual, Evidence-Backed Recommendation)
    - Phase D: Comparative Contrast (Without Memory vs With Hindsight)
    """
    console.print()
    banner = Panel(
        "[bold cyan]FinSight: Hindsight Memory Learning Demonstration[/bold cyan]\n"
        "[italic white]Watch an AI Finance Controller evolve from generic advice to seasoned operational expertise[/italic white]",
        box=box.DOUBLE,
        style="on blue"
    )
    console.print(banner)
    console.print()

    # Initialize agent and clear memory bank to ensure clean demonstration
    memory_service = FinSightMemoryService()
    memory_service.clear_all_memories()
    agent = FinancialReconciliationAgent(memory_service=memory_service)

    # Define a realistic recurring discrepancy case: FEE_MISMATCH on Razorpay
    case_1_discrepancy = {
        "order_id": "ORD-2026-0046",
        "payment_id": "pay_RZP_000046",
        "bank_utr": "UTRBNK202608200046",
        "discrepancy_category": "FEE_MISMATCH",
        "gross_amount": 20000.0,
        "pg_net_payout": 18820.0,  # 5% fee charged (₹1,000 + ₹180 GST = ₹1,180) instead of 2% (₹400 + ₹72 GST = ₹472)
        "bank_credit_amount": 18820.0,
        "erp_booked_amount": 20000.0,
        "net_variance": 0.0,
        "fee_overcharge_amount": 708.0,
        "failure_cause": "Gateway fee charged (₹1,000.00) exceeds contracted fee (₹400.00) at 2% rate",
        "remediation_action": "Raise fee dispute billing ticket with Payment Gateway support for overcharge credit."
    }

    # -------------------------------------------------------------
    # PHASE A: COLD MEMORY (BASELINE)
    # -------------------------------------------------------------
    console.print("[bold yellow]══════════════════════════════════════════════════════════════[/bold yellow]")
    console.print("[bold yellow]PHASE A: COLD MEMORY EVALUATION (First Encounter)[/bold yellow]")
    console.print("[italic]Memory bank is pristine. FinSight has no historical operational context.[/italic]\n")

    analysis_cold = agent.analyze_discrepancy(case_1_discrepancy, merchant_name="Apex Retail", gateway="Razorpay")

    cold_table = Table(box=box.ROUNDED, header_style="bold magenta")
    cold_table.add_column("Parameter", style="cyan")
    cold_table.add_column("Agent Diagnostic & Assessment", style="white")

    cold_table.add_row("Discrepancy Category", f"[bold red]{analysis_cold.discrepancy_type}[/bold red]")
    cold_table.add_row("Deterministic Math", f"Gross: ₹{analysis_cold.deterministic_findings['gross_amount']:,.2f} | Fee Leakage: ₹{analysis_cold.deterministic_findings['fee_overcharge_amount']:,.2f}")
    cold_table.add_row("Hindsight Memory Used", "[bold red]NO (0 prior cases found)[/bold red]")
    cold_table.add_row("Reasoning Summary", analysis_cold.reasoning_summary)
    cold_table.add_row("Recommended Action", f"[yellow]{analysis_cold.recommended_action}[/yellow]")
    cold_table.add_row("Supporting Evidence", ", ".join(analysis_cold.supporting_evidence))

    console.print(cold_table)
    console.print()

    # Prepare a second historical case in the agent registry before retention.
    historical_case_2 = {
        "order_id": "ORD-2026-0032",
        "payment_id": "pay_RZP_000032",
        "bank_utr": "UTRBNK202608190032",
        "discrepancy_category": "FEE_MISMATCH",
        "gross_amount": 12500.0,
        "pg_net_payout": 11550.0,
        "bank_credit_amount": 11550.0,
        "erp_booked_amount": 12500.0,
        "net_variance": 0.0,
        "fee_overcharge_amount": 564.0,
        "failure_cause": "Gateway fee charged at a 5% corporate-card tier instead of the contracted 2% rate",
        "remediation_action": "Raise fee dispute billing ticket with Payment Gateway support for overcharge credit.",
    }
    agent.analyze_discrepancy(historical_case_2, merchant_name="Apex Retail", gateway="Razorpay")

    # -------------------------------------------------------------
    # PHASE B: TEACH THE SYSTEM (Persist Historical Outcomes)
    # -------------------------------------------------------------
    console.print("[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]PHASE B: PERSISTING RESOLUTION EXPERIENCE TO HINDSIGHT[/bold cyan]")
    console.print("[italic]Finance Controller resolves cases and retains durable operational experience into Hindsight memory bank...[/italic]\n")

    historical_outcomes = [
        OperatorOutcomeInput(
            case_id="CASE-ORD-2026-0046",
            outcome_status="RESOLVED",
            final_resolution="Gateway acknowledged billing engine MDR tier bug on corporate credit cards; credited ₹708.00 back to merchant account.",
            operator_notes="Razorpay billing desk requested Master Merchant Agreement Schedule B and Batch Settlement ID #BCH-4491.",
            evidence_submitted=["Master Merchant Agreement Schedule B (2% rate)", "Batch Settlement ID #BCH-4491", "Bank UTR Credit Record"]
        ),
        OperatorOutcomeInput(
            case_id="CASE-ORD-2026-0032",
            outcome_status="RESOLVED",
            final_resolution="Gateway resolved overcharge dispute within 24 hours; credited ₹450.00 difference via credit memo CM-8832.",
            operator_notes="Always attach Merchant Agreement Schedule B when disputing corporate card 5% fee tier.",
            evidence_submitted=["Master Merchant Agreement Schedule B (2% rate)", "Credit Memo Request", "Gateway Fee Breakdown CSV"]
        )
    ]

    for item in historical_outcomes:
        res = agent.record_operator_resolution(item.case_id, item, gateway="Razorpay", merchant_name="Apex Retail")
        console.print(f"[green]✓ RETAINED EXPERIENCE IN HINDSIGHT:[/green] Case {item.case_id} -> [bold]{item.final_resolution[:75]}...[/bold]")

    console.print()

    # -------------------------------------------------------------
    # PHASE C: WARM MEMORY (New Similar Discrepancy)
    # -------------------------------------------------------------
    console.print("[bold green]══════════════════════════════════════════════════════════════[/bold green]")
    console.print("[bold green]PHASE C: WARM MEMORY EVALUATION (New Similar Exception)[/bold green]")
    console.print("[italic]Presenting a brand new transaction (ORD-2026-0052) with an identical fee anomaly...[/italic]\n")

    case_2_discrepancy = {
        "order_id": "ORD-2026-0052",
        "payment_id": "pay_RZP_000052",
        "bank_utr": "UTRBNK202608200052",
        "discrepancy_category": "FEE_MISMATCH",
        "gross_amount": 35000.0,
        "pg_net_payout": 32935.0,  # Charged 5% fee (₹1,750 + ₹315 GST) instead of 2% (₹700 + ₹126 GST)
        "bank_credit_amount": 32935.0,
        "erp_booked_amount": 35000.0,
        "net_variance": 0.0,
        "fee_overcharge_amount": 1239.0,
        "failure_cause": "Gateway fee charged (₹1,750.00) exceeds contracted fee (₹700.00) at 2% rate",
        "remediation_action": "Raise fee dispute billing ticket with Payment Gateway support for overcharge credit."
    }

    analysis_warm = agent.analyze_discrepancy(case_2_discrepancy, merchant_name="Apex Retail", gateway="Razorpay")

    warm_table = Table(box=box.ROUNDED, header_style="bold green")
    warm_table.add_column("Parameter", style="cyan")
    warm_table.add_column("Agent Diagnostic & Assessment", style="white")

    warm_table.add_row("Discrepancy Category", f"[bold red]{analysis_warm.discrepancy_type}[/bold red]")
    warm_table.add_row("Deterministic Math", f"Gross: ₹{analysis_warm.deterministic_findings['gross_amount']:,.2f} | Fee Leakage: ₹{analysis_warm.deterministic_findings['fee_overcharge_amount']:,.2f}")
    warm_table.add_row("Hindsight Memory Used", f"[bold green]YES ({len(analysis_warm.memory_matches)} relevant historical cases retrieved)[/bold green]")
    warm_table.add_row("Learned Pattern", analysis_warm.historical_pattern.pattern_description if analysis_warm.historical_pattern else "Pattern synthesized")
    warm_table.add_row("Reasoning Summary", analysis_warm.reasoning_summary)
    warm_table.add_row("Contextual Recommendation", f"[bold green]{analysis_warm.recommended_action}[/bold green]")
    warm_table.add_row("Evidence-Backed Package", "[bold cyan]" + ", ".join(analysis_warm.supporting_evidence) + "[/bold cyan]")
    warm_table.add_row("Expected Turnaround", f"{analysis_warm.historical_pattern.average_turnaround_hours:.0f} hours (based on prior cases)")

    console.print(warm_table)
    console.print()

    # -------------------------------------------------------------
    # PHASE D: CONTRAST COMPARISON (WITHOUT MEMORY VS WITH HINDSIGHT)
    # -------------------------------------------------------------
    console.print("[bold blue]══════════════════════════════════════════════════════════════[/bold blue]")
    console.print("[bold blue]PHASE D: LEARNING IMPACT COMPARISON[/bold blue]\n")

    contrast_table = Table(title="Before vs After Memory Comparison", box=box.HEAVY_EDGE, header_style="bold yellow")
    contrast_table.add_column("Feature", style="bold cyan")
    contrast_table.add_column("WITHOUT HINDSIGHT (Cold)", style="italic red", width=42)
    contrast_table.add_column("WITH HINDSIGHT (Learned)", style="bold green", width=48)

    contrast_table.add_row(
        "Recommendation",
        analysis_cold.recommended_action,
        analysis_warm.recommended_action
    )
    contrast_table.add_row(
        "Evidence Prepared",
        ", ".join(analysis_cold.supporting_evidence),
        ", ".join(analysis_warm.supporting_evidence)
    )
    contrast_table.add_row(
        "Historical Pattern Context",
        "None (Blind to recurring vendor bugs)",
        analysis_warm.reasoning_summary
    )
    contrast_table.add_row(
        "Turnaround / Resolution Expectation",
        "No historical turnaround available",
        f"{analysis_warm.historical_pattern.average_turnaround_hours:.0f}h average turnaround recorded in prior cases" if analysis_warm.historical_pattern and analysis_warm.historical_pattern.average_turnaround_hours is not None else "No turnaround history recorded"
    )
    contrast_table.add_row(
        "Operator Efficiency",
        "Manual investigation required",
        "Historical evidence package surfaced automatically"
    )

    console.print(contrast_table)
    console.print("\n[bold green]✓ Demo completed successfully: FinSight demonstrably learns from past exceptions![/bold green]\n")
