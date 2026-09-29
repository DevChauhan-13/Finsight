"""FinSight premium interactive controller UI.

The active application has three real surfaces:
Controller -> run an investigation and see the agent working -> clear output.
Evidence   -> inspect the authoritative PG / Bank / ERP records for a case.
Memory     -> inspect Hindsight context and record operator outcomes for learning.
"""
from __future__ import annotations

import html
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import streamlit as st

from src.agent.schemas import OperatorOutcomeInput
from src.dashboard.utils.common import (
    DATA_DIR,
    format_inr,
    init_session_state,
    load_custom_css,
    load_reconciliation_data,
    render_footer,
)
from src.normalization.schema_normalizer import (
    normalize_bank_dataset,
    normalize_erp_dataset,
    normalize_pg_dataset,
)


st.set_page_config(
    page_title="FinSight · AI Finance Controller",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()
load_custom_css()

results_df, perf, stats, discrepancy_df = load_reconciliation_data(False)


@st.cache_data(show_spinner=False)
def load_source_records() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the exact normalized source datasets used by reconciliation."""
    pg_path = DATA_DIR / "pg_transactions.csv"
    bank_path = DATA_DIR / "bank_settlements.csv"
    erp_path = DATA_DIR / "erp_ledger.json"

    pg_raw = pd.read_csv(pg_path)
    bank_raw = pd.read_csv(bank_path)
    erp_raw = json.loads(erp_path.read_text(encoding="utf-8"))
    return (
        normalize_pg_dataset(pg_raw, use_llm=False),
        normalize_bank_dataset(bank_raw, use_llm=False),
        normalize_erp_dataset(erp_raw, use_llm=False),
    )


PG_DF, BANK_DF, ERP_DF = load_source_records()


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _clean_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _case_options() -> list[str]:
    if discrepancy_df.empty:
        return [""]
    unique = discrepancy_df[["order_id", "discrepancy_category"]].drop_duplicates()
    return [
        "",
        *[
            f"{row.discrepancy_category.replace('_', ' ').title()} · {row.order_id}"
            for row in unique.itertuples(index=False)
        ],
    ]


def _order_from_case_label(label: str) -> str:
    if " · " not in label:
        return ""
    return label.rsplit(" · ", 1)[-1].strip()


def _find_case(raw_input: str) -> Optional[Dict[str, Any]]:
    """Resolve an Order ID / Payment ID, preferring the flagged duplicate row."""
    query = str(raw_input or "").strip()
    if not query:
        return None

    order_matches = results_df[
        results_df["order_id"].astype(str).str.casefold() == query.casefold()
    ]
    if not order_matches.empty:
        # Duplicate orders intentionally create one clean base row plus one flagged row.
        # Prefer the flagged row so a user never opens the clean record by mistake.
        if "reconciliation_status" in order_matches.columns:
            flagged = order_matches[
                order_matches["reconciliation_status"].astype(str).str.upper() == "DISCREPANCY"
            ]
            if not flagged.empty:
                return flagged.iloc[0].to_dict()
        return order_matches.iloc[0].to_dict()

    payment_matches = results_df[
        results_df["payment_id"].astype(str).str.casefold() == query.casefold()
    ]
    if not payment_matches.empty:
        return payment_matches.iloc[0].to_dict()

    # Tolerate a pasted one-field JSON payload.
    if query.startswith("{") and query.endswith("}"):
        try:
            payload = json.loads(query)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            key = str(payload.get("order_id") or payload.get("payment_id") or "").strip()
            if key:
                return _find_case(key)
    return None


def _find_source_records(case: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]:
    """Resolve the exact PG, Bank and ERP evidence rows backing a reconciled case."""
    order_id = str(case.get("order_id", "")).strip()
    payment_id = str(case.get("payment_id", "")).strip()
    utr = str(case.get("bank_utr", "")).strip()
    pg = None
    bank = None
    erp = None
    bank_match_method = ""

    if payment_id:
        matches = PG_DF[PG_DF["payment_id"].astype(str).str.casefold() == payment_id.casefold()]
        if not matches.empty:
            pg = matches.iloc[0].to_dict()
    if pg is None and order_id:
        matches = PG_DF[PG_DF["order_id"].astype(str).str.casefold() == order_id.casefold()]
        if not matches.empty:
            pg = matches.iloc[-1].to_dict()

    if utr:
        matches = BANK_DF[BANK_DF["bank_ref_utr"].astype(str).str.casefold() == utr.casefold()]
        if not matches.empty:
            bank = matches.iloc[0].to_dict()
            bank_match_method = "Matched on UTR"

    if bank is None and case.get("discrepancy_category") == "MISSING_BANK_REF" and pg:
        target = _clean_float(pg.get("net_payout"))
        candidates = BANK_DF[
            (BANK_DF["credit_amount"].astype(float) - target).abs() <= 0.01
        ]
        if len(candidates) == 1:
            bank = candidates.iloc[0].to_dict()
            bank_match_method = "Matched on settlement amount; bank UTR is missing/invalid"

    if order_id:
        matches = ERP_DF[ERP_DF["order_id"].astype(str).str.casefold() == order_id.casefold()]
        if not matches.empty:
            erp = matches.iloc[0].to_dict()

    return pg, bank, erp, bank_match_method


def _render_header() -> None:
    active = st.session_state.active_view
    brand, nav, system = st.columns([1.0, 1.55, 0.8], gap="medium")

    with brand:
        st.markdown(
            """
            <div class="fs-brand">
              <div class="fs-brand-mark">F</div>
              <div>
                <div class="fs-brand-name">FinSight</div>
                <div class="fs-brand-sub">AI finance controller</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with nav:
        n1, n2, n3 = st.columns(3, gap="small")
        for col, key, label in (
            (n1, "controller", "Controller"),
            (n2, "evidence", "Evidence"),
            (n3, "memory", "Memory"),
        ):
            with col:
                clicked = st.button(
                    label,
                    key=f"nav_{key}",
                    use_container_width=True,
                    disabled=active == key,
                )
                if clicked:
                    st.session_state.active_view = key

    with system:
        memory_online = st.session_state.memory_service.is_online
        status_text = "Backend online" if memory_online else "Controller ready"
        st.markdown(
            f'<div class="fs-system-chip"><span class="fs-status-dot"></span>{_esc(status_text)}</div>',
            unsafe_allow_html=True,
        )


def _render_page_title(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="fs-intro fs-page-intro">
          <div class="fs-eyebrow"><span class="fs-eyebrow-dot"></span>{_esc(eyebrow)}</div>
          <div class="fs-title">{_esc(title)}</div>
          <div class="fs-subtitle">{_esc(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_input_area() -> tuple[str, bool]:
    _render_page_title(
        "Exception investigation",
        "Turn a payment issue into a clear decision.",
        "Enter an Order ID or Payment ID. The controller resolves authoritative source data, visibly runs the investigation, then presents a review-ready result.",
    )

    with st.container(border=True):
        st.markdown('<div class="fs-card-kicker">Investigation input</div>', unsafe_allow_html=True)
        st.markdown('<div class="fs-card-title">Start with one transaction reference</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="fs-card-copy">The quick-case picker is an assistant only. It never overwrites the manual input field, so the two controls always remain independent.</div>',
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([1.6, 0.78], gap="medium")
        with c1:
            user_input = st.text_input(
                "Order ID / Payment ID",
                value=st.session_state.analysis_input,
                key="case_input_field",
                placeholder="e.g. ORD-2026-0046 or pay_RZP_000046",
                help="Enter an exact reference from the reconciled dataset.",
            )
        with c2:
            quick_label = st.selectbox(
                "Quick test case",
                _case_options(),
                index=0,
                key="quick_case_picker",
                format_func=lambda x: "Choose an exception…" if x == "" else x,
            )

        selected_order = _order_from_case_label(quick_label)
        choice_text = selected_order if selected_order else "None selected"
        st.markdown(
            f'<div class="fs-selection-strip"><span>Quick selection</span><b>{_esc(choice_text)}</b><em>Manual input takes precedence when filled.</em></div>',
            unsafe_allow_html=True,
        )

        note_cols = st.columns(3)
        notes = [
            ("Input", "Order ID or Payment ID"),
            ("Engine", "Deterministic reconciliation"),
            ("Context", "Hindsight memory when available"),
        ]
        for col, (label, value) in zip(note_cols, notes):
            with col:
                st.markdown(
                    f'<span class="fs-note-pill"><b>{_esc(label)}</b>&nbsp; {_esc(value)}</span>',
                    unsafe_allow_html=True,
                )

        run = st.button("Run investigation  →", type="primary", use_container_width=True)

    effective_input = user_input.strip() or selected_order
    return effective_input, run


def _stage_row(state: str, title: str, detail: str) -> str:
    return (
        f'<div class="fs-stage {state}"><span class="fs-stage-dot"></span>'
        f'<span><b>{_esc(title)}</b> · {_esc(detail)}</span></div>'
    )


def _category_tone(category: str) -> str:
    return {
        "FEE_MISMATCH": "gold",
        "SETTLEMENT_DELAY": "gold",
        "MISSING_BANK_REF": "gold",
        "ERP_AMOUNT_MISMATCH": "red",
        "REFUND_UNACCOUNTED": "red",
        "STATUS_MISMATCH": "red",
        "PARTIAL_HOLD": "gold",
        "DUPLICATE_ENTRY": "red",
        "TIMING_OUT_OF_PERIOD": "teal",
    }.get(category, "teal")


def _render_output(analysis, source_case: Dict[str, Any], elapsed: float) -> None:
    findings = analysis.deterministic_findings
    category = analysis.discrepancy_type
    tone = _category_tone(category)
    bank_utr = findings.get("bank_utr") or source_case.get("bank_utr") or "—"
    fee_leakage = _clean_float(findings.get("fee_overcharge_amount"))
    bank_variance = _clean_float(findings.get("net_variance"))
    historical_success = (
        f"{analysis.historical_pattern.success_rate_pct:.1f}%"
        if analysis.historical_pattern
        else "Not recorded"
    )
    sample_count = analysis.historical_pattern.sample_count if analysis.historical_pattern else 0
    turnaround = analysis.historical_pattern.average_turnaround_hours if analysis.historical_pattern else None
    turnaround_text = f"{turnaround:.1f}h" if turnaround is not None else "Not recorded"
    memory_label = "Memory context used" if analysis.memory_influenced else "No prior case found"
    memory_tone = "green" if analysis.memory_influenced else "teal"
    evidence = analysis.supporting_evidence or []

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="fs-result-head">
              <div>
                <div class="fs-card-kicker">Agent output · authoritative result</div>
                <div class="fs-result-title">{_esc(analysis.order_id)}</div>
                <div class="fs-result-sub">{_esc(analysis.payment_id)} · {_esc(analysis.case_id)} · completed in {elapsed:.2f}s</div>
              </div>
              <span class="fs-pill fs-pill-{tone}">{_esc(category.replace('_', ' '))}</span>
            </div>

            <div class="fs-metrics">
              <div class="fs-metric"><div class="fs-metric-label">Gross amount</div><div class="fs-metric-value">{format_inr(findings.get('gross_amount', 0), 2)}</div><div class="fs-metric-help">Payment gateway</div></div>
              <div class="fs-metric"><div class="fs-metric-label">PG net payout</div><div class="fs-metric-value">{format_inr(findings.get('pg_net_payout', 0), 2)}</div><div class="fs-metric-help">After gateway fee + GST</div></div>
              <div class="fs-metric"><div class="fs-metric-label">Bank credit</div><div class="fs-metric-value">{format_inr(findings.get('bank_credit_amount', 0), 2)}</div><div class="fs-metric-help">Settlement evidence</div></div>
              <div class="fs-metric"><div class="fs-metric-label">ERP booked</div><div class="fs-metric-value">{format_inr(findings.get('erp_booked_amount', 0), 2)}</div><div class="fs-metric-help">Ledger amount</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        p1, p2, p3 = st.columns([1.1, 1.1, 0.9], gap="medium")
        with p1:
            st.markdown(
                f"""
                <div class="fs-panel highlight">
                  <div class="fs-card-kicker">What the engine found</div>
                  <div class="fs-panel-title">{_esc(category.replace('_', ' '))}</div>
                  <div class="fs-panel-copy">{_esc(analysis.reasoning_summary)}</div>
                  <div class="fs-kv"><span class="k">Bank variance</span><span class="v">{format_inr(bank_variance, 2)}</span></div>
                  <div class="fs-kv"><span class="k">Fee leakage</span><span class="v">{format_inr(fee_leakage, 2)}</span></div>
                  <div class="fs-kv"><span class="k">Bank UTR</span><span class="v">{_esc(bank_utr)}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with p2:
            st.markdown(
                f"""
                <div class="fs-panel gold">
                  <div class="fs-card-kicker">Recommended action</div>
                  <div class="fs-panel-title">{_esc(analysis.recommended_action)}</div>
                  <div class="fs-panel-copy">{_esc(analysis.current_case_summary)}</div>
                  <div class="fs-memory-line"><span class="fs-pill fs-pill-green">Human review required</span><span>{analysis.confidence * 100:.0f}% synthesis confidence</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with p3:
            st.markdown(
                f"""
                <div class="fs-panel">
                  <div class="fs-card-kicker">Memory signal</div>
                  <div style="margin-top:6px"><span class="fs-pill fs-pill-{memory_tone}">{_esc(memory_label)}</span></div>
                  <div class="fs-kv" style="margin-top:8px"><span class="k">Similar cases</span><span class="v">{sample_count}</span></div>
                  <div class="fs-kv"><span class="k">Historical success</span><span class="v">{_esc(historical_success)}</span></div>
                  <div class="fs-kv"><span class="k">Avg. turnaround</span><span class="v">{_esc(turnaround_text)}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        pg, bank, erp, bank_method = _find_source_records(source_case)
        if pg:
            gateway_fee = _clean_float(pg.get("gateway_fee"))
            gst = _clean_float(pg.get("gst_tax"))
            gross = _clean_float(pg.get("gross_amount"))
            expected_fee = round(gross * 0.02, 2)
            expected_gst = round(expected_fee * 0.18, 2)
            if category == "FEE_MISMATCH":
                st.markdown(
                    f"""
                    <div class="fs-panel fs-math-panel">
                      <div class="fs-card-kicker">Fee audit math</div>
                      <div class="fs-math-grid">
                        <div><span>Contracted fee</span><b>{format_inr(expected_fee,2)}</b></div>
                        <div><span>Contracted GST</span><b>{format_inr(expected_gst,2)}</b></div>
                        <div><span>Charged fee</span><b>{format_inr(gateway_fee,2)}</b></div>
                        <div><span>Charged GST</span><b>{format_inr(gst,2)}</b></div>
                        <div class="wide"><span>Fee + GST leakage</span><b>{format_inr(fee_leakage,2)}</b></div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        evidence_html = "".join(
            f'<span>{_esc(item)}</span>' for item in evidence
        )
        st.markdown(
            f"""
            <div class="fs-panel" style="margin-top:12px">
              <div class="fs-card-kicker">Evidence package</div>
              <div class="fs-panel-copy">These are the records and signals the controller expects an operator to verify before approval.</div>
              <div class="fs-evidence">{evidence_html or '<span>No evidence items returned.</span>'}</div>
              <div style="margin-top:13px" class="fs-panel-copy"><span class="fs-strong">Next step:</span> {_esc(analysis.expected_next_step)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("View investigation payload", expanded=False):
            raw_view = {
                "case_id": analysis.case_id,
                "order_id": analysis.order_id,
                "payment_id": analysis.payment_id,
                "discrepancy_type": analysis.discrepancy_type,
                "deterministic_findings": analysis.deterministic_findings,
                "memory_influenced": analysis.memory_influenced,
                "memory_matches": [m.model_dump() for m in analysis.memory_matches],
                "historical_pattern": analysis.historical_pattern.model_dump() if analysis.historical_pattern else None,
                "supporting_evidence": analysis.supporting_evidence,
            }
            st.json(raw_view)

        st.download_button(
            "Download investigation JSON",
            data=json.dumps(raw_view, indent=2, default=str),
            file_name=f"{analysis.case_id}.json",
            mime="application/json",
            use_container_width=True,
        )


def _render_controller() -> None:
    user_input, run = _render_input_area()

    if run:
        st.session_state.analysis_input = user_input
        source_case = _find_case(user_input)
        st.session_state.analysis = None

        if source_case is None:
            st.markdown(
                '<div class="fs-empty"><div class="fs-empty-title">Case not found in the authoritative dataset.</div><div class="fs-empty-copy">Use an exact Order ID or Payment ID from the current reconciled data. FinSight will never fabricate financial values from unsupported free text.</div></div>',
                unsafe_allow_html=True,
            )
            render_footer()
            return

        started = time.perf_counter()
        with st.status("Agent is working…", expanded=True) as status:
            stage_log = st.container()
            stage_log.markdown(
                _stage_row("done", "Reading the case", f"Resolved {source_case.get('order_id')} from the authoritative reconciliation dataset."),
                unsafe_allow_html=True,
            )
            stage_log.markdown(
                _stage_row("active", "Running finance controller", "Executing deterministic reconciliation and exception synthesis."),
                unsafe_allow_html=True,
            )
            analysis = st.session_state.agent.analyze_discrepancy(source_case)
            stage_log.markdown(
                _stage_row("done", "Running finance controller", "Financial logic completed from PG, Bank and ERP evidence."),
                unsafe_allow_html=True,
            )
            stage_log.markdown(
                _stage_row(
                    "done",
                    "Checking memory",
                    "Hindsight context attached to the recommendation." if analysis.memory_influenced else "No matching prior memory case was found.",
                ),
                unsafe_allow_html=True,
            )
            elapsed = time.perf_counter() - started
            stage_log.markdown(
                _stage_row("done", "Preparing output", f"Review-ready result prepared in {elapsed:.2f}s."),
                unsafe_allow_html=True,
            )
            status.update(label="Investigation complete", state="complete", expanded=False)

        st.session_state.analysis = analysis
        _render_output(analysis, source_case, elapsed)
        render_footer()
        return

    if st.session_state.analysis is not None:
        source_case = _find_case(st.session_state.analysis_input)
        if source_case is not None:
            st.markdown('<div style="height:3px"></div>', unsafe_allow_html=True)
            _render_output(st.session_state.analysis, source_case, 0.0)
    else:
        st.markdown(
            '<div class="fs-empty"><div class="fs-empty-title">Ready when you are.</div><div class="fs-empty-copy">Start with <b>ORD-2026-0046</b> to see a fee exception with separate bank variance and fee leakage, or choose another exception from the quick-case picker.</div></div>',
            unsafe_allow_html=True,
        )

    render_footer()


def _render_case_picker(label: str = "Case") -> Optional[Dict[str, Any]]:
    current = st.session_state.analysis_input
    labels = _case_options()
    default_order = current if current else ""
    choice_labels = [""] + labels[1:]
    current_index = 0
    for idx, option in enumerate(choice_labels):
        if default_order and _order_from_case_label(option) == default_order:
            current_index = idx
            break
    selected = st.selectbox(
        label,
        choice_labels,
        index=current_index,
        format_func=lambda x: "Choose a case…" if x == "" else x,
        key=f"{label.lower().replace(' ', '_')}_picker",
    )
    order_id = _order_from_case_label(selected) or default_order
    if not order_id:
        return None
    return _find_case(order_id)


def _record_card(title: str, subtitle: str, pairs: list[tuple[str, Any]]) -> None:
    rows = "".join(
        f'<div class="fs-kv"><span class="k">{_esc(k)}</span><span class="v">{_esc(v if v not in (None, "") else "—")}</span></div>'
        for k, v in pairs
    )
    st.markdown(
        f"""
        <div class="fs-panel">
          <div class="fs-card-kicker">{_esc(title)}</div>
          <div class="fs-panel-title">{_esc(subtitle)}</div>
          <div style="margin-top:7px">{rows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_evidence() -> None:
    _render_page_title(
        "Evidence workspace",
        "See the records behind the decision.",
        "Evidence is not synthesized from the recommendation. This view resolves the normalized source records used by the deterministic engine so an operator can verify the chain directly.",
    )
    case = _render_case_picker("Evidence case")
    if case is None:
        st.markdown(
            '<div class="fs-empty"><div class="fs-empty-title">Choose a case to inspect.</div><div class="fs-empty-copy">Run a controller investigation first, or select any seeded exception above.</div></div>',
            unsafe_allow_html=True,
        )
        render_footer()
        return

    pg, bank, erp, bank_method = _find_source_records(case)
    status_tone = _category_tone(str(case.get("discrepancy_category", "")))
    st.markdown(
        f'<div class="fs-context-bar"><span class="fs-pill fs-pill-{status_tone}">{_esc(str(case.get("discrepancy_category", "NONE")).replace("_", " "))}</span><b>{_esc(case.get("order_id"))}</b><span>{_esc(case.get("payment_id"))}</span></div>',
        unsafe_allow_html=True,
    )

    p1, p2, p3 = st.columns(3, gap="medium")
    with p1:
        _record_card(
            "Payment gateway",
            "Authoritative PG record",
            [
                ("Payment ID", pg.get("payment_id") if pg else None),
                ("Order ID", pg.get("order_id") if pg else None),
                ("Gross amount", format_inr(pg.get("gross_amount", 0), 2) if pg else None),
                ("Gateway fee", format_inr(pg.get("gateway_fee", 0), 2) if pg else None),
                ("GST", format_inr(pg.get("gst_tax", 0), 2) if pg else None),
                ("Net payout", format_inr(pg.get("net_payout", 0), 2) if pg else None),
                ("Status", pg.get("status") if pg else None),
            ],
        )
    with p2:
        _record_card(
            "Bank settlement",
            "Authoritative bank record",
            [
                ("Bank UTR", bank.get("bank_ref_utr") if bank else None),
                ("Credit", format_inr(bank.get("credit_amount", 0), 2) if bank else None),
                ("Debit", format_inr(bank.get("debit_amount", 0), 2) if bank else None),
                ("Settlement date", bank.get("settlement_date") if bank else None),
                ("Status", bank.get("settlement_status") if bank else None),
                ("Narration", bank.get("narrative_raw") if bank else None),
                ("Match method", bank_method or "No bank record matched"),
            ],
        )
    with p3:
        _record_card(
            "ERP ledger",
            "Authoritative ledger record",
            [
                ("Order ID", erp.get("order_id") if erp else None),
                ("Journal entry", erp.get("journal_entry_id") if erp else None),
                ("Invoice ref", erp.get("invoice_reference") if erp else None),
                ("Booked amount", format_inr(erp.get("booked_amount", 0), 2) if erp else None),
                ("Posting date", erp.get("posting_date") if erp else None),
                ("Status", erp.get("status") if erp else None),
                ("UTR number", erp.get("utr_number") if erp else None),
            ],
        )

    if pg:
        gross = _clean_float(pg.get("gross_amount"))
        fee = _clean_float(pg.get("gateway_fee"))
        gst = _clean_float(pg.get("gst_tax"))
        net = _clean_float(pg.get("net_payout"))
        bank_credit = _clean_float(bank.get("credit_amount")) if bank else 0.0
        erp_booked = _clean_float(erp.get("booked_amount")) if erp else 0.0
        st.markdown(
            f"""
            <div class="fs-panel fs-trace-panel">
              <div class="fs-card-kicker">Reconciliation trace</div>
              <div class="fs-trace">
                <div><span>PG gross</span><b>{format_inr(gross,2)}</b></div>
                <div><span>PG fee + GST</span><b>{format_inr(fee+gst,2)}</b></div>
                <div><span>PG net payout</span><b>{format_inr(net,2)}</b></div>
                <div><span>Bank credit</span><b>{format_inr(bank_credit,2)}</b></div>
                <div><span>ERP booked</span><b>{format_inr(erp_booked,2)}</b></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Open raw normalized records", expanded=False):
        for title, record in (("Payment Gateway", pg), ("Bank", bank), ("ERP", erp)):
            st.markdown(f"**{title}**")
            st.json(record or {})

    render_footer()


def _render_memory() -> None:
    _render_page_title(
        "Learning memory",
        "Make the controller better with operator outcomes.",
        "Memory is a separate feature from financial truth. Hindsight contributes prior experience and patterns; the deterministic reconciliation engine remains authoritative for current amounts and status.",
    )

    memory = st.session_state.memory_service
    online = memory.is_online
    total = memory.total_memories()
    status = "Hindsight server connected" if online else "Local fallback memory active"
    tone = "green" if online else "gold"

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.markdown(
            f'<div class="fs-stat-card"><div class="fs-card-kicker">Connection</div><div class="fs-stat-value">{_esc(status)}</div><div class="fs-stat-help">{_esc(memory.client.base_url)}</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="fs-stat-card"><div class="fs-card-kicker">Stored memories</div><div class="fs-stat-value">{total}</div><div class="fs-stat-help">Retained learning experiences</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="fs-stat-card"><div class="fs-card-kicker">Role of memory</div><div class="fs-stat-value"><span class="fs-pill fs-pill-{tone}">Context only</span></div><div class="fs-stat-help">Never overrides financial facts</div></div>',
            unsafe_allow_html=True,
        )

    case = _render_case_picker("Memory case")
    if case is not None:
        st.markdown(
            f'<div class="fs-context-bar"><span class="fs-pill fs-pill-teal">{_esc(case.get("discrepancy_category", "UNKNOWN").replace("_", " "))}</span><b>{_esc(case.get("order_id"))}</b><span>{_esc(case.get("payment_id"))}</span></div>',
            unsafe_allow_html=True,
        )

        if st.button("Recall similar cases  →", type="secondary", use_container_width=True):
            with st.spinner("Recalling similar operator experiences…"):
                recalled = memory.recall_similar_exceptions(
                    discrepancy_type=str(case.get("discrepancy_category", "UNKNOWN")),
                    gateway="Razorpay",
                    merchant_name="Apex Retail",
                    failure_cause=str(case.get("failure_cause", "")),
                    net_variance=_clean_float(case.get("net_variance")),
                )
            st.session_state.memory_recall = recalled

        recalled = st.session_state.get("memory_recall", [])
        if recalled:
            st.markdown(f'<div class="fs-card-kicker" style="margin-top:16px">{len(recalled)} recalled experience(s)</div>', unsafe_allow_html=True)
            for item in recalled:
                text = str(item.get("text", "")).strip()
                st.markdown(
                    f"""
                    <div class="fs-memory-card">
                      <div class="fs-memory-id">{_esc(item.get('id','memory'))}</div>
                      <div class="fs-memory-text">{_esc(text[:1400])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="fs-empty"><div class="fs-empty-title">No recalled history yet.</div><div class="fs-empty-copy">Record an operator outcome below and that experience becomes the durable context for later investigations.</div></div>',
                unsafe_allow_html=True,
            )

        analysis = st.session_state.analysis
        if analysis and analysis.order_id == case.get("order_id") and analysis.historical_pattern:
            hp = analysis.historical_pattern
            st.markdown(
                f"""
                <div class="fs-panel fs-history-panel" style="margin-top:14px">
                  <div class="fs-card-kicker">Observed pattern</div>
                  <div class="fs-panel-title">{_esc(hp.pattern_description)}</div>
                  <div class="fs-kv"><span class="k">Samples</span><span class="v">{hp.sample_count}</span></div>
                  <div class="fs-kv"><span class="k">Observed success</span><span class="v">{hp.success_rate_pct:.1f}%</span></div>
                  <div class="fs-kv"><span class="k">Avg. turnaround</span><span class="v">{hp.average_turnaround_hours:.1f}h</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if analysis and analysis.order_id == case.get("order_id"):
            st.markdown('<div class="fs-card-kicker" style="margin-top:20px">Operator learning loop</div>', unsafe_allow_html=True)
            with st.form("operator_resolution_form", clear_on_submit=False):
                outcome_status = st.selectbox(
                    "Outcome",
                    ["RESOLVED", "UNSUCCESSFUL", "ESCALATED"],
                    key="memory_outcome_status",
                )
                final_resolution = st.text_area(
                    "Final resolution",
                    placeholder="e.g. Gateway credited the excess fee after dispute review.",
                    key="memory_final_resolution",
                )
                operator_notes = st.text_area(
                    "Operator notes",
                    placeholder="Add concise evidence or handling notes for future cases.",
                    key="memory_operator_notes",
                )
                evidence_submitted = st.text_input(
                    "Evidence submitted (comma separated)",
                    placeholder="Settlement batch ID, bank statement, gateway invoice",
                    key="memory_evidence_submitted",
                )
                save = st.form_submit_button("Record outcome & retain memory  →", type="primary", use_container_width=True)

            if save:
                if not final_resolution.strip():
                    st.error("Final resolution is required before the outcome can be retained.")
                else:
                    outcome = OperatorOutcomeInput(
                        case_id=analysis.case_id,
                        outcome_status=outcome_status,
                        final_resolution=final_resolution.strip(),
                        operator_notes=operator_notes.strip(),
                        evidence_submitted=[x.strip() for x in evidence_submitted.split(",") if x.strip()],
                    )
                    with st.spinner("Retaining operator experience…"):
                        result = st.session_state.agent.record_operator_resolution(analysis.case_id, outcome)
                    if result.get("status") == "success":
                        st.success("Operator outcome retained. Future investigations can recall this experience.")
                        st.session_state.memory_recall = []
                    else:
                        st.error(result.get("error", "Memory retention failed."))
    else:
        st.markdown(
            '<div class="fs-empty"><div class="fs-empty-title">Choose a case to inspect memory.</div><div class="fs-empty-copy">The controller must first analyze a case before an operator outcome can be stored against it.</div></div>',
            unsafe_allow_html=True,
        )

    render_footer()


def main() -> None:
    _render_header()
    active = st.session_state.active_view
    if active == "controller":
        _render_controller()
    elif active == "evidence":
        _render_evidence()
    else:
        _render_memory()


if __name__ == "__main__":
    main()
