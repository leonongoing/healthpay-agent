"""
Tests for Phase 3 enhanced MCP tools with Gemma 4 integration.

Tests cover:
- Enhanced denial_analyzer with Gemma 4 medical reasoning
- Enhanced ar_reporter with trend analysis
- New compliance_checker tool
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest


# Sample test data
SAMPLE_CLAIM = {
    "id": "claim-001",
    "resourceType": "Claim",
    "status": "active",
    "type": {
        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "professional"}]
    },
    "patient": {"reference": "Patient/patient-001"},
    "provider": {"reference": "Practitioner/provider-001", "display": "Dr. Smith"},
    "created": "2026-03-15",
    "billablePeriod": {"start": "2026-03-15", "end": "2026-03-15"},
    "diagnosis": [
        {
            "sequence": 1,
            "diagnosisCodeableConcept": {
                "coding": [
                    {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11.9", "display": "Type 2 diabetes"}
                ]
            },
        }
    ],
    "item": [
        {
            "sequence": 1,
            "productOrService": {
                "coding": [
                    {"system": "http://www.ama-assn.org/go/cpt", "code": "99213", "display": "Office visit"}
                ]
            },
            "unitPrice": {"value": 150.0, "currency": "USD"},
        }
    ],
    "total": {"value": 150.0, "currency": "USD"},
}

SAMPLE_EOB = {
    "id": "eob-001",
    "resourceType": "ExplanationOfBenefit",
    "status": "active",
    "type": {
        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "professional"}]
    },
    "outcome": "denied",
    "patient": {"reference": "Patient/patient-001"},
    "claim": {"reference": "Claim/claim-001"},
    "insurer": {"reference": "Organization/payer-001", "display": "Blue Cross"},
    "payment": {"amount": {"value": 0.0, "currency": "USD"}},
    "processNote": [
        {"text": "Prior authorization required but not obtained"}
    ],
    "item": [
        {
            "sequence": 1,
            "adjudication": [
                {
                    "category": {"coding": [{"code": "submitted"}]},
                    "amount": {"value": 150.0},
                    "reason": {
                        "coding": [
                            {"code": "197", "display": "Prior authorization absent"}
                        ]
                    },
                }
            ],
        }
    ],
    "total": [
        {
            "category": {"coding": [{"code": "submitted"}]},
            "amount": {"value": 150.0, "currency": "USD"},
        }
    ],
}


def test_denial_analyzer_base():
    """Test base denial analyzer (without Gemma 4)."""
    from denial_analyzer import analyze_denials
    
    report = analyze_denials(
        patient_id="patient-001",
        claims=[SAMPLE_CLAIM],
        eobs=[SAMPLE_EOB],
    )
    
    assert report.patient_id == "patient-001"
    assert report.total_denials == 1
    assert report.total_denied_amount == 150.0
    assert len(report.analyses) == 1
    
    analysis = report.analyses[0]
    assert analysis.claim_id == "claim-001"
    assert analysis.denial_category.value == "missing_prior_authorization"
    assert analysis.appeal_recommendation.priority == "high"
    
    print("✅ Base denial analyzer test passed")


@pytest.mark.asyncio
async def test_denial_analyzer_enhanced():
    """Test enhanced denial analyzer with Gemma 4."""
    from denial_analyzer import analyze_denials_enhanced
    from gemma4_client import Gemma4LLM
    
    # Initialize Gemma 4 client
    gemma4 = Gemma4LLM()
    
    if not gemma4.is_available():
        print("⚠️ Gemma 4 not available, skipping enhanced test")
        return
    
    report = await analyze_denials_enhanced(
        patient_id="patient-001",
        claims=[SAMPLE_CLAIM],
        eobs=[SAMPLE_EOB],
        use_gemma4=True,
        gemma4_client=gemma4,
    )
    
    assert report.patient_id == "patient-001"
    assert report.total_denials == 1
    assert len(report.analyses) == 1
    
    analysis = report.analyses[0]
    # Enhanced analysis should have more detailed root cause
    assert len(analysis.root_cause) > 50
    # Should have appeal points
    assert len(analysis.appeal_recommendation.key_points) >= 3
    
    print("✅ Enhanced denial analyzer test passed")
    print(f"   Root cause: {analysis.root_cause[:100]}...")


def test_ar_reporter_base():
    """Test base A/R reporter (without Gemma 4)."""
    from ar_reporter import generate_ar_report
    
    report = generate_ar_report(
        claims=[SAMPLE_CLAIM],
        eobs=[SAMPLE_EOB],
    )
    
    assert report.total_claims == 1
    assert report.vital_signs.total_billed == 150.0
    assert report.vital_signs.total_collected == 0.0
    assert report.vital_signs.denial_rate == 100.0
    assert len(report.aging_buckets) == 5
    
    print("✅ Base A/R reporter test passed")


@pytest.mark.asyncio
async def test_ar_reporter_enhanced():
    """Test enhanced A/R reporter with Gemma 4."""
    from ar_reporter import generate_ar_report_enhanced
    from gemma4_client import Gemma4LLM
    
    gemma4 = Gemma4LLM()
    
    if not gemma4.is_available():
        print("⚠️ Gemma 4 not available, skipping enhanced test")
        return
    
    report = await generate_ar_report_enhanced(
        claims=[SAMPLE_CLAIM],
        eobs=[SAMPLE_EOB],
        use_gemma4=True,
        gemma4_client=gemma4,
    )
    
    assert report.total_claims == 1
    # Enhanced report should have trends
    assert len(report.trends) > 0
    # Should have more recommendations
    assert len(report.recommendations) > 3
    
    print("✅ Enhanced A/R reporter test passed")
    print(f"   Trends: {len(report.trends)}")
    print(f"   Recommendations: {len(report.recommendations)}")


def test_compliance_checker_base():
    """Test compliance checker (without Gemma 4)."""
    from compliance_checker import check_compliance
    
    report = check_compliance(
        claim=SAMPLE_CLAIM,
        eob=SAMPLE_EOB,
    )
    
    assert report.claim_id == "claim-001"
    assert report.overall_status.value in ["compliant", "warning", "violation", "critical"]
    assert report.documentation_score >= 0
    assert report.documentation_score <= 100
    
    # Should have code validations
    assert len(report.coding_validations) >= 2  # At least 1 ICD-10 + 1 CPT
    
    print("✅ Base compliance checker test passed")
    print(f"   Status: {report.overall_status.value}")
    print(f"   Documentation score: {report.documentation_score}%")
    print(f"   Issues: {len(report.issues)}")


@pytest.mark.asyncio
async def test_compliance_checker_enhanced():
    """Test enhanced compliance checker with Gemma 4."""
    from compliance_checker import check_compliance_enhanced
    from gemma4_client import Gemma4LLM
    
    gemma4 = Gemma4LLM()
    
    if not gemma4.is_available():
        print("⚠️ Gemma 4 not available, skipping enhanced test")
        return
    
    report = await check_compliance_enhanced(
        claim=SAMPLE_CLAIM,
        eob=SAMPLE_EOB,
        use_gemma4=True,
        gemma4_client=gemma4,
    )
    
    assert report.claim_id == "claim-001"
    # Enhanced report should have more recommendations
    assert len(report.recommendations) > 0
    
    print("✅ Enhanced compliance checker test passed")
    print(f"   Recommendations: {len(report.recommendations)}")


def test_invalid_codes():
    """Test compliance checker with invalid codes."""
    from compliance_checker import check_compliance
    
    bad_claim = SAMPLE_CLAIM.copy()
    bad_claim["diagnosis"] = [
        {
            "sequence": 1,
            "diagnosisCodeableConcept": {
                "coding": [
                    {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "INVALID", "display": "Bad code"}
                ]
            },
        }
    ]
    
    report = check_compliance(claim=bad_claim)
    
    # Should detect invalid code
    invalid_codes = [v for v in report.coding_validations if not v.is_valid]
    assert len(invalid_codes) > 0
    assert report.overall_status.value in ["violation", "critical"]
    
    print("✅ Invalid code detection test passed")


if __name__ == "__main__":
    print("Running Phase 3 enhanced tools tests...\n")
    
    # Run sync tests
    test_denial_analyzer_base()
    test_ar_reporter_base()
    test_compliance_checker_base()
    test_invalid_codes()
    
    # Run async tests
    asyncio.run(test_denial_analyzer_enhanced())
    asyncio.run(test_ar_reporter_enhanced())
    asyncio.run(test_compliance_checker_enhanced())
    
    print("\n✅ All tests passed!")
