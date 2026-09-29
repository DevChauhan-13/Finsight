import pytest
from src.memory.hindsight_client import FinSightHindsightWrapper, LocalFallbackMemoryStore

def test_hindsight_client_init_and_fallback():
    client = FinSightHindsightWrapper(base_url="http://localhost:9999", bank_id="test-bank")
    assert client.bank_id == "test-bank"
    assert client.local_store is not None

def test_hindsight_client_retain_and_recall():
    client = FinSightHindsightWrapper(bank_id="test-bank")
    client.clear_bank()

    retain_res = client.retain(
        content="Discrepancy FEE_MISMATCH for merchant Apex on Razorpay was resolved with refund credit.",
        tags=["discrepancy:fee_mismatch", "gateway:razorpay"]
    )
    assert retain_res["status"] == "success"

    recalls = client.recall(query="FEE_MISMATCH Razorpay", tags=["discrepancy:fee_mismatch"])
    assert len(recalls) >= 1
    assert "FEE_MISMATCH" in recalls[0]["text"]

def test_hindsight_client_reflect():
    client = FinSightHindsightWrapper(bank_id="test-bank")
    client.clear_bank()

    client.retain("Case 1: Gateway overcharged 5% fee; refund granted after dispute with contract.")
    client.retain("Case 2: Gateway overcharged fee again; resolved using batch ID.")

    reflection = client.reflect("Summarize gateway fee overcharge resolutions")
    assert reflection is not None
    assert len(reflection) > 20

def test_local_store_clear():
    store = LocalFallbackMemoryStore()
    store.retain("bank1", "Some content")
    assert len(store.recall("bank1", "content")) == 1
    store.clear("bank1")
    assert len(store.recall("bank1", "content")) == 0
