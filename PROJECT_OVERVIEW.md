# 💳 Multi-Source Financial Reconciliation Agent
### *AI Finance Controller — Razorpay Buildathon (Track 04)*

---

## 📌 Executive Summary

The **Multi-Source Financial Reconciliation Agent** is an enterprise-grade automated financial audit system built for modern fintech and commerce operations. In high-volume transactional environments, organizations face significant operational overhead and revenue leakage trying to reconcile data across three distinct financial silos:

1. **Payment Gateways (PG)**: Customer checkout authorizations, transaction fees, and gateway-initiated payouts.
2. **Bank Settlement Statements**: Actual net credits, bank reference numbers (UTRs), rolling reserves, and settlement batches.
3. **Enterprise Resource Planning (ERP) Ledgers**: Internal order invoices, booked revenues, customer accounts, and tax postings.

This project delivers an autonomous, high-throughput, **dual-layer reconciliation system** that bridges unstructured/heterogeneous vendor data into a unified schema, performs zero-tolerance mathematical 3-way matching, flags discrepancies with actionable remediation steps, and presents financial insights via an interactive web dashboard and terminal interface.

---

## 🎯 The Problem It Solves

Modern finance and operations teams routinely spend days at month-end closing accounts due to:
- **Disparate Data Formats**: Currencies in paise vs. rupees, varying timestamp conventions, missing UTR references, or semi-structured JSON records.
- **Hidden Fee Leakages**: Payment gateways inadvertently overcharging transaction rates (e.g., charging 5% instead of a contracted 2% MDR + 18% GST).
- **Timing & Settlement Delays**: Payments cleared in the gateway but delayed in bank clearing corridors (T+2 settlements).
- **Unaccounted Refunds & Chargebacks**: Customer refunds completed in payment gateways without corresponding debit reversals in ERP ledgers.
- **Silent Status Inconsistencies**: Gateway transaction failures that nevertheless result in bank statement credits (unallocated funds).
- **Human Error & High Latency**: Manual spreadsheet lookups that fail to scale beyond hundreds of transactions.

---

## 🏗️ Dual-Layer System Architecture

```
                            +-----------------------------------+
                            |     Synthetic Data Generator      |
                            | (55+ records, 10 seeded errors)   |
                            +-----------------+-----------------+
                                              |
                                              v
                            +-----------------------------------+
                            | Layer 1: Schema Normalizer (LLM)  |
                            | (Pydantic / Structured Parsing)   |
                            +-----------------+-----------------+
                                              |
                                              v
                            +-----------------------------------+
                            | Layer 2: Deterministic Engine     |
                            | (3-Way Arithmetic & Math Rules)   |
                            +-----------------+-----------------+
                                              |
                                              v
                            +-----------------------------------+
                            | Metrics & Exception Diagnostics   |
                            | (Throughput, Match %, Remediation)|
                            +-----------------+-----------------+
                                              |
                              +---------------+---------------+
                              |                               |
                              v                               v
                   +--------------------+           +--------------------+
                   | Rich CLI Dashboard |           | Web Dashboard UI   |
                   +--------------------+           +--------------------+
```

### 1. Layer 1: Hybrid Schema Normalizer (LLM + Deterministic Fallback)
Financial datasets from multiple third-party providers rarely share schemas. This layer converts raw, varied formats into strict Pydantic models:
- **Unit Normalization**: Automatically converts units (e.g., `1600000 paise` $\rightarrow$ `₹16,000.00`).
- **Data Sanitization**: Strips currency symbols (`₹`, `$`, commas), maps string timestamps into standardized ISO datetimes, and standardizes vendor status strings.
- **Dual Mode**: Powered by **Google Gemini API** (`gemini-1.5-flash`) for schema inference, with a built-in zero-latency rule-based fallback that operates offline with 100% precision.

### 2. Layer 2: Deterministic Arithmetic Rule Engine
Large Language Models cannot be trusted with raw financial calculations due to hallucination risks. Our architecture delegates all financial calculations to a strictly deterministic mathematical engine:
- **3-Way Matching**: Links records across `Payment ID`, `Bank UTR`, and `Order ID`.
- **Contract Verification**: Validates contracted merchant fee rates (2% MDR) and applicable statutory taxes (18% GST on fee).
- **Tolerance Bounds**: Applied configurable precision tolerances (₹0.50 fee tolerance, ₹0.01 amount tolerance).
- **Automated Root-Cause Diagnosis & Remediation**: Automatically tags discrepancies and generates immediate next steps for the finance operations team.

---

## 🔍 Seeded Discrepancy Scenarios & Diagnostics

The agent detects and diagnoses 10 critical real-world payment ecosystem exceptions:

| Discrepancy Tag | Root Cause Description | Automated Remediation Action |
| :--- | :--- | :--- |
| `FEE_MISMATCH` | Gateway charged 5% fee instead of contracted 2% rate | Raise billing dispute ticket with Payment Gateway |
| `SETTLEMENT_DELAY` | PG record cleared but missing in current bank statement | Track payout node for T+2 settlement arrival |
| `MISSING_BANK_REF` | Bank settlement narration lacks 12-digit UTR reference | Request electronic bank statement re-query |
| `ERP_AMOUNT_MISMATCH` | ERP invoice booking differs from PG checkout gross amount | Audit checkout coupon code / discount variance |
| `REFUND_UNACCOUNTED` | Payment refunded in PG/Bank but ERP retains revenue | Post debit/credit memo journal reversal in ERP |
| `STATUS_MISMATCH` | PG transaction FAILED but bank statement shows credit | Flag uncaptured bank credit to finance ops |
| `PARTIAL_HOLD` | Bank credit short by ₹2,500 due to rolling reserve | Log reserve hold in clearing suspense account |
| `DUPLICATE_ENTRY` | Identical Order ID submitted twice in PG settlement log | Void duplicate PG entry; audit webhook retries |
| `HETEROGENEOUS_SCHEMA` | Unit mismatch (`1600000 paise` vs `₹16,000.00`) | Resolved seamlessly by Schema Normalizer |
| `TIMING_OUT_OF_PERIOD` | ERP posting date booked in incorrect fiscal period | Re-classify posting date to current fiscal month |

