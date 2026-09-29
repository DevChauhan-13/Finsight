# 💳 FinSight — AI Financial Reconciliation Agent
### *A Multi-Source Financial Reconciliation Controller That Learns From Every Exception*
**Built for the Hindsight Hackathon — Track: AI Agents That Learn Using Hindsight**

---

## 📌 Executive Summary

Modern finance and operations teams routinely spend days at month-end closing accounts, repeatedly re-investigating the same reconciliation exceptions: payment gateway fee overcharges, settlement delays, missing bank reference UTRs, and unreversed refunds. 

**FinSight** transforms financial operations by combining:
1. **Zero-Tolerance Deterministic 3-Way Reconciliation Engine:** Strictly calculates mathematical truth (gross, fees, GST, variances) across Payment Gateways (PG), Bank Settlement Statements, and ERP Ledgers without hallucination.
2. **Hindsight Persistent Operational Memory:** Automatically recalls how past discrepancies were resolved, what evidence succeeded with vendors, and retains durable operational experience from every operator resolution.

With FinSight, the system behaves like an experienced financial controller: **it never has to investigate the same exception from scratch twice.**

---

## 🏗️ System Architecture

```text
       DATA SOURCES (Payment Gateway + Bank Statements + ERP Ledgers)
                                    ↓
                         SCHEMA NORMALIZATION LAYER
                    (Pydantic Models + Gemini / Rule Parser)
                                    ↓
                   DETERMINISTIC RECONCILIATION ENGINE
                   (3-Way Primary Key Match & Math Verification)
                                    ↓
                          FLAGGED DISCREPANCY
                                    ↓
                     FINANCIAL RECONCILIATION AGENT
                    ↙                             ↘
         HINDSIGHT RECALL                CURRENT DETERMINISTIC FACTS
        (TEMPR Multi-Strategy)           (Gross, Fee, Variance, UTR)
                    ↘                             ↙
                   HISTORICAL CONTEXT & LEARNED PATTERNS
                                    ↓
                       AGENT CONTEXTUAL DECISION
                      (Evidence-Backed Remediation)
                                    ↓
                        HUMAN OPERATOR OUTCOME
                   (Resolve, Dispute, Journal Entry)
                                    ↓
                         HINDSIGHT RETAIN LOOP
                    (Persists Case Resolution Memory)
                                    ↓
                        FUTURE LEARNING ACCELERATION
```

---

## 🧠 Why FinSight Needs Hindsight

Traditional Retrieval-Augmented Generation (RAG) retrieves static text chunks. It fails in financial operations because RAG does not possess **operational state** or **episodic learning**:
- It doesn't know that Razorpay has a recurring corporate credit card billing tier bug.
- It doesn't know that submitting *Master Merchant Agreement Schedule B* + *Settlement Batch ID* gets approved within 24 hours.
- It doesn't learn when a human operator discovers a new vendor dispute channel.

### Hindsight Core Operations in FinSight:
* **`retain`**: When an operator resolves a case, FinSight persists a structured `CaseMemory` (discrepancy category, variance, resolution attempted, evidence submitted, outcome, turnaround time). Sensitive credentials and card numbers are strictly masked via `sanitize_sensitive_data()`.
* **`recall`**: When a new discrepancy arrives, FinSight builds a targeted semantic query and uses TEMPR to retrieve matching historical exceptions.
* **`reflect`**: When multiple memories exist, Hindsight synthesizes recurring root causes, dispute acceptance rates, and average turnaround times across transactions.

---

## 🔄 The Closed Learning Loop

The central innovation of FinSight is its closed feedback loop:

```text
NEW CASE
   ↓
Deterministic Reconciliation Engine (Flags FEE_MISMATCH, Variance = ₹708.00)
   ↓
Hindsight Recall (Finds past corporate card MDR overcharge cases on Razorpay)
   ↓
Agent Analysis (Identifies proven evidence: Master Merchant Agreement Schedule B)
   ↓
Recommended Resolution (Prepares instant high-priority dispute package)
   ↓
Human Operator Outcome (Confirms dispute approved and refund credited)
   ↓
Hindsight Retain (Persists resolution experience into durable memory bank)
   ↓
Future Cases (Instantly benefit from accelerated turnaround and pre-filled evidence)
```

---

## ⚡ The 10 Deterministic Discrepancy Categories

FinSight deterministically audits 10 critical payment ecosystem failure modes:

| Discrepancy Category | Deterministic Detection Rule | Automated Remediation Action |
| :--- | :--- | :--- |
| `FEE_MISMATCH` | Gateway fee exceeds contracted rate (2% MDR + 18% GST) | Raise billing dispute ticket with Payment Gateway |
| `SETTLEMENT_DELAY` | Cleared in PG but missing in bank settlement statement | Track payout node for T+2 settlement arrival |
| `MISSING_BANK_REF` | Bank settlement narration lacks 12-digit UTR reference | Request electronic bank statement re-query |
| `ERP_AMOUNT_MISMATCH` | ERP invoice booking differs from PG checkout gross amount | Audit checkout coupon code / discount variance |
| `REFUND_UNACCOUNTED` | Payment refunded in PG/Bank but ERP retains revenue | Post debit/credit memo journal reversal in ERP |
| `STATUS_MISMATCH` | PG transaction FAILED but bank statement shows credit | Flag uncaptured bank credit to finance ops |
| `PARTIAL_HOLD` | Bank credit short by ₹2,500 due to rolling reserve | Log reserve hold in clearing suspense account |
| `DUPLICATE_ENTRY` | Identical Order ID submitted twice in PG settlement log | Void duplicate PG entry; audit webhook retries |
| `HETEROGENEOUS_SCHEMA` | Unit mismatch (`1600000 paise` vs `₹16,000.00`) | Resolved seamlessly by Schema Normalizer |
| `TIMING_OUT_OF_PERIOD` | ERP posting date booked in incorrect fiscal period | Re-classify posting date to current fiscal month |

