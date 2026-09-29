import time
import pandas as pd
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field

@dataclass
class PerformanceMetrics:
    total_records: int
    normalization_latency_ms: float
    reconciliation_latency_ms: float
    total_pipeline_latency_ms: float
    throughput_records_per_sec: float

@dataclass
class MatchStatistics:
    total_records: int
    reconciled_count: int
    discrepancy_count: int
    match_rate_pct: float
    total_gross_volume_inr: float
    total_reconciled_volume_inr: float
    total_discrepancy_volume_inr: float
    category_breakdown: Dict[str, int]

class ReconciliationDiagnostics:
    def __init__(self):
        pass

    def compute_metrics(
        self,
        reconciliation_df: pd.DataFrame,
        norm_latency_ms: float,
        rec_latency_ms: float
    ) -> Tuple[PerformanceMetrics, MatchStatistics, pd.DataFrame]:
        total_records = len(reconciliation_df)
        total_latency_ms = norm_latency_ms + rec_latency_ms
        throughput = (total_records / (total_latency_ms / 1000.0)) if total_latency_ms > 0 else 0.0

        perf = PerformanceMetrics(
            total_records=total_records,
            normalization_latency_ms=round(norm_latency_ms, 2),
            reconciliation_latency_ms=round(rec_latency_ms, 2),
            total_pipeline_latency_ms=round(total_latency_ms, 2),
            throughput_records_per_sec=round(throughput, 2)
        )

        reconciled_df = reconciliation_df[reconciliation_df["reconciliation_status"] == "RECONCILED"]
        discrepancy_df = reconciliation_df[reconciliation_df["reconciliation_status"] == "DISCREPANCY"]

        reconciled_count = len(reconciled_df)
        discrepancy_count = len(discrepancy_df)
        match_rate = round((reconciled_count / total_records * 100.0), 2) if total_records > 0 else 0.0

        gross_vol = float(reconciliation_df["gross_amount"].sum())
        reconciled_vol = float(reconciled_df["gross_amount"].sum())
        discrepancy_vol = float(discrepancy_df["gross_amount"].sum())

        cat_counts = discrepancy_df["discrepancy_category"].value_counts().to_dict()

        stats = MatchStatistics(
            total_records=total_records,
            reconciled_count=reconciled_count,
            discrepancy_count=discrepancy_count,
            match_rate_pct=match_rate,
            total_gross_volume_inr=round(gross_vol, 2),
            total_reconciled_volume_inr=round(reconciled_vol, 2),
            total_discrepancy_volume_inr=round(discrepancy_vol, 2),
            category_breakdown=cat_counts
        )

        return perf, stats, discrepancy_df
