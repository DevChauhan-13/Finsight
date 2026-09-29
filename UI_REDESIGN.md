# FinSight UI — Final Interaction Design

The Streamlit application is now a focused premium workflow with three functional surfaces:

- **Controller** — enter an Order ID / Payment ID, visibly watch the finance controller execute, then read the authoritative output.
- **Evidence** — inspect the normalized Payment Gateway, Bank and ERP records that support the result, including the reconciliation trace and raw records.
- **Memory** — inspect Hindsight/local-memory status, recall similar cases, review observed patterns, and record the human operator outcome back into durable memory.

## Input behavior

The manual case input and Quick test case selector are intentionally independent. The selector never writes into the text field. When both are supplied, the manual reference takes precedence; when the manual field is empty, the selected quick case is used.

Duplicate Order IDs are resolved to the flagged discrepancy row, preventing a duplicate case from accidentally opening the clean base row.

## Output behavior

The result separates:

- **Bank variance:** PG net payout minus bank credit.
- **Fee leakage:** gateway fee + GST above the contracted 2% MDR + 18% GST calculation.

For the seeded `ORD-2026-0046` fee case, the authoritative values are: gross ₹20,000; PG net payout ₹18,820; bank credit ₹18,820; bank variance ₹0; fee leakage ₹708.

## Visual system

The design keeps the reference-inspired visual language: deep teal, warm white, restrained gold accents, soft borders, premium cards, generous spacing, compact metadata, and a high-signal status treatment.
