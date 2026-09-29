import pandas as pd
from typing import List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ReconciliationResultRow:
    order_id: str
    payment_id: str
    bank_utr: str
    transaction_date: str
    reconciliation_status: str  # RECONCILED / DISCREPANCY
    discrepancy_category: str   # NONE, FEE_MISMATCH, SETTLEMENT_DELAY, etc.
    gross_amount: float
    pg_net_payout: float
    bank_credit_amount: float
    erp_booked_amount: float
    net_variance: float         # PG net payout minus bank credit
    fee_overcharge_amount: float
    failure_cause: str
    remediation_action: str


class DeterministicReconciliationEngine:
    """Deterministic 3-way reconciliation for Payment Gateway, Bank and ERP data."""

    def __init__(
        self,
        fee_tolerance: float = 0.50,
        amount_tolerance: float = 0.01,
        partial_hold_threshold: float = 100.0,
        current_period_year: Optional[int] = None,
    ):
        self.fee_tolerance = fee_tolerance
        self.amount_tolerance = amount_tolerance
        self.partial_hold_threshold = partial_hold_threshold
        self.current_period_year = current_period_year
        self.contracted_fee_rate = 0.02
        self.contracted_gst_rate = 0.18

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            if pd.isna(value):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _is_missing_utr(utr: str) -> bool:
        normalized = str(utr or "").strip().upper()
        return normalized in {"", "MISSING_N/A", "N/A", "NA", "UNKNOWN", "NONE", "NULL"}

    def _infer_period_year(self, pg_df: pd.DataFrame) -> Optional[int]:
        if self.current_period_year is not None:
            return self.current_period_year
        if "created_at" not in pg_df.columns:
            return None
        years = pd.to_datetime(pg_df["created_at"], errors="coerce").dt.year.dropna()
        if years.empty:
            return None
        return int(years.mode().iloc[0])

    def reconcile_batch(
        self,
        pg_df: pd.DataFrame,
        bank_df: pd.DataFrame,
        erp_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Perform deterministic multi-source reconciliation without LLM involvement."""
        results: List[ReconciliationResultRow] = []

        bank_rows = [row.to_dict() for _, row in bank_df.iterrows()]
        bank_utr_map = {}
        missing_ref_rows = []
        for row in bank_rows:
            utr = str(row.get("bank_ref_utr", "")).strip()
            if self._is_missing_utr(utr):
                missing_ref_rows.append(row)
            else:
                bank_utr_map.setdefault(utr, row)

        erp_order_map = {}
        for _, e_row in erp_df.iterrows():
            order_id = str(e_row.get("order_id", "")).strip()
            if order_id:
                erp_order_map.setdefault(order_id, e_row.to_dict())

        seen_order_ids = set()
        period_year = self._infer_period_year(pg_df)

        for _, pg_row in pg_df.iterrows():
            order_id = str(pg_row.get("order_id", "")).strip()
            pay_id = str(pg_row.get("payment_id", "")).strip()
            utr = str(pg_row.get("bank_utr", "")).strip()
            transaction_date = str(pg_row.get("created_at", "")).strip()

            gross = self._safe_float(pg_row.get("gross_amount"))
            pg_fee = self._safe_float(pg_row.get("gateway_fee"))
            pg_gst = self._safe_float(pg_row.get("gst_tax"))
            pg_net = self._safe_float(pg_row.get("net_payout"))
            pg_status = str(pg_row.get("status", "SUCCESS")).upper()

            bank_record = bank_utr_map.get(utr) if not self._is_missing_utr(utr) else None
            erp_record = erp_order_map.get(order_id)

            # If the PG UTR has no direct bank match, a uniquely matching bank
            # credit with an invalid UTR is evidence of a corrupted bank reference,
            # not a settlement delay.
            if bank_record is None and pg_status == "SUCCESS":
                candidates = [
                    row for row in missing_ref_rows
                    if abs(self._safe_float(row.get("credit_amount")) - pg_net) <= self.amount_tolerance
                ]
                if len(candidates) == 1:
                    bank_record = candidates[0]

            bank_credit = self._safe_float(bank_record.get("credit_amount")) if bank_record else 0.0
            bank_debit = self._safe_float(bank_record.get("debit_amount")) if bank_record else 0.0
            bank_ref = str(bank_record.get("bank_ref_utr", "")).strip() if bank_record else ""

            erp_booked = self._safe_float(erp_record.get("booked_amount")) if erp_record else 0.0
            erp_status = str(erp_record.get("status", "NOT_FOUND")).upper() if erp_record else "NOT_FOUND"
            erp_posting_date = str(erp_record.get("posting_date", "")).strip() if erp_record else ""

            expected_fee = round(gross * self.contracted_fee_rate, 2)
            expected_gst = round(expected_fee * self.contracted_gst_rate, 2)
            expected_net = round(gross - expected_fee - expected_gst, 2)
            fee_overcharge = round(max(0.0, (pg_fee + pg_gst) - (expected_fee + expected_gst)), 2)

            rec_status = "RECONCILED"
            category = "NONE"
            cause = ""
            action = ""

            if order_id in seen_order_ids:
                rec_status = "DISCREPANCY"
                category = "DUPLICATE_ENTRY"
                cause = f"Duplicate Payment Gateway record found for Order ID {order_id} (Payment ID: {pay_id})"
                action = "Void duplicate payment entry in PG settlement log and review API webhook idempotent headers."
            else:
                seen_order_ids.add(order_id)

            if category == "NONE" and pg_status == "FAILED" and bank_credit > 0:
                rec_status = "DISCREPANCY"
                category = "STATUS_MISMATCH"
                cause = f"PG payment marked FAILED, but Bank statement received credit of ₹{bank_credit:,.2f}"
                action = "Flag uncaptured bank credit to finance operations for manual verification or customer refund."

            if category == "NONE" and abs(pg_fee - expected_fee) > self.fee_tolerance:
                rec_status = "DISCREPANCY"
                category = "FEE_MISMATCH"
                cause = (
                    f"Gateway fee charged (₹{pg_fee:,.2f}) exceeds contracted fee "
                    f"(₹{expected_fee:,.2f}) at {self.contracted_fee_rate:.0%} rate"
                )
                action = "Raise fee dispute billing ticket with Payment Gateway support for overcharge credit."

            if category == "NONE" and (pg_status == "REFUNDED" or bank_debit > 0):
                if erp_status == "BOOKED" and erp_booked > 0:
                    rec_status = "DISCREPANCY"
                    category = "REFUND_UNACCOUNTED"
                    cause = f"Payment refunded in PG/Bank, but ERP ledger retains booked revenue of ₹{erp_booked:,.2f}"
                    action = "Post credit memo/refund journal entry in ERP to reverse revenue account credit."

            if category == "NONE" and erp_record and abs(erp_booked - gross) > self.amount_tolerance:
                rec_status = "DISCREPANCY"
                category = "ERP_AMOUNT_MISMATCH"
                cause = f"ERP booked invoice amount (₹{erp_booked:,.2f}) differs from PG gross amount (₹{gross:,.2f})"
                action = "Reconcile ERP sales order invoice line item against checkout coupon/discount variance."

            if category == "NONE" and erp_record and erp_posting_date and period_year is not None:
                posting_year = pd.to_datetime(erp_posting_date, errors="coerce")
                if not pd.isna(posting_year) and posting_year.year != period_year:
                    rec_status = "DISCREPANCY"
                    category = "TIMING_OUT_OF_PERIOD"
                    cause = f"ERP posting date ({erp_posting_date}) is outside current transaction period ({period_year})"
                    action = "Re-classify journal posting date to the active accounting period."

            if category == "NONE" and bank_record is None and pg_status == "SUCCESS":
                rec_status = "DISCREPANCY"
                category = "SETTLEMENT_DELAY"
                cause = f"Transaction cleared in PG (₹{pg_net:,.2f}), but missing from current Bank settlement statement"
                action = "Track payout batch status with bank node; flag for T+2 settlement follow-up."

            if category == "NONE" and bank_record is not None and self._is_missing_utr(bank_ref):
                rec_status = "DISCREPANCY"
                category = "MISSING_BANK_REF"
                cause = "Bank statement entry lacks valid UTR or reference number (corrupted narration)"
                action = "Request bank electronic statement re-query with the full UTR/reference field."

            if category == "NONE" and bank_record is not None:
                holdback = round(pg_net - bank_credit, 2)
                if holdback > self.partial_hold_threshold:
                    rec_status = "DISCREPANCY"
                    category = "PARTIAL_HOLD"
                    cause = f"Bank credit (₹{bank_credit:,.2f}) is short of expected payout (₹{pg_net:,.2f}) by ₹{holdback:,.2f}"
                    action = "Log rolling reserve / risk holdback entry in gateway clearing suspense account."

            variance = round(pg_net - bank_credit, 2)

            results.append(
                ReconciliationResultRow(
                    order_id=order_id,
                    payment_id=pay_id,
                    bank_utr=utr,
                    transaction_date=transaction_date,
                    reconciliation_status=rec_status,
                    discrepancy_category=category,
                    gross_amount=gross,
                    pg_net_payout=pg_net,
                    bank_credit_amount=bank_credit,
                    erp_booked_amount=erp_booked,
                    net_variance=variance,
                    fee_overcharge_amount=fee_overcharge,
                    failure_cause=cause,
                    remediation_action=action,
                )
            )

        return pd.DataFrame([asdict(row) for row in results])
