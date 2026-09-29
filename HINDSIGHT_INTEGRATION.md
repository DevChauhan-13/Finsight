# 🧠 Hindsight Integration Architecture — FinSight

This document specifies the technical design, memory ontology, and behavioral impact of integrating **Hindsight** into **FinSight (Multi-Source Financial Reconciliation Agent)** for the Hindsight Hackathon.

---

## 1. Why does this project need memory?

In high-volume fintech and commerce operations, financial reconciliation teams repeatedly encounter exceptions:
- Payment gateway fee overcharges (e.g. 5% charged on corporate credit cards instead of contracted 2% MDR).
- Settlement delays (T+2 clearing corridors).
- Missing bank narration UTRs.
- ERP revenue reversals for refunded orders.

In traditional finance stacks, every month-end audit starts from scratch:
- A new operator or bot treats every fee discrepancy as an unknown event.
- Teams waste hours re-investigating which vendor agreement applies, what evidence the gateway requires, and which settlement batch ID to quote.
- **The problem:** Traditional RAG merely retrieves static text documents; it does not remember **operational outcomes** (what action was taken, what evidence worked, whether the dispute was accepted, and how long it took).

**FinSight uses Hindsight** to build persistent operational memory. Every time a human controller resolves an exception, FinSight retains the durable experience. Future exceptions automatically inherit that proven operational knowledge.

---

## 2. What does Hindsight store?

FinSight never retains raw transaction noise or unmasked credentials. It stores structured, durable operational knowledge:

### A. Case Experience Memory (`CaseMemory`)
* **Case Reference:** Order ID, Payment ID (sanitized)
* **Parties:** Merchant ID, Gateway Name (e.g. `Razorpay`)
* **Discrepancy Category:** `FEE_MISMATCH`, `SETTLEMENT_DELAY`, `REFUND_UNACCOUNTED`, etc.
* **Deterministic Math:** Gross amount, exact fee variance, root cause
* **Resolution Strategy:** Dispute ticket, ERP journal reversal, bank re-query
* **Proven Evidence Submitted:** Master Merchant Agreement Schedule B, Settlement Batch ID, Bank UTR Credit Record
* **Outcome Status:** `RESOLVED`, `UNSUCCESSFUL`, `ESCALATED`
* **Turnaround Duration:** Resolution time in hours
* **Operator Notes:** Specific operational takeaways

### B. Merchant Profile Memory (`MerchantMemory`)
* Contracted fee schedule (2% MDR, 18% GST)
* Known operational quirks and recurring exceptions
* Preferred dispute documentation

### C. Gateway Operational Memory (`GatewayMemory`)
* Known billing engine bugs (e.g. corporate card MDR tier glitch)
* Settlement SLA corridors (T+2)
* Required dispute fields and escalation channels

### 🛡️ Safety & PII Sanitization
Before any content reaches Hindsight, `sanitize_sensitive_data()` automatically strips:
- Credit card numbers (masked to `CARD-****-****-****-XXXX`)
- API keys, tokens, and passwords (redacted to `[REDACTED_SECRET]`)
- Customer phone numbers

---

## 3. How is memory recalled?

When the deterministic engine flags a discrepancy, FinSight invokes `tools.recall_similar_cases()` using **targeted query builders**:

```python
query = build_recall_query_for_discrepancy(
    discrepancy_type="FEE_MISMATCH",
    gateway="Razorpay",
    merchant_name="Apex Retail",
    failure_cause="Gateway fee charged (₹1,000.00) exceeds contracted fee (₹400.00) at 2% rate",
    net_variance=708.0
)
```

### Multi-Strategy Retrieval (TEMPR)
Hindsight searches across:
1. **Semantic matching:** Conceptual alignment with fee overcharges.
2. **Entity graphs:** Exact merchant and gateway entity nodes.
3. **Structured Tags:** `tags=["discrepancy:fee_mismatch", "gateway:razorpay"]`.
4. **Synthesis via Reflect:** When multiple memories exist, `client.reflect()` aggregates patterns, calculating average turnaround hours and extracting proven evidence packages.

---

## 4. How does memory change agent behavior?

The behavioral difference is explicit and empirically measurable:

