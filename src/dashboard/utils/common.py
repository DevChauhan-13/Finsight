"""Shared data and visual utilities for the single-screen FinSight controller UI."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import streamlit as st

from src.agent.reconciliation_agent import FinancialReconciliationAgent
from src.memory.memory_service import FinSightMemoryService
from src.metrics.diagnostics import ReconciliationDiagnostics
from src.normalization.schema_normalizer import (
    normalize_bank_dataset,
    normalize_erp_dataset,
    normalize_pg_dataset,
)
from src.reconciliation.engine import DeterministicReconciliationEngine


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"


def init_session_state() -> None:
    """Initialize shared session state for the interactive controller."""
    if "memory_service" not in st.session_state:
        st.session_state.memory_service = FinSightMemoryService()
    if "agent" not in st.session_state:
        st.session_state.agent = FinancialReconciliationAgent(st.session_state.memory_service)
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "analysis_input" not in st.session_state:
        st.session_state.analysis_input = ""
    if "last_case_lookup" not in st.session_state:
        st.session_state.last_case_lookup = ""
    if "active_view" not in st.session_state:
        st.session_state.active_view = "controller"
    if "memory_recall" not in st.session_state:
        st.session_state.memory_recall = []


def format_inr(value: float, decimals: int = 0) -> str:
    """Format INR consistently."""
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"₹{amount:,.{decimals}f}"


def safe_text(value: Any, fallback: str = "—") -> str:
    text = str(value).strip() if value is not None else ""
    return html.escape(text) if text else fallback


def _pill(tone: str, label: str) -> str:
    return f'<span class="fs-pill fs-pill-{html.escape(tone)}">{html.escape(label)}</span>'


def load_custom_css() -> None:
    """Inject the focused, premium single-screen application theme."""
    css = r"""
    <style>
      :root {
        --fs-ink: #0b2026;
        --fs-ink-soft: #2c454b;
        --fs-muted: #6d7f83;
        --fs-teal-950: #09262d;
        --fs-teal-900: #0d3b45;
        --fs-teal-800: #1f5f6b;
        --fs-teal-700: #2d7682;
        --fs-teal-200: #cde5e8;
        --fs-teal-100: #eaf4f5;
        --fs-gold: #d8aa54;
        --fs-gold-100: #f9f0dc;
        --fs-green: #2e7d65;
        --fs-green-100: #e7f3ed;
        --fs-red: #af564e;
        --fs-red-100: #f8e9e6;
        --fs-paper: #f4f7f7;
        --fs-surface: #ffffff;
        --fs-line: #dfe8e9;
        --fs-shadow: 0 18px 55px rgba(18, 61, 69, 0.10);
        --fs-shadow-soft: 0 9px 24px rgba(18, 61, 69, 0.07);
      }

      html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
      .stApp {
        background:
          radial-gradient(circle at 92% 3%, rgba(216,170,84,.11), transparent 26%),
          radial-gradient(circle at 3% 18%, rgba(45,118,130,.08), transparent 26%),
          var(--fs-paper);
        color: var(--fs-ink);
      }
      [data-testid="stAppViewContainer"] { background: transparent; }
      [data-testid="stMain"] .block-container { max-width: 1240px; padding: 1.0rem 1.6rem 3rem; }
      header[data-testid="stHeader"] { background: rgba(244,247,247,.78); }

      /* Hide the default multipage navigation: this build is intentionally a single controller surface. */
      [data-testid="stSidebarNav"] { display: none !important; }
      [data-testid="stSidebar"] { display: none !important; }
      [data-testid="stToolbar"] { visibility: hidden; height: 0; }
      div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--fs-line) !important;
        border-radius: 24px !important;
        background: rgba(255,255,255,.92) !important;
        box-shadow: var(--fs-shadow) !important;
      }
      div[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 24px !important; }

      .fs-topbar {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        gap: 18px;
        min-height: 56px;
        padding: 8px 10px 8px 12px;
        margin-bottom: 16px;
      }
      .fs-brand {
        display: inline-flex;
        align-items: center;
        gap: 11px;
      }
      .fs-brand-mark {
        width: 39px;
        height: 39px;
        display: grid;
        place-items: center;
        border-radius: 12px;
        color: #fff;
        font-size: 17px;
        font-weight: 850;
        background: linear-gradient(145deg, #4d95a0, #1c5a65);
        box-shadow: inset 0 0 0 1px rgba(255,255,255,.2), 0 9px 22px rgba(13,59,69,.16);
      }
      .fs-brand-name { font-size: 1.03rem; line-height: 1.05; font-weight: 850; letter-spacing: -.02em; }
      .fs-brand-sub { margin-top: 3px; color: #819094; font-size: .66rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
      .fs-topnav {
        justify-self: center;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px;
        border: 1px solid rgba(19,62,70,.08);
        background: rgba(255,255,255,.78);
        border-radius: 999px;
        box-shadow: 0 9px 22px rgba(18,61,69,.08);
      }
      .fs-topnav-pill { padding: 8px 18px; border-radius: 999px; color: #77888c; font-size: .71rem; font-weight: 800; }
      .fs-topnav-pill.active { color: #fff; background: linear-gradient(135deg,#2d7682,#1f5f6b); }
      .fs-topbar-right { justify-self: end; display:flex; align-items:center; gap:8px; }

      .fs-status-dot {
        width: 7px; height: 7px; border-radius: 50%; background: #39a17d; box-shadow: 0 0 0 5px rgba(57,161,125,.11);
      }
      .fs-system-chip { display:inline-flex; align-items:center; gap:9px; padding:8px 11px; border-radius:999px; background:#eef5f4; color:#2c6c63; font-size:.69rem; font-weight:800; }

      .fs-intro {
        padding: 8px 0 15px;
      }
      .fs-eyebrow {
        display:inline-flex; align-items:center; gap:8px; padding:7px 11px; border-radius:999px;
        color:#255d66; background:rgba(45,118,130,.09); border:1px solid rgba(45,118,130,.09);
        font-size:.68rem; font-weight:850; letter-spacing:.08em; text-transform:uppercase;
      }
      .fs-eyebrow-dot { width:6px; height:6px; border-radius:50%; background:var(--fs-gold); box-shadow:0 0 0 4px rgba(216,170,84,.13); }
      .fs-title { margin:14px 0 9px; font-size:clamp(2.25rem,5.1vw,4.8rem); line-height:.98; letter-spacing:-.065em; font-weight:880; color:#07191e; max-width:900px; }
      .fs-title .accent {
        background: linear-gradient(100deg,#0f4651,#2d7682 62%,#6eaab0);
        -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
      }
      .fs-subtitle { max-width:790px; color:#64777b; font-size:.98rem; line-height:1.65; }

      .fs-work-card, .fs-output-card {
        border:1px solid var(--fs-line); background:rgba(255,255,255,.93); border-radius:24px; box-shadow:var(--fs-shadow);
      }
      .fs-work-card { padding:24px; margin-top:15px; }
      .fs-output-card { padding:22px; margin-top:16px; }
      .fs-card-kicker { color:#87979a; font-size:.65rem; font-weight:850; letter-spacing:.11em; text-transform:uppercase; }
      .fs-card-title { color:#0d272e; font-size:1.03rem; font-weight:850; letter-spacing:-.02em; margin-top:5px; }
      .fs-card-copy { color:#6c7e82; font-size:.79rem; line-height:1.55; margin-top:7px; }
      .fs-input-note { display:flex; gap:7px; flex-wrap:wrap; margin-top:10px; color:#819094; font-size:.68rem; }
      .fs-note-pill { display:inline-flex; padding:5px 8px; border-radius:8px; background:#f2f6f6; border:1px solid #e4ebec; color:#6b7e82; }

      .fs-pill { display:inline-flex; align-items:center; padding:6px 9px; border-radius:999px; font-size:.66rem; font-weight:850; letter-spacing:.02em; white-space:nowrap; }
      .fs-pill-teal { background:var(--fs-teal-100); color:#245e67; }
      .fs-pill-gold { background:var(--fs-gold-100); color:#866820; }
      .fs-pill-green { background:var(--fs-green-100); color:#2c715c; }
      .fs-pill-red { background:var(--fs-red-100); color:#924a43; }
      .fs-pill-dark { background:#e8eef0; color:#355159; }

      .fs-button-row { display:flex; gap:9px; align-items:center; }
      .stButton > button, .stDownloadButton > button {
        border-radius:999px; border:1px solid #dbe5e6; min-height:42px; font-weight:800; letter-spacing:-.01em;
        background:#fff; color:#1b434c; box-shadow:0 6px 14px rgba(19,62,70,.05); transition:all .15s ease;
      }
      .stButton > button:hover, .stDownloadButton > button:hover { border-color:#b7cdd0; transform:translateY(-1px); }
      .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
        color:#fff; border-color:transparent; background:linear-gradient(135deg,#2d7682,#1c5662); box-shadow:0 12px 24px rgba(31,95,107,.22);
      }
      .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover { background:linear-gradient(135deg,#317f8b,#215f6b); }

      .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
        border-radius:12px !important; border-color:#d5e1e2 !important; background:#fcfefe !important;
        min-height:43px; font-size:.86rem !important;
      }
      .stTextInput input:focus, .stTextArea textarea:focus { border-color:#76aab1 !important; box-shadow:0 0 0 3px rgba(45,118,130,.10) !important; }
      label { color:#4e676d !important; font-size:.72rem !important; font-weight:800 !important; }

      .fs-run-status {
        border:1px solid #dce8e9; background:#f9fcfc; border-radius:18px; padding:15px 17px; margin-top:15px;
      }
      .fs-stage { display:flex; align-items:center; gap:11px; padding:8px 0; border-bottom:1px solid #edf2f2; font-size:.76rem; color:#5f7478; }
      .fs-stage:last-child { border-bottom:0; }
      .fs-stage-dot { width:9px; height:9px; border-radius:50%; background:#cbd9db; flex:0 0 auto; }
      .fs-stage.done .fs-stage-dot { background:#38a27d; box-shadow:0 0 0 4px rgba(56,162,125,.10); }
      .fs-stage.active .fs-stage-dot { background:#d7a850; box-shadow:0 0 0 4px rgba(215,168,80,.10); }

      .fs-result-head { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; flex-wrap:wrap; }
      .fs-result-title { font-size:1.35rem; line-height:1.08; font-weight:880; letter-spacing:-.035em; color:#0a232a; margin-top:6px; }
      .fs-result-sub { color:#708185; font-size:.76rem; margin-top:6px; }
      .fs-metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin-top:17px; }
      .fs-metric { padding:14px 15px; border-radius:15px; background:linear-gradient(180deg,#ffffff,#fbfdfd); border:1px solid #e2e9ea; }
      .fs-metric-label { color:#819094; font-size:.63rem; font-weight:850; letter-spacing:.10em; text-transform:uppercase; }
      .fs-metric-value { color:#183b44; font-size:1.15rem; font-weight:860; margin-top:5px; }
      .fs-metric-help { color:#99a6a8; font-size:.63rem; margin-top:3px; }

      .fs-grid-3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-top:13px; }
      .fs-panel { border:1px solid #e3eaeb; background:#fcfefe; border-radius:17px; padding:16px; }
      .fs-panel.highlight { background:linear-gradient(145deg,#f7fbfb,#f2f8f8); border-color:#cfe1e3; }
      .fs-panel.gold { background:linear-gradient(145deg,#fffdf8,#fbf5e8); border-color:#eadfca; }
      .fs-panel.red { background:linear-gradient(145deg,#fffafa,#fdf0ed); border-color:#ecd8d5; }
      .fs-panel-title { color:#163941; font-size:.83rem; font-weight:850; margin-top:4px; }
      .fs-panel-copy { color:#66797d; font-size:.73rem; line-height:1.55; margin-top:8px; }
      .fs-strong { color:#123f49; font-weight:850; }
      .fs-kv { display:flex; justify-content:space-between; gap:10px; padding:8px 0; border-bottom:1px solid #edf2f2; font-size:.72rem; }
      .fs-kv:last-child { border-bottom:0; }
      .fs-kv .k { color:#74878a; }
      .fs-kv .v { color:#1c3f47; font-weight:800; text-align:right; }

      .fs-evidence { display:flex; flex-wrap:wrap; gap:7px; margin-top:9px; }
      .fs-evidence span { padding:6px 8px; border-radius:8px; background:#eef4f4; color:#46666c; border:1px solid #dfe9ea; font-size:.67rem; font-weight:760; }
      .fs-memory-line { display:flex; align-items:center; gap:8px; margin-top:8px; color:#5d7378; font-size:.72rem; }

      .fs-empty {
        padding:34px 28px; margin-top:16px; border:1px dashed #cddbdd; border-radius:20px; background:rgba(255,255,255,.65); text-align:center;
      }
      .fs-empty-title { font-weight:850; color:#1c4149; font-size:1rem; }
      .fs-empty-copy { max-width:600px; margin:7px auto 0; color:#788b8f; font-size:.74rem; line-height:1.55; }

      .fs-footer { margin-top:26px; padding-top:14px; border-top:1px solid #dfe8e9; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; color:#87979a; font-size:.63rem; }
      .fs-footer strong { color:#547077; }


      /* Functional top navigation. The disabled button is intentionally the active pill. */
      .fs-topnav-btn button {
        border-radius: 999px !important;
        min-height: 35px !important;
        padding: 0 15px !important;
        border: 1px solid transparent !important;
        background: transparent !important;
        color: #6f8185 !important;
        font-size: .71rem !important;
        font-weight: 820 !important;
        box-shadow: none !important;
      }
      .fs-topnav-btn button:hover {
        color: #1f5f6b !important;
        border-color: #dbe7e8 !important;
        background: #f7fbfb !important;
        transform: none !important;
      }
      .fs-topnav-btn button:disabled {
        opacity: 1 !important;
        color: #fff !important;
        background: linear-gradient(135deg,#2d7682,#1f5f6b) !important;
        border-color: transparent !important;
        box-shadow: 0 7px 16px rgba(31,95,107,.18) !important;
      }

      .fs-selection-strip {
        display:flex; align-items:center; gap:9px; flex-wrap:wrap; margin-top:12px;
        padding:9px 11px; border:1px solid #e0e9ea; border-radius:11px; background:#f8fbfb;
        color:#768a8e; font-size:.68rem;
      }
      .fs-selection-strip b { color:#1f5661; font-weight:850; }
      .fs-selection-strip em { margin-left:auto; color:#9aa7a9; font-style:normal; }

      .fs-context-bar {
        display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:15px 0 12px;
        padding:10px 12px; border:1px solid #dfe9ea; border-radius:14px; background:rgba(255,255,255,.78);
        color:#6b7d81; font-size:.74rem; box-shadow:var(--fs-shadow-soft);
      }
      .fs-context-bar b { color:#173d46; font-weight:850; }

      .fs-stat-card {
        min-height:118px; padding:16px; border-radius:17px; background:rgba(255,255,255,.92);
        border:1px solid #e1e9ea; box-shadow:var(--fs-shadow-soft);
      }
      .fs-stat-value { margin-top:8px; color:#173b44; font-size:1.0rem; font-weight:850; line-height:1.25; }
      .fs-stat-help { margin-top:6px; color:#879699; font-size:.66rem; line-height:1.45; word-break:break-word; }

      .fs-math-panel, .fs-trace-panel { margin-top:12px; background:linear-gradient(145deg,#fbfdfd,#f5f9f9); }
      .fs-math-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; margin-top:10px; }
      .fs-math-grid > div { display:flex; justify-content:space-between; gap:10px; padding:9px 10px; border:1px solid #e2eaeb; border-radius:11px; background:#fff; }
      .fs-math-grid span { color:#75878b; font-size:.67rem; }
      .fs-math-grid b { color:#1c4650; font-size:.74rem; }
      .fs-math-grid .wide { grid-column:1 / -1; background:#fffaf0; border-color:#eadfca; }
      .fs-math-grid .wide b { color:#856620; }

      .fs-trace { display:flex; align-items:stretch; gap:7px; margin-top:10px; overflow-x:auto; }
      .fs-trace > div { min-width:145px; padding:11px; border:1px solid #e1eaeb; border-radius:12px; background:#fff; }
      .fs-trace span { display:block; color:#839397; font-size:.61rem; text-transform:uppercase; letter-spacing:.06em; font-weight:800; }
      .fs-trace b { display:block; margin-top:5px; color:#1d444d; font-size:.79rem; }

      .fs-memory-card { margin-top:9px; padding:13px 14px; border:1px solid #e0e9ea; border-radius:14px; background:#fff; box-shadow:var(--fs-shadow-soft); }
      .fs-memory-id { color:#7c8f93; font-size:.61rem; font-weight:850; letter-spacing:.08em; text-transform:uppercase; }
      .fs-memory-text { margin-top:6px; color:#5e7276; font-size:.72rem; line-height:1.58; white-space:pre-wrap; }
      .fs-history-panel { background:linear-gradient(145deg,#f7fbfb,#f0f7f7); }

      @media (max-width: 980px) {
        .fs-math-grid { grid-template-columns:1fr; }
        .fs-math-grid .wide { grid-column:auto; }
        .fs-selection-strip em { width:100%; margin-left:0; }
      }

      div[data-testid="stAlert"] { border-radius:13px !important; }
      @media (max-width: 980px) {
        .fs-topbar { grid-template-columns:1fr auto; }
        .fs-topnav { display:none; }
        .fs-topbar-right { grid-column:2; }
        .fs-metrics { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .fs-grid-3 { grid-template-columns:1fr; }
      }
      @media (max-width: 640px) {
        [data-testid="stMain"] .block-container { padding: .7rem .75rem 2.5rem; }
        .fs-topbar { padding-left:2px; padding-right:2px; }
        .fs-title { font-size:2.35rem; }
        .fs-work-card, .fs-output-card { padding:17px; border-radius:20px; }
        .fs-metrics { grid-template-columns:1fr 1fr; }
        .fs-footer { display:block; }
        .fs-footer span { display:block; margin-bottom:5px; }
      }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_reconciliation_data(use_llm: bool = False) -> tuple[pd.DataFrame, object, object, pd.DataFrame]:
    """Load, normalize and reconcile the active synthetic datasets."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pg_path = DATA_DIR / "pg_transactions.csv"
    bank_path = DATA_DIR / "bank_settlements.csv"
    erp_path = DATA_DIR / "erp_ledger.json"

    if not (pg_path.exists() and bank_path.exists() and erp_path.exists()):
        from src.generator.synthetic_engine import generate_synthetic_financial_datasets
        generate_synthetic_financial_datasets(output_dir=str(DATA_DIR))

    pg_raw = pd.read_csv(pg_path)
    bank_raw = pd.read_csv(bank_path)
    erp_raw = __import__("json").load(erp_path.open("r", encoding="utf-8"))

    pg_norm = normalize_pg_dataset(pg_raw, use_llm=use_llm)
    bank_norm = normalize_bank_dataset(bank_raw, use_llm=use_llm)
    erp_norm = normalize_erp_dataset(erp_raw, use_llm=use_llm)

    engine = DeterministicReconciliationEngine()
    results = engine.reconcile_batch(pg_norm, bank_norm, erp_norm)
    diagnostics = ReconciliationDiagnostics()
    perf, stats, discrepancy_df = diagnostics.compute_metrics(results, 0.0, 0.0)
    return results, perf, stats, discrepancy_df


def render_footer() -> None:
    memory = st.session_state.memory_service
    memory_state = "Hindsight connected" if memory.is_online else "Local memory fallback"
    st.markdown(
        f'<div class="fs-footer"><span>FinSight <strong>AI Finance Controller</strong> · deterministic money math · evidence-first output</span><span>{html.escape(memory_state)} · human approval remains the final decision point</span></div>',
        unsafe_allow_html=True,
    )