---

## 📊 Performance, Diagnostics & Analytics

The diagnostics module (`src/metrics/diagnostics.py`) continuously computes:
- **Reconciliation Match Rate**: Percentage of transactions with full 3-way alignment.
- **Gross Volume & Payout Metrics**: Total gross transaction volume, bank credits, and net variances.
- **Financial Leakage Metrics**: Overcharged gateway fees, reserve holds, and unaccounted refunds.
- **Processing Performance**:
  - Processing speed exceeding **1,000+ transactions per second** in deterministic mode.
  - End-to-end audit latency logged down to sub-millisecond precision.

---

## 🖥️ User Experience: Web Dashboard & CLI

### 1. Interactive Streamlit Web Dashboard (`src/dashboard/web_app.py`)
- **Executive KPI Cards**: Real-time display of Gross Processed Volume, Match Rate, Discrepancies Count, and Identified Fee Leakage.
- **Interactive Visualizations**:
  - Breakdown of reconciliation statuses (Reconciled vs. Discrepancies).
  - Distribution chart of discrepancy categories.
  - Financial cashflow waterfall (Gross $\rightarrow$ Fees $\rightarrow$ Bank Settlement).
- **Searchable Audit Ledger**: Dynamic filtering by discrepancy type, order ID, or payment status.
- **Export Utility**: One-click download of reconciliation audit reports in CSV format.

### 2. Rich CLI Report (`src/dashboard/cli_view.py`)
- Terminal dashboard using the `rich` library.
- Formatted tables with color-coded status badges, execution metrics, and discrepancy breakdowns.

---

## 🛠️ Technology Stack

| Category | Technology | Usage |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core application runtime |
| **Data Processing** | `pandas`, `numpy` | High-performance tabular transformation and matching |
| **Data Validation** | `pydantic` | Strict type schema validation for normalized data |
| **LLM Integration** | `google-generativeai` (Gemini) | Flexible vendor schema normalization |
| **Web Dashboard** | `streamlit` | Financial controller visual interface |
| **Charting** | `plotly` | Interactive financial distribution and waterfall graphs |
| **CLI Formatting** | `rich` | Terminal tables, panels, and metric displays |
| **Testing** | `pytest` | Unit, integration, and mathematical tolerance tests |

---

## 📂 Project Structure

```
razorpay/
├── data/
│   ├── pg_transactions.csv       # Raw Payment Gateway transaction records
│   ├── bank_settlements.csv      # Raw Bank clearing statement records
│   └── erp_ledger.json           # Raw ERP accounting journal records
├── src/
│   ├── generator/
│   │   └── synthetic_engine.py   # Synthetic data engine (55+ linked records, 10 errors)
│   ├── normalization/
│   │   └── schema_normalizer.py  # Layer 1: Schema normalization (Pydantic / Gemini)
│   ├── reconciliation/
│   │   └── engine.py             # Layer 2: Deterministic 3-way arithmetic rule engine
│   ├── metrics/
│   │   └── diagnostics.py        # Metrics, throughput & discrepancy analytics
│   └── dashboard/
│       ├── cli_view.py           # Rich terminal visual report
│       └── web_app.py            # Streamlit interactive web dashboard
├── tests/
│   ├── test_synthetic_data.py    # Test data generation and seeded errors
│   ├── test_normalizer.py        # Test schema parsing and unit conversions
│   ├── test_reconciliation.py    # Test 3-way matching and arithmetic precision
│   └── test_metrics.py           # Test diagnostic calculations and throughput
├── main.py                       # Unified CLI entry point
├── requirements.txt              # Project dependencies
├── README.md                     # Quickstart documentation
└── PROJECT_OVERVIEW.md           # Comprehensive project description
```

---

## 🚀 How to Run the Project

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run CLI Reconciliation Pipeline
Generates synthetic multi-source data and executes the full reconciliation:
```bash
python main.py --generate
```

### 3. Run with Live LLM Parsing (Optional)
```bash
set GEMINI_API_KEY="your-gemini-api-key"
python main.py --use-llm
```

### 4. Launch Interactive Web Dashboard
```bash
streamlit run src/dashboard/web_app.py
```
*(Or run `python main.py --launch-ui`)*

### 5. Run Test Suite
```bash
pytest tests/ -v
```

---

## 💡 Business Impact & Value Proposition

- **100% Elimination of Manual Matching**: Cuts monthly financial closing cycles from days to seconds.
- **Zero Calculation Error**: By decoupling schema parsing (LLM) from arithmetic verification (Deterministic Engine), the system eliminates hallucination risks.
- **Direct Bottom-Line Protection**: Detects gateway overcharges and fee leakages immediately for billing disputes.
- **Audit-Ready Compliance**: Every flagged record includes an auditable failure cause and concrete operational remediation step.
