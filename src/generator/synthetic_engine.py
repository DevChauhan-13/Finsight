import json
import random
import os
import pandas as pd
from datetime import datetime, timedelta

def generate_synthetic_financial_datasets(
    output_dir: str = "data",
    num_clean_records: int = 45,
    seed: int = 42
):
    """
    Generates 3 parallel financial datasets (pg_transactions.csv, bank_settlements.csv, erp_ledger.json)
    containing 50+ linked records with 10 intentionally seeded realistic error cases.
    """
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    base_time = datetime(2026, 8, 20, 10, 0, 0)

    pg_records = []
    bank_records = []
    erp_records = []

    # Track metadata about seeded errors for benchmark evaluation
    seeded_errors = {}

    payment_methods = ["UPI", "CREDIT_CARD", "NET_BANKING", "DEBIT_CARD"]

    # -------------------------------------------------------------
    # 1. GENERATE CLEAN RECONCILED RECORDS (1 to 45)
    # -------------------------------------------------------------
    for i in range(1, num_clean_records + 1):
        order_id = f"ORD-2026-{i:04d}"
        pay_id = f"pay_RZP_{i:06d}"
        utr = f"UTRBNK{202608200000 + i}"
        
        gross = float(random.choice([1500, 2499, 4999, 7500, 12000, 25000, 50000]))
        fee_rate = 0.02 # 2% contracted fee
        gst_rate = 0.18 # 18% GST on fee
        fee = round(gross * fee_rate, 2)
        gst = round(fee * gst_rate, 2)
        net_payout = round(gross - fee - gst, 2)

        timestamp = base_time + timedelta(minutes=i * 15)
        settle_date = (timestamp + timedelta(days=1)).strftime("%Y-%m-%d")

        # PG record
        pg_records.append({
            "payment_id": pay_id,
            "order_id": order_id,
            "gross_amount": gross,
            "gateway_fee": fee,
            "gst_tax": gst,
            "net_payout": net_payout,
            "currency": "INR",
            "payment_method": random.choice(payment_methods),
            "status": "SUCCESS",
            "created_at": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_email": f"client_{i}@example.com",
            "bank_utr": utr
        })

        # Bank record
        bank_records.append({
            "bank_ref_utr": utr,
            "settlement_date": settle_date,
            "credit_amount": net_payout,
            "debit_amount": 0.0,
            "bank_fee": 0.0,
            "narrative_raw": f"CMS/RAZORPAY/{pay_id}/{utr}/SETTLE",
            "settlement_status": "CREDITED"
        })

        # ERP record
        erp_records.append({
            "journal_entry_id": f"JE-2026-{i:05d}",
            "invoice_reference": f"INV-{i:04d}",
            "order_id": order_id,
            "debit_account": "1100 - Razorpay Clearing Account",
            "credit_account": "4000 - Sales Revenue",
            "booked_amount": gross,
            "posting_date": timestamp.strftime("%Y-%m-%d"),
            "status": "BOOKED",
            "utr_number": utr
        })

    # -------------------------------------------------------------
    # 2. GENERATE INTENTIONAL SEEDED ERROR CASES (10 ERRORS)
    # -------------------------------------------------------------
    
    # --- ERROR 1: Gateway Fee Overcharge (Contracted 2%, charged 5%) ---
    e1_idx = num_clean_records + 1
    ord_e1 = f"ORD-2026-{e1_idx:04d}"
    pay_e1 = f"pay_RZP_{e1_idx:06d}"
    utr_e1 = f"UTRBNK{202608200000 + e1_idx}"
    gross_e1 = 20000.0
    actual_fee = round(gross_e1 * 0.05, 2) # Overcharge!
    actual_gst = round(actual_fee * 0.18, 2)
    wrong_net = round(gross_e1 - actual_fee - actual_gst, 2)
    
    pg_records.append({
        "payment_id": pay_e1, "order_id": ord_e1, "gross_amount": gross_e1,
        "gateway_fee": actual_fee, "gst_tax": actual_gst, "net_payout": wrong_net,
        "currency": "INR", "payment_method": "CREDIT_CARD", "status": "SUCCESS",
        "created_at": (base_time + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err1@example.com", "bank_utr": utr_e1
    })
    bank_records.append({
        "bank_ref_utr": utr_e1, "settlement_date": "2026-08-21",
        "credit_amount": wrong_net, "debit_amount": 0.0, "bank_fee": 0.0,
        "narrative_raw": f"CMS/RAZORPAY/{pay_e1}/{utr_e1}", "settlement_status": "CREDITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e1_idx:05d}", "invoice_reference": f"INV-{e1_idx:04d}",
        "order_id": ord_e1, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_e1,
        "posting_date": "2026-08-20", "status": "BOOKED", "utr_number": utr_e1
    })
    seeded_errors[ord_e1] = "FEE_MISMATCH: Gateway fee charged (5%) exceeds contracted rate (2%)"

    # --- ERROR 2: Bank Settlement Delay (Missing in Bank statement) ---
    e2_idx = num_clean_records + 2
    ord_e2 = f"ORD-2026-{e2_idx:04d}"
    pay_e2 = f"pay_RZP_{e2_idx:06d}"
    gross_e2 = 15000.0
    net_e2 = round(15000.0 * 0.9764, 2)
    pg_records.append({
        "payment_id": pay_e2, "order_id": ord_e2, "gross_amount": gross_e2,
        "gateway_fee": 300.0, "gst_tax": 54.0, "net_payout": net_e2,
        "currency": "INR", "payment_method": "UPI", "status": "SUCCESS",
        "created_at": (base_time + timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err2@example.com", "bank_utr": f"UTRBNK{202608200000 + e2_idx}"
    })
    # Omit from bank_records!
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e2_idx:05d}", "invoice_reference": f"INV-{e2_idx:04d}",
        "order_id": ord_e2, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_e2,
        "posting_date": "2026-08-20", "status": "BOOKED", "utr_number": ""
    })
    seeded_errors[ord_e2] = "SETTLEMENT_DELAY: Transaction recorded in PG & ERP, but un-credited in Bank file"

    # --- ERROR 3: Missing / Truncated Bank Reference ID ---
    e3_idx = num_clean_records + 3
    ord_e3 = f"ORD-2026-{e3_idx:04d}"
    pay_e3 = f"pay_RZP_{e3_idx:06d}"
    gross_e3 = 8500.0
    net_e3 = round(gross_e3 - 170.0 - 30.6, 2)
    pg_records.append({
        "payment_id": pay_e3, "order_id": ord_e3, "gross_amount": gross_e3,
        "gateway_fee": 170.0, "gst_tax": 30.6, "net_payout": net_e3,
        "currency": "INR", "payment_method": "NET_BANKING", "status": "SUCCESS",
        "created_at": (base_time + timedelta(hours=16)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err3@example.com", "bank_utr": f"UTRBNK{202608200000 + e3_idx}"
    })
    bank_records.append({
        "bank_ref_utr": "MISSING_N/A", # Corrupted UTR in Bank statement
        "settlement_date": "2026-08-21", "credit_amount": net_e3, "debit_amount": 0.0,
        "bank_fee": 0.0, "narrative_raw": f"CMS/BULK_PAYOUT_UNKNOWN_REF", "settlement_status": "CREDITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e3_idx:05d}", "invoice_reference": f"INV-{e3_idx:04d}",
        "order_id": ord_e3, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_e3,
        "posting_date": "2026-08-20", "status": "BOOKED", "utr_number": ""
    })
    seeded_errors[ord_e3] = "MISSING_BANK_REF: Bank settlement record lacks valid UTR or reference tie-back"

    # --- ERROR 4: ERP Invoice Amount Mismatch ---
    e4_idx = num_clean_records + 4
    ord_e4 = f"ORD-2026-{e4_idx:04d}"
    pay_e4 = f"pay_RZP_{e4_idx:06d}"
    utr_e4 = f"UTRBNK{202608200000 + e4_idx}"
    gross_pg_e4 = 10000.0 # Customer paid 10,000 on PG
    gross_erp_e4 = 12000.0 # ERP booked 12,000 expecting no coupon discount
    net_e4 = round(10000.0 - 200.0 - 36.0, 2)
    pg_records.append({
        "payment_id": pay_e4, "order_id": ord_e4, "gross_amount": gross_pg_e4,
        "gateway_fee": 200.0, "gst_tax": 36.0, "net_payout": net_e4,
        "currency": "INR", "payment_method": "UPI", "status": "SUCCESS",
        "created_at": (base_time + timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err4@example.com", "bank_utr": utr_e4
    })
    bank_records.append({
        "bank_ref_utr": utr_e4, "settlement_date": "2026-08-21",
        "credit_amount": net_e4, "debit_amount": 0.0, "bank_fee": 0.0,
        "narrative_raw": f"CMS/RAZORPAY/{pay_e4}/{utr_e4}", "settlement_status": "CREDITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e4_idx:05d}", "invoice_reference": f"INV-{e4_idx:04d}",
        "order_id": ord_e4, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_erp_e4, # Mismatch!
        "posting_date": "2026-08-20", "status": "BOOKED", "utr_number": utr_e4
    })
    seeded_errors[ord_e4] = "ERP_AMOUNT_MISMATCH: ERP booked amount (₹12,000) differs from PG gross (₹10,000)"

    # --- ERROR 5: Unaccounted Refund / Chargeback ---
    e5_idx = num_clean_records + 5
    ord_e5 = f"ORD-2026-{e5_idx:04d}"
    pay_e5 = f"pay_RZP_{e5_idx:06d}"
    utr_e5 = f"UTRBNK{202608200000 + e5_idx}"
    gross_e5 = 6000.0
    pg_records.append({
        "payment_id": pay_e5, "order_id": ord_e5, "gross_amount": gross_e5,
        "gateway_fee": 120.0, "gst_tax": 21.6, "net_payout": 0.0, # Refunded net payout 0
        "currency": "INR", "payment_method": "CREDIT_CARD", "status": "REFUNDED",
        "created_at": (base_time + timedelta(hours=20)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err5@example.com", "bank_utr": utr_e5
    })
    bank_records.append({
        "bank_ref_utr": utr_e5, "settlement_date": "2026-08-21",
        "credit_amount": 0.0, "debit_amount": 6000.0, "bank_fee": 0.0, # Bank reversed funds
        "narrative_raw": f"CMS/RAZORPAY/REFUND/{pay_e5}", "settlement_status": "DEBITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e5_idx:05d}", "invoice_reference": f"INV-{e5_idx:04d}",
        "order_id": ord_e5, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_e5, # ERP still booked full revenue!
        "posting_date": "2026-08-20", "status": "BOOKED", "utr_number": utr_e5
    })
    seeded_errors[ord_e5] = "REFUND_UNACCOUNTED: PG & Bank registered refund, but ERP has not posted reversal entry"

    # --- ERROR 6: Status Mismatch (PG FAILED vs Bank Credited) ---
    e6_idx = num_clean_records + 6
    ord_e6 = f"ORD-2026-{e6_idx:04d}"
    pay_e6 = f"pay_RZP_{e6_idx:06d}"
    utr_e6 = f"UTRBNK{202608200000 + e6_idx}"
    gross_e6 = 14000.0
    pg_records.append({
        "payment_id": pay_e6, "order_id": ord_e6, "gross_amount": gross_e6,
        "gateway_fee": 0.0, "gst_tax": 0.0, "net_payout": 0.0,
        "currency": "INR", "payment_method": "UPI", "status": "FAILED", # PG marked failed
        "created_at": (base_time + timedelta(hours=22)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err6@example.com", "bank_utr": utr_e6
    })
    bank_records.append({
        "bank_ref_utr": utr_e6, "settlement_date": "2026-08-21",
        "credit_amount": 13670.4, "debit_amount": 0.0, "bank_fee": 0.0, # Bank erroneously credited!
        "narrative_raw": f"CMS/RAZORPAY/{pay_e6}/{utr_e6}", "settlement_status": "CREDITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e6_idx:05d}", "invoice_reference": f"INV-{e6_idx:04d}",
        "order_id": ord_e6, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": 0.0,
        "posting_date": "2026-08-20", "status": "CANCELLED", "utr_number": utr_e6
    })
    seeded_errors[ord_e6] = "STATUS_MISMATCH: PG transaction FAILED, but bank statement shows funds credited"

    # --- ERROR 7: Partial Split Settlement Holdback ---
    e7_idx = num_clean_records + 7
    ord_e7 = f"ORD-2026-{e7_idx:04d}"
    pay_e7 = f"pay_RZP_{e7_idx:06d}"
    utr_e7 = f"UTRBNK{202608200000 + e7_idx}"
    gross_e7 = 30000.0
    fee_e7 = 600.0
    gst_e7 = 108.0
    net_expected_e7 = 29292.0
    actual_bank_credit_e7 = 26792.0 # 2500 short (rolling reserve holdback)
    pg_records.append({
        "payment_id": pay_e7, "order_id": ord_e7, "gross_amount": gross_e7,
        "gateway_fee": fee_e7, "gst_tax": gst_e7, "net_payout": net_expected_e7,
        "currency": "INR", "payment_method": "CREDIT_CARD", "status": "SUCCESS",
        "created_at": (base_time + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err7@example.com", "bank_utr": utr_e7
    })
    bank_records.append({
        "bank_ref_utr": utr_e7, "settlement_date": "2026-08-21",
        "credit_amount": actual_bank_credit_e7, "debit_amount": 0.0, "bank_fee": 0.0,
        "narrative_raw": f"CMS/RAZORPAY/{pay_e7}/PARTIAL_HOLDBACK", "settlement_status": "CREDITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e7_idx:05d}", "invoice_reference": f"INV-{e7_idx:04d}",
        "order_id": ord_e7, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_e7,
        "posting_date": "2026-08-20", "status": "BOOKED", "utr_number": utr_e7
    })
    seeded_errors[ord_e7] = "PARTIAL_HOLD: Bank credit is short by ₹2,500 due to gateway rolling reserve hold"

    # --- ERROR 8: Duplicate Payment Gateway Record ---
    e8_idx = num_clean_records + 8
    ord_e8 = f"ORD-2026-{e8_idx:04d}"
    pay_e8_a = f"pay_RZP_{e8_idx:06d}_A"
    pay_e8_b = f"pay_RZP_{e8_idx:06d}_B"
    utr_e8 = f"UTRBNK{202608200000 + e8_idx}"
    gross_e8 = 9500.0
    net_e8 = round(9500.0 * 0.9764, 2)
    # Duplicate PG entry 1
    pg_records.append({
        "payment_id": pay_e8_a, "order_id": ord_e8, "gross_amount": gross_e8,
        "gateway_fee": 190.0, "gst_tax": 34.2, "net_payout": net_e8,
        "currency": "INR", "payment_method": "UPI", "status": "SUCCESS",
        "created_at": (base_time + timedelta(hours=26)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err8@example.com", "bank_utr": utr_e8
    })
    # Duplicate PG entry 2 (same Order ID)
    pg_records.append({
        "payment_id": pay_e8_b, "order_id": ord_e8, "gross_amount": gross_e8,
        "gateway_fee": 190.0, "gst_tax": 34.2, "net_payout": net_e8,
        "currency": "INR", "payment_method": "UPI", "status": "SUCCESS",
        "created_at": (base_time + timedelta(hours=26, minutes=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err8@example.com", "bank_utr": utr_e8
    })
    bank_records.append({
        "bank_ref_utr": utr_e8, "settlement_date": "2026-08-21",
        "credit_amount": net_e8, "debit_amount": 0.0, "bank_fee": 0.0,
        "narrative_raw": f"CMS/RAZORPAY/{pay_e8_a}/{utr_e8}", "settlement_status": "CREDITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e8_idx:05d}", "invoice_reference": f"INV-{e8_idx:04d}",
        "order_id": ord_e8, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_e8,
        "posting_date": "2026-08-20", "status": "BOOKED", "utr_number": utr_e8
    })
    seeded_errors[ord_e8] = "DUPLICATE_ENTRY: Multiple PG transactions found for identical Order ID"

    # --- ERROR 9: Unit Mismatch (Paise in PG vs INR Float in ERP & Bank) ---
    e9_idx = num_clean_records + 9
    ord_e9 = f"ORD-2026-{e9_idx:04d}"
    pay_e9 = f"pay_RZP_{e9_idx:06d}"
    utr_e9 = f"UTRBNK{202608200000 + e9_idx}"
    gross_inr_e9 = 16000.0
    net_inr_e9 = round(16000.0 * 0.9764, 2)
    # PG record formatted with paise integer or unnormalized field names
    pg_records.append({
        "payment_id": pay_e9, "order_id": ord_e9,
        "gross_amount": "1600000 paise", # Raw vendor string with paise!
        "gateway_fee": "32000 paise", "gst_tax": "5760 paise",
        "net_payout": f"₹{net_inr_e9}", "currency": "INR",
        "payment_method": "DEBIT_CARD", "status": "SUCCESS",
        "created_at": (base_time + timedelta(hours=28)).strftime("%Y-%m-%d %H:%M:%S"),
        "customer_email": "err9@example.com", "bank_utr": utr_e9
    })
    bank_records.append({
        "bank_ref_utr": utr_e9, "settlement_date": "2026-08-21",
        "credit_amount": net_inr_e9, "debit_amount": 0.0, "bank_fee": 0.0,
        "narrative_raw": f"CMS/RAZORPAY/{pay_e9}/{utr_e9}", "settlement_status": "CREDITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e9_idx:05d}", "invoice_reference": f"INV-{e9_idx:04d}",
        "order_id": ord_e9, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_inr_e9,
        "posting_date": "2026-08-20", "status": "BOOKED", "utr_number": utr_e9
    })
    # Note: LLM/Schema Normalizer handles this unit conversion! If correctly normalized, this record will reconcile successfully.
    seeded_errors[ord_e9] = "HETEROGENEOUS_SCHEMA: Non-standard string format ('1600000 paise') resolved by Schema Normalizer"

    # --- ERROR 10: Out-of-Period Posting Date Mismatch ---
    e10_idx = num_clean_records + 10
    ord_e10 = f"ORD-2026-{e10_idx:04d}"
    pay_e10 = f"pay_RZP_{e10_idx:06d}"
    utr_e10 = f"UTRBNK{202608200000 + e10_idx}"
    gross_e10 = 18500.0
    net_e10 = round(18500.0 * 0.9764, 2)
    pg_records.append({
        "payment_id": pay_e10, "order_id": ord_e10, "gross_amount": gross_e10,
        "gateway_fee": 370.0, "gst_tax": 66.6, "net_payout": net_e10,
        "currency": "INR", "payment_method": "UPI", "status": "SUCCESS",
        "created_at": "2026-08-20 12:00:00",
        "customer_email": "err10@example.com", "bank_utr": utr_e10
    })
    bank_records.append({
        "bank_ref_utr": utr_e10, "settlement_date": "2026-08-21",
        "credit_amount": net_e10, "debit_amount": 0.0, "bank_fee": 0.0,
        "narrative_raw": f"CMS/RAZORPAY/{pay_e10}/{utr_e10}", "settlement_status": "CREDITED"
    })
    erp_records.append({
        "journal_entry_id": f"JE-2026-{e10_idx:05d}", "invoice_reference": f"INV-{e10_idx:04d}",
        "order_id": ord_e10, "debit_account": "1100 - Razorpay Clearing",
        "credit_account": "4000 - Revenue", "booked_amount": gross_e10,
        "posting_date": "2025-08-20", # Booked in 2025 (1 year out of period!)
        "status": "BOOKED", "utr_number": utr_e10
    })
    seeded_errors[ord_e10] = "TIMING_OUT_OF_PERIOD: ERP posting date is out of current fiscal period window"

    # Save to disk
    pg_df = pd.DataFrame(pg_records)
    bank_df = pd.DataFrame(bank_records)

    pg_path = os.path.join(output_dir, "pg_transactions.csv")
    bank_path = os.path.join(output_dir, "bank_settlements.csv")
    erp_path = os.path.join(output_dir, "erp_ledger.json")
    meta_path = os.path.join(output_dir, "seeded_errors_meta.json")

    pg_df.to_csv(pg_path, index=False)
    bank_df.to_csv(bank_path, index=False)
    with open(erp_path, "w") as f:
        json.dump({"entries": erp_records}, f, indent=2)

    with open(meta_path, "w") as f:
        json.dump(seeded_errors, f, indent=2)

    return {
        "pg_path": pg_path,
        "bank_path": bank_path,
        "erp_path": erp_path,
        "meta_path": meta_path,
        "total_pg_records": len(pg_records),
        "total_bank_records": len(bank_records),
        "total_erp_records": len(erp_records),
        "seeded_error_count": len(seeded_errors)
    }

if __name__ == "__main__":
    result = generate_synthetic_financial_datasets()
    print("Synthetic dataset generation complete!")
    print(json.dumps(result, indent=2))
