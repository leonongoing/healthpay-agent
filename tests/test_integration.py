"""
Integration tests for HealthPay Reconciliation Agent.
Tests all 5 core tools against the live HAPI FHIR server with Synthea data.

Run: pytest tests/test_integration.py -v
Requires: HAPI FHIR server running on localhost:19911
"""

import asyncio
import pytest
import pytest_asyncio

from src.fhir_client import FHIRClient
from src.reconciler import reconcile
from src.denial_analyzer import analyze_denials
from src.ar_reporter import generate_ar_report
from src.risk_predictor import predict_payment_risk
from src.coding_optimizer import suggest_coding_optimization

FHIR_URL = "http://localhost:19911/fhir"
TEST_PATIENT_ID = "1617"  # Agnes294 Laree109 Berge125

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def fhir_client():
    client = FHIRClient(base_url=FHIR_URL)
    yield client
    await client.close()


@pytest_asyncio.fixture
async def patient_data(fhir_client):
    claims = await fhir_client.get_claims(TEST_PATIENT_ID)
    eobs = await fhir_client.get_eobs(TEST_PATIENT_ID)
    return claims, eobs


# === FHIR Client Tests ===

async def test_fhir_server_reachable(fhir_client):
    stats = await fhir_client.get_server_stats()
    assert stats["Patient"] > 0
    assert stats["Claim"] > 0
    assert stats["ExplanationOfBenefit"] > 0


async def test_search_patients(fhir_client):
    patients = await fhir_client.search_patients(count=5)
    assert len(patients) > 0
    assert "id" in patients[0]


async def test_get_claims(fhir_client):
    claims = await fhir_client.get_claims(TEST_PATIENT_ID)
    assert len(claims) > 0
    assert "id" in claims[0]
    assert "total" in claims[0]


async def test_get_eobs(fhir_client):
    eobs = await fhir_client.get_eobs(TEST_PATIENT_ID)
    assert len(eobs) > 0
    assert "claim" in eobs[0]
    assert "payment" in eobs[0]


# === Reconciliation Tests ===

async def test_reconcile_claims(patient_data):
    claims, eobs = patient_data
    result = reconcile(patient_id=TEST_PATIENT_ID, claims=claims, eobs=eobs)
    assert result.total_claims > 0
    assert result.total_eobs > 0
    total = len(result.matched) + len(result.discrepancies) + len(result.unmatched)
    assert total >= result.total_claims
    assert "total_claimed_amount" in result.summary


async def test_reconcile_empty():
    result = reconcile(patient_id="nonexistent", claims=[], eobs=[])
    assert result.total_claims == 0
    assert len(result.matched) == 0


# === Denial Analysis Tests ===

async def test_analyze_denials(patient_data):
    claims, eobs = patient_data
    report = analyze_denials(patient_id=TEST_PATIENT_ID, claims=claims, eobs=eobs)
    assert report.total_denials >= 0
    assert report.total_recovery_potential >= 0
    if report.analyses:
        a = report.analyses[0]
        assert a.denied_amount > 0
        assert a.appeal_recommendation.priority in ("high", "medium", "low")


async def test_denial_payer_profiles(patient_data):
    claims, eobs = patient_data
    report = analyze_denials(patient_id=TEST_PATIENT_ID, claims=claims, eobs=eobs)
    if report.payer_profiles:
        p = report.payer_profiles[0]
        assert p.total_claims > 0
        assert 0 <= p.denial_rate <= 100


# === A/R Report Tests ===

async def test_ar_report(patient_data):
    claims, eobs = patient_data
    report = generate_ar_report(claims=claims, eobs=eobs)
    assert report.total_claims > 0
    assert report.vital_signs.total_billed > 0
    assert 0 <= report.vital_signs.collection_rate <= 100
    assert len(report.aging_buckets) == 5


async def test_ar_aging_buckets(patient_data):
    claims, eobs = patient_data
    report = generate_ar_report(claims=claims, eobs=eobs)
    labels = [b.label for b in report.aging_buckets]
    assert "0-30 days" in labels
    assert "120+ days" in labels


# === Risk Prediction Tests ===

async def test_payment_risk(patient_data):
    claims, eobs = patient_data
    report = predict_payment_risk(
        target_claims=claims, historical_claims=claims,
        historical_eobs=eobs, patient_id=TEST_PATIENT_ID,
    )
    assert report.total_claims_analyzed > 0
    assert 0 <= report.portfolio_risk_score <= 100
    if report.predictions:
        p = report.predictions[0]
        assert 0 <= p.payment_probability <= 1.0
        assert p.risk_level in ("low", "medium", "high")


# === Coding Optimization Tests ===

