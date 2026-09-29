import sys
import os
from typing import Optional, List, Dict, Any
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.metrics.diagnostics import PerformanceMetrics, MatchStatistics
from src.agent.schemas import AgentCaseAnalysis

# Ensure UTF-8 output encoding for Windows legacy console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

console = Console()

def render_cli_report(
    perf: PerformanceMetrics,
    stats: MatchStatistics,
    discrepancy_df: pd.DataFrame,
    agent_analyses: Optional[List[AgentCaseAnalysis]] = None
):
    """
    Renders a visually striking Rich CLI report in terminal, incorporating
    authoritative deterministic reconciliation and FinSight AI memory insights.
    """
    title_panel = Panel(
        "[bold cyan]FinSight: Multi-Source Reconciliation Agent & AI Controller[/bold cyan]\n"
        "[bold white]Deterministic 3-Way Audit Engine + Hindsight Persistent Memory[/bold white]",
        box=box.DOUBLE,
        style="on blue",
        expand=False
    )
    console.print(title_panel)
    console.print()

    # Performance Metrics Table
    perf_table = Table(title="[PERFORMANCE] System Throughput & Latency Metrics", box=box.ROUNDED, header_style="bold magenta")
    perf_table.add_column("Metric Description", style="cyan")
    perf_table.add_column("Value", style="bold green", justify="right")

    perf_table.add_row("Total Financial Records Processed", f"{perf.total_records:,} records")
    perf_table.add_row("Schema Normalization Latency", f"{perf.normalization_latency_ms:.2f} ms")
    perf_table.add_row("Reconciliation Engine Latency", f"{perf.reconciliation_latency_ms:.2f} ms")
    perf_table.add_row("Total Pipeline Execution Time", f"{perf.total_pipeline_latency_ms:.2f} ms")
    perf_table.add_row("Processing Throughput", f"{perf.throughput_records_per_sec:,.2f} rec/sec")

    console.print(perf_table)
    console.print()

    # Financial Reconciliation Metrics Table
    rec_table = Table(title="[FINANCIAL RECONCILIATION] Multi-Source Audit Statistics", box=box.ROUNDED, header_style="bold yellow")
    rec_table.add_column("Financial Metric", style="cyan")
    rec_table.add_column("Count / Amount", style="bold white", justify="right")
    rec_table.add_column("Status / Share", style="bold green", justify="right")

    rec_table.add_row("Total Records Evaluated", f"{stats.total_records}", "100.0%")
    rec_table.add_row("Successfully Reconciled Records", f"{stats.reconciled_count}", f"{stats.match_rate_pct:.1f}% MATCH")
    rec_table.add_row("Un-reconciled Discrepancies", f"{stats.discrepancy_count}", f"{(100 - stats.match_rate_pct):.1f}% EXCEPTION")
    rec_table.add_row("Total Gross Transaction Volume", f"INR {stats.total_gross_volume_inr:,.2f}", "-")
    rec_table.add_row("Reconciled Net Volume", f"INR {stats.total_reconciled_volume_inr:,.2f}", f"{(stats.total_reconciled_volume_inr/stats.total_gross_volume_inr*100):.1f}%" if stats.total_gross_volume_inr > 0 else "0.0%")
    rec_table.add_row("Total Discrepancy Volume", f"INR {stats.total_discrepancy_volume_inr:,.2f}", f"{(stats.total_discrepancy_volume_inr/stats.total_gross_volume_inr*100):.1f}%" if stats.total_gross_volume_inr > 0 else "0.0%")

    console.print(rec_table)
    console.print()

    # AI CONTROLLER SECTION (if agent analyses are provided)
    if agent_analyses:
        ai_table = Table(title="[AI CONTROLLER] Hindsight Memory & Agent Operations", box=box.ROUNDED, header_style="bold cyan")
        ai_table.add_column("Agent Metric", style="cyan")
        ai_table.add_column("Value", style="bold green", justify="right")

        total_analyzed = len(agent_analyses)
        memory_matches = sum(1 for a in agent_analyses if a.memory_influenced)
        new_patterns = sum(1 for a in agent_analyses if a.historical_pattern is not None)
        recommendations = len(agent_analyses)

        ai_table.add_row("Cases Analyzed by FinSight Agent", f"{total_analyzed}")
        ai_table.add_row("Memory Matches (Hindsight Recall)", f"{memory_matches} / {total_analyzed} ({(memory_matches/total_analyzed*100):.1f}%)" if total_analyzed > 0 else "0")
        ai_table.add_row("Learned Operational Patterns", f"{new_patterns}")
        ai_table.add_row("Evidence-Backed Recommendations", f"{recommendations}")

        console.print(ai_table)
        console.print()

        # MEMORY INSIGHT HIGHLIGHTS TABLE
        insight_table = Table(
            title="[MEMORY INSIGHTS] Top Agent Remediation Strategies from Hindsight",
            box=box.ROUNDED,
            header_style="bold yellow"
        )
        insight_table.add_column("Case / Order", style="bold cyan")
        insight_table.add_column("Category", style="yellow")
        insight_table.add_column("Memory Used", style="bold green")
        insight_table.add_column("Learned Evidence & Strategy", style="white", width=45)
        insight_table.add_column("Contextual Next Step", style="italic green", width=30)

        for a in agent_analyses[:5]:  # Display top 5
            mem_status = f"[green]YES ({len(a.memory_matches)} cases)[/green]" if a.memory_influenced else "[red]NO (Cold start)[/red]"
            evidence_str = ", ".join(a.supporting_evidence[:2]) if a.supporting_evidence else "Standard docs"
            insight_table.add_row(
                a.order_id,
                a.discrepancy_type,
                mem_status,
                f"{a.recommended_action[:75]}...\n[italic]Evidence: {evidence_str}[/italic]",
                a.expected_next_step[:50]
            )

        console.print(insight_table)
        console.print()

    # Deterministic Exception Report Table
    if not discrepancy_df.empty:
        exc_table = Table(
            title=f"[EXCEPTION AUDIT] Detail of Flagged Discrepancies ({len(discrepancy_df)} Found)",
            box=box.HEAVY_HEAD,
            header_style="bold red"
        )
        exc_table.add_column("Order ID", style="bold cyan")
        exc_table.add_column("Category", style="bold yellow")
        exc_table.add_column("Gross (INR)", justify="right")
        exc_table.add_column("Exact Failure Cause", style="bold white", width=42)
        exc_table.add_column("Deterministic Baseline Action", style="italic green", width=32)

        for _, row in discrepancy_df.iterrows():
            exc_table.add_row(
                str(row["order_id"]),
                str(row["discrepancy_category"]),
                f"INR {float(row['gross_amount']):,.2f}",
                str(row["failure_cause"]),
                str(row["remediation_action"])
            )

        console.print(exc_table)
    else:
        console.print("[bold green]Perfect Batch Reconciliation! 0 Exceptions Detected.[/bold green]")

    console.print()
