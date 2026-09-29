# FinSight Final Verification

## UI behavior fixed

### Controller
- Manual **Order ID / Payment ID** input is independent from the Quick test case selector.
- The Quick test case selector never overwrites the manual field.
- Manual input takes precedence when both are present; the selected quick case is used only when the manual field is blank.
- Investigation visibly progresses through case resolution, deterministic controller analysis, memory check, and output preparation.

### Evidence
- Top navigation is functional.
- The Evidence surface resolves the normalized Payment Gateway, Bank, and ERP records for the selected case.
- Missing-UTR cases are matched using the unique settlement amount and explicitly labeled as amount-based matching.
- The evidence trace shows PG gross -> fee/GST -> PG net -> Bank credit -> ERP booked amount.
- Raw normalized source records are available in an expandable section.

### Memory
- Top navigation is functional.
- Displays Hindsight connection/fallback status and retained-memory count.
- Recalls similar cases for the selected discrepancy.
- Displays recalled historical experiences and observed patterns after an investigation.
- Records operator outcomes and retains them using the existing memory service.
- Memory remains contextual; it never replaces deterministic financial truth.

## Duplicate case resolution

`ORD-2026-0053` intentionally has two Payment Gateway rows. The resolver now prefers the flagged `DUPLICATE_ENTRY` row, so entering the Order ID cannot accidentally open the clean base row.

## Seeded financial output re-check

| Order | Category | PG Net | Bank Credit | Bank Variance | Fee Leakage |
|---|---|---:|---:|---:|---:|
| ORD-2026-0046 | FEE_MISMATCH | ₹18,820.00 | ₹18,820.00 | ₹0.00 | ₹708.00 |
| ORD-2026-0047 | SETTLEMENT_DELAY | ₹14,646.00 | ₹0.00 | ₹14,646.00 | ₹0.00 |
| ORD-2026-0048 | MISSING_BANK_REF | ₹8,299.40 | ₹8,299.40 | ₹0.00 | ₹0.00 |
| ORD-2026-0049 | ERP_AMOUNT_MISMATCH | ₹9,764.00 | ₹9,764.00 | ₹0.00 | ₹0.00 |
| ORD-2026-0050 | REFUND_UNACCOUNTED | ₹0.00 | ₹0.00 | ₹0.00 | ₹0.00 |
| ORD-2026-0051 | STATUS_MISMATCH | ₹0.00 | ₹13,670.40 | -₹13,670.40 | ₹0.00 |
| ORD-2026-0052 | PARTIAL_HOLD | ₹29,292.00 | ₹26,792.00 | ₹2,500.00 | ₹0.00 |
| ORD-2026-0053 | DUPLICATE_ENTRY | ₹9,275.80 | ₹9,275.80 | ₹0.00 | ₹0.00 |
| ORD-2026-0055 | TIMING_OUT_OF_PERIOD | ₹18,063.40 | ₹18,063.40 | ₹0.00 | ₹0.00 |

`ORD-2026-0054` remains a successful reconciliation after schema normalization; its seeded issue is a normalization-format case rather than a reconciliation discrepancy.

## Automated verification

- `python -m compileall -q .` — passed
- `pytest -q` — **23 passed**
- `python main.py --generate` — passed; regenerated 56 records with 10 seeded error cases
- `python main.py --evaluate` — passed
- Controller smoke test — passed
- Memory retain/recall smoke test — passed

The current execution environment does not have the `streamlit` package installed, so a live browser screenshot test was not run here. The project requirements include `streamlit>=1.36.0` and the UI source compiles successfully.
