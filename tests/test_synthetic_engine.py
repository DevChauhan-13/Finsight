import os
import json
import pandas as pd
import pytest
from src.generator.synthetic_engine import generate_synthetic_financial_datasets

def test_synthetic_data_generation(tmp_path):
    output_dir = str(tmp_path / "data")
    res = generate_synthetic_financial_datasets(output_dir=output_dir, num_clean_records=45, seed=42)
    
    assert os.path.exists(res["pg_path"])
    assert os.path.exists(res["bank_path"])
    assert os.path.exists(res["erp_path"])
    assert os.path.exists(res["meta_path"])

    pg_df = pd.read_csv(res["pg_path"])
    bank_df = pd.read_csv(res["bank_path"])
    with open(res["erp_path"], "r") as f:
        erp_data = json.load(f)

    # 45 clean records + 10 seeded error cases (some with duplicates) >= 55 records
    assert len(pg_df) >= 55
    assert len(bank_df) >= 50
    assert len(erp_data["entries"]) >= 55

    with open(res["meta_path"], "r") as f:
        seeded_errors = json.load(f)
    assert len(seeded_errors) == 10
