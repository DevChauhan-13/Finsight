import argparse
import time
import json
import os
import sys
import pandas as pd

from src.generator.synthetic_engine import generate_synthetic_financial_datasets
from src.normalization.schema_normalizer import (
    normalize_pg_dataset,
    normalize_bank_dataset,
    normalize_erp_dataset
)
from src.reconciliation.engine import DeterministicReconciliationEngine
from src.metrics.diagnostics import ReconciliationDiagnostics
from src.dashboard.cli_view import render_cli_report
from src.memory.memory_service import FinSightMemoryService
from src.agent.reconciliation_agent import FinancialReconciliationAgent
from src.demo.memory_learning_demo import run_reproducible_memory_demo
from src.evaluation.evaluation_harness import FinSightEvaluationHarness

def main():
    parser = argparse.ArgumentParser(
        description="FinSight — Multi-Source Financial Reconciliation Agent Powered by Hindsight"
    )
    parser.add_argument("--generate", action="store_true", help="Generate synthetic PG, Bank, and ERP datasets")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory containing datasets")
    parser.add_argument("--use-llm", action="store_true", help="Use Gemini/LLM parsing for schema normalization")
    parser.add_argument("--launch-ui", action="store_true", help="Launch Streamlit Web Dashboard")
    parser.add_argument("--agent", action="store_true", help="Execute FinSight AI Agent with Hindsight memory on flagged exceptions")
    parser.add_argument("--demo-memory", action="store_true", help="Run reproducible 4-phase Hindsight before/after learning demonstration")
    parser.add_argument("--evaluate", action="store_true", help="Run empirical evaluation harness comparing baseline vs Hindsight memory")
    parser.add_argument("--clear-memory", action="store_true", help="Reset Hindsight memory bank")

    args = parser.parse_args()

    # Evaluation mode
    if args.evaluate:
        harness = FinSightEvaluationHarness()
        metrics = harness.run_benchmark()
        harness.render_report(metrics)
        sys.exit(0)

    # Demo memory mode
    if args.demo_memory:
        run_reproducible_memory_demo()
        sys.exit(0)

    # Clear memory mode
    if args.clear_memory:
        mem_service = FinSightMemoryService()
        mem_service.clear_all_memories()
        print("FinSight: Hindsight memory bank cleared successfully.")
        sys.exit(0)

    data_dir = args.data_dir
    pg_path = os.path.join(data_dir, "pg_transactions.csv")
    bank_path = os.path.join(data_dir, "bank_settlements.csv")
    erp_path = os.path.join(data_dir, "erp_ledger.json")

    # Generate synthetic datasets if requested or missing
    if args.generate or not (os.path.exists(pg_path) and os.path.exists(bank_path) and os.path.exists(erp_path)):
        print(f"Generating synthetic financial datasets in '{data_dir}'...")
        res = generate_synthetic_financial_datasets(output_dir=data_dir)
        print(f"Successfully generated {res['total_pg_records']} records with {res['seeded_error_count']} seeded error cases.")

    if args.launch_ui:
        print("Launching Interactive Streamlit Web Dashboard...")
        os.system("python -m streamlit run src/dashboard/web_app.py")
        sys.exit(0)

    # 1. Load raw datasets
    pg_df_raw = pd.read_csv(pg_path)
    bank_df_raw = pd.read_csv(bank_path)
    with open(erp_path, "r") as f:
        erp_json_raw = json.load(f)

    # 2. Layer 1: Schema Normalization & Parsing
    t0 = time.time()
    pg_norm = normalize_pg_dataset(pg_df_raw, use_llm=args.use_llm)
    bank_norm = normalize_bank_dataset(bank_df_raw, use_llm=args.use_llm)
    erp_norm = normalize_erp_dataset(erp_json_raw, use_llm=args.use_llm)
    t1 = time.time()
    norm_latency = (t1 - t0) * 1000.0

    # 3. Layer 2: Deterministic Reconciliation Engine
    engine = DeterministicReconciliationEngine()
    t2 = time.time()
    reconciled_df = engine.reconcile_batch(pg_norm, bank_norm, erp_norm)
    t3 = time.time()
    rec_latency = (t3 - t2) * 1000.0

    # 4. Metrics & Diagnostics Calculation
    diagnostics = ReconciliationDiagnostics()
    perf, stats, discrepancy_df = diagnostics.compute_metrics(reconciled_df, norm_latency, rec_latency)

    # 5. Layer 3: FinSight AI Agent with Hindsight Memory (if --agent is set or by default when exceptions occur)
    agent_analyses = []
    if args.agent or not discrepancy_df.empty:
        agent = FinancialReconciliationAgent()
        for _, row in discrepancy_df.iterrows():
            analysis = agent.analyze_discrepancy(row.to_dict())
            agent_analyses.append(analysis)

    # 6. Render Rich CLI Visual Report
    render_cli_report(perf, stats, discrepancy_df, agent_analyses=agent_analyses if agent_analyses else None)

if __name__ == "__main__":
    main()