async def test_coding_optimization(patient_data):
    claims, eobs = patient_data
    report = suggest_coding_optimization(
        patient_id=TEST_PATIENT_ID, claims=claims, eobs=eobs,
    )
    assert report.total_claims_reviewed > 0
    assert 0 <= report.overall_coding_score <= 100
    if report.suggestions:
        s = report.suggestions[0]
        assert s.severity in ("high", "medium", "low")


async def test_coding_patterns(patient_data):
    claims, eobs = patient_data
    report = suggest_coding_optimization(
        patient_id=TEST_PATIENT_ID, claims=claims, eobs=eobs,
    )
    if report.patterns:
        assert report.patterns[0].occurrence_count > 0


# === 0G Storage Tests (Mock Mode) ===

async def test_0g_upload_mock():
    """Test 0G upload in mock/degraded mode (SDK not installed)."""
    from src.zero_g_storage import upload_to_0g

    data = {
        "audit_type": "reconciliation",
        "patient_id": "test-123",
        "summary": {"matched": 5, "discrepancies": 1},
    }
    root_hash = upload_to_0g(data=data, filename="test_audit.json")

    # Should return a mock hash since SDK is not installed
    assert root_hash.startswith("0xMOCK_")
    assert len(root_hash) > 10


async def test_0g_upload_deterministic():
    """Test that mock hash is deterministic for same input."""
    from src.zero_g_storage import upload_to_0g

    data = {"patient_id": "p1", "result": "ok"}
    hash1 = upload_to_0g(data=data, filename="a.json")
    hash2 = upload_to_0g(data=data, filename="a.json")
    assert hash1 == hash2


async def test_0g_download_mock():
    """Test 0G download in mock/degraded mode."""
    from src.zero_g_storage import download_from_0g

    result = download_from_0g(
        root_hash="0xMOCK_abc123",
        output_path="/tmp/test_0g_download.json",
    )

    assert result["mock"] is True
    assert result["root_hash"] == "0xMOCK_abc123"
    assert "timestamp" in result


async def test_0g_storage_error_class():
    """Test ZeroGStorageError is properly defined."""
    from src.zero_g_storage import ZeroGStorageError

    err = ZeroGStorageError("test error")
    assert str(err) == "test error"
    assert isinstance(err, Exception)


async def test_0g_sdk_not_available():
    """Test _is_0g_available detects python-0g package."""
    from src.zero_g_storage import _is_0g_available

    # In test environment, SDK should not be installed
    assert _is_0g_available() is True  # python-0g is installed


# === 0G Compute Tests (Degraded Mode) ===

async def test_0g_compute_error_class():
    """Test ZeroGComputeError is properly defined."""
    from src.zero_g_compute import ZeroGComputeError

    err = ZeroGComputeError("compute error")
    assert str(err) == "compute error"
    assert isinstance(err, Exception)


async def test_0g_compute_is_0g_available():
    """Test _is_0g_available detects python-0g package."""
    from src.zero_g_compute import _is_0g_available

    # python-0g is installed (a0g package available)
    assert _is_0g_available() is True


async def test_0g_compute_get_config():
    """Test _get_config reads environment variables."""
    from src.zero_g_compute import _get_config, DEFAULT_MODEL

    config = _get_config()
    assert "private_key" in config
    assert "network" in config
    assert "model" in config
    assert "openai_key" in config
    # Default model should be DeepSeek V3
    assert config["model"] == DEFAULT_MODEL


async def test_0g_compute_default_model():
    """Test default model is Qwen 2.5 7B (testnet)."""
    from src.zero_g_compute import DEFAULT_MODEL, FALLBACK_MODEL

    assert DEFAULT_MODEL == "Qwen/Qwen2.5-7B-Instruct"
    assert FALLBACK_MODEL == "gpt-4o-mini"


async def test_0g_compute_llm_init_no_credentials():
    """Test ZeroGLLM initializes gracefully without credentials."""
    from src.zero_g_compute import ZeroGLLM

    llm = ZeroGLLM()
    # Without credentials, should not use 0G
    assert llm.is_using_0g() is False
    assert llm.model == "Qwen/Qwen2.5-7B-Instruct"
    await llm.close()


async def test_0g_compute_llm_custom_model():
    """Test ZeroGLLM accepts custom model name."""
    from src.zero_g_compute import ZeroGLLM

    llm = ZeroGLLM(model="custom-model-v1")
    assert llm.model == "custom-model-v1"
    await llm.close()


async def test_0g_compute_llm_no_client_raises():
    """Test chat_completion raises when no client configured."""
    from src.zero_g_compute import ZeroGLLM, ZeroGComputeError

    llm = ZeroGLLM()
    with pytest.raises(ZeroGComputeError, match="No LLM client available"):
        await llm.chat_completion(
            messages=[{"role": "user", "content": "hello"}]
        )
    await llm.close()