---

## 🎬 Before/After Hindsight Learning Demo

FinSight includes a reproducible terminal demo demonstrating the exact behavioral change between cold memory and warm Hindsight memory:

```bash
python main.py --demo-memory
```

### The 4-Phase Demo Sequence:
1. **Phase A (Cold Memory):** First encounter of `FEE_MISMATCH`. Memory bank is empty. FinSight states `Memory Used: NO` and provides safe baseline advice.
2. **Phase B (Teach the System):** Controller resolves cases and persists durable operational outcomes to Hindsight (`client.retain()`).
3. **Phase C (Warm Memory):** A brand new similar case arrives. FinSight retrieves past experiences (`Memory Used: YES`), identifies recurring gateway billing bugs, and recommends the exact proven dispute package.
4. **Phase D (Comparison Matrix):** Renders a comparative contrast table demonstrating that memory transformed generic advice into an instant evidence package.

---

## 📊 Empirical Evaluation Harness

Run the evaluation benchmark measuring cold vs warm memory performance:

```bash
python main.py --evaluate
```

### Measured Benchmark Signals:
* **Memory-Influenced Decisions:** Increases from **0.0%** (cold) to **100.0%** (warm).
* **Evidence Augmentation Rate:** Increases from **0.0%** to **100.0%** (proven documents surfaced).
* **Confidence Score:** Increases from **80%** to **96%**.
* **Estimated Operator Time Saved:** **45 minutes** saved per batch of exceptions.

---

## 🎨 Premium UI Redesign

The Streamlit experience now uses a shared FinSight design system inspired by the supplied visual reference: warm-white surfaces, deep teal navigation, restrained gold accents, rounded cards, soft shadows, consistent metrics, and the same visual language across Overview, AI Controller, Reconciliation, Memory, Analytics, Learning Center, System Health, and Architecture. See `UI_REDESIGN.md` for the detailed UI map.

## 🖥️ Streamlit Web Dashboard

Launch the interactive controller UI:

```bash
streamlit run src/dashboard/web_app.py
```
*(Or run `python main.py --launch-ui`)*

### Dashboard Features:
* **Executive KPIs:** Match Rate, Reconciled Volume, Fee Leakage, Throughput, Learned Memories Count.
* **FinSight AI & Hindsight Controller Tab:**
  - Select any flagged discrepancy to see deterministic math findings side-by-side with recalled Hindsight memories.
  - View learned patterns, proven evidence, and agent recommendations.
  - Interactive **Outcome Recording Form**: Mark cases resolved and submit operator notes to trigger real-time Hindsight retention!
* **Memory Timeline Tab:** Chronological history of resolved vendor exceptions showing how memory evolves over time.
* **Live Interactive Demo:** Run the 4-phase before/after demonstration right inside the web interface.

---

## 🚀 Quickstart & Setup

### 1. Installation
```bash
git clone https://github.com/your-org/razorpay.git
cd razorpay
pip install -r requirements.txt
```

### 2. Environment Configuration (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Supported variables:
* `HINDSIGHT_API_URL` (Default: `http://localhost:8888`)
* `HINDSIGHT_API_KEY` (Optional)
* `HINDSIGHT_BANK_ID` (Default: `finsight-finance-reconciliation`)
* `GEMINI_API_KEY` (Optional - for Gemini schema normalization)

*(Note: FinSight features full local memory and rule-based fallbacks. It runs 100% offline out-of-the-box without requiring external server dependencies!)*

### 3. Run Reconciliation Pipeline
```bash
python main.py --generate --agent
```

### 4. Run Test Suite
```bash
python -m pytest -v
```

---

## 🛡️ Financial Invariants & Safety Guarantees

1. **Deterministic Calculations are Authoritative:** Transaction amounts, fees, GST, bank credits, and variances are calculated strictly by the Python deterministic engine. Large Language Models and Hindsight **never** calculate or alter financial totals.
2. **Credential & PII Redaction:** Credit card numbers and authentication secrets are automatically masked before reaching memory banks.
3. **Graceful Degradation:** If Hindsight is offline or unconfigured, the financial reconciliation engine and diagnostics continue operating with zero disruption.

## Interactive controller UI

The Streamlit application is now a single-screen investigation console.

Run from the project root (the folder containing `main.py`):

```bash
pip install -r requirements.txt
python main.py --generate
python main.py --launch-ui
```

Then open the local Streamlit address shown by the command, usually `http://localhost:8501`.

Enter an existing Order ID or Payment ID from the generated dataset, for example `ORD-2026-0046`.

## Interactive UI

Controller / Evidence / Memory are functional application surfaces.