| Attribute | WITHOUT MEMORY (Cold Start) | WITH HINDSIGHT (Learned Experience) |
| :--- | :--- | :--- |
| **Memory Status** | `Memory Used: NO` | `Memory Used: YES (2+ cases recalled)` |
| **Diagnosis** | Detects raw math variance | Recognizes recurring gateway corporate-card MDR bug |
| **Recommendation** | Generic advice: *"Raise dispute with gateway"* | Contextual instruction: *"Prepare high-priority dispute citing Master Merchant Agreement Schedule B + Settlement Batch ID"* |
| **Evidence Package** | Standard Payment ID & timestamp | Exact documents previously accepted: Schedule B, Settlement Batch ID, Bank UTR Record |
| **Turnaround Expectation** | Unknown (manual investigation) | Accurately predicts 24h turnaround based on prior dispute outcomes |
| **Confidence** | 80% (baseline rule) | 96% (empirically validated by past success) |

---

## 5. How does the system learn from outcomes?

FinSight implements a closed **Feedback Learning Loop**:

```
[ New Discrepancy Flagged ]
             ↓
[ Deterministic Engine Computes Truth (Gross, Fee, Variance) ]
             ↓
[ FinSight Recalls Similar Past Cases from Hindsight ]
             ↓
[ Agent Formulates Evidence-Backed Recommendation ]
             ↓
[ Human Operator Audits & Executes Operational Action ]
             ↓
[ Operator Submits Outcome in UI / CLI ]
             ↓
[ Hindsight RETAIN: Persists CaseMemory + Outcome + Proven Evidence ]
             ↓
[ Future Exceptions of this Type Instantly Benefit ]
```

When an operator marks a case as `RESOLVED` and notes *"Gateway approved refund when attaching Schedule B"*, that experience is immediately retained into Hindsight (`client.retain()`). The very next transaction with a fee overcharge retrieves that exact resolution!

---

## 6. What is the before/after demonstration?

A fully reproducible terminal demo is available via:
```bash
python main.py --demo-memory
```

It executes in 4 explicit phases:
1. **Phase A (Cold Memory):** Processes `ORD-2026-0046` with an unseeded memory bank. Emits `Memory Used: NO` and generic remediation.
2. **Phase B (Persist Experience):** Records operator resolution and retains the experience into Hindsight.
3. **Phase C (Warm Memory):** Processes a new transaction `ORD-2026-0052` with identical fee anomalies. Retrieves prior cases, recognizes the gateway bug, and prepares the exact evidence package.
4. **Phase D (Comparative Matrix):** Renders a side-by-side Rich comparison table proving memory impact.

---

## 7. Which parts are deterministic?

To prevent hallucination in financial auditing:
- **3-Way Transaction Matching:** Strict primary key joins across `Payment ID`, `Bank UTR`, and `Order ID`.
- **Contract Fee Verification:** Mathematical calculation of contracted 2% MDR and 18% statutory GST.
- **Financial Variances:** `gross - net_payout - bank_credit`.
- **Reconciliation Status:** Categorization into `RECONCILED` or `DISCREPANCY`.
- **Threshold Tolerances:** Configurable ₹0.50 fee tolerance, ₹0.01 amount tolerance.

**Rule:** The AI agent and Hindsight **CANNOT** modify financial totals or override arithmetic facts.

---

## 8. Which parts are agentic?

The AI controller layer (`src/agent/`) is responsible for:
- Translating mathematical discrepancies into targeted memory queries.
- Recalling relevant historical cases from Hindsight.
- Synthesizing recurring root causes across disparate transactions.
- Drafting operational remediation instructions and preparing evidence packages.
- Asking for human authorization on high-variance exceptions (`requires_human_review = True`).
- Capturing human resolution outcomes and formatting durable memory payloads.

---

## 9. What happens when memory is unavailable?

FinSight includes **Graceful Degradation**:
1. **Zero Crash Guarantee:** If the Hindsight server is offline or unreachable, FinSight automatically activates its local memory fallback (`LocalFallbackMemoryStore`).
2. **Deterministic Core Unaffected:** 100% of multi-source 3-way matching and diagnostics execute without interruption.
3. **Transparent Status:** The agent explicitly outputs:
   ```text
   Memory Used: NO
   No prior historical cases found in Hindsight memory for this exception type.
   Defaulting to baseline deterministic financial protocol.
   ```
4. **No Hallucination:** The system never invents fake memories when the memory bank is empty or offline.
