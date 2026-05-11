"""
HIPAA Compliance and Coding Accuracy Checker.

Phase 3 enhancement: Uses Gemma 4 for intelligent compliance analysis.
Checks:
- HIPAA compliance for claim data
- Coding accuracy (CPT/ICD-10 validation)
- Documentation completeness
"""

import logging
import re
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ComplianceLevel(str, Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


class ComplianceIssue(BaseModel):
    category: str  # "hipaa", "coding", "documentation"
    level: ComplianceLevel
    description: str
    recommendation: str
    reference: str = ""  # Regulation or guideline reference


class CodingValidation(BaseModel):
    code: str
    code_type: str  # "CPT", "ICD-10", "HCPCS"
    is_valid: bool
    issue: str = ""
    suggestion: str = ""


class ComplianceReport(BaseModel):
    claim_id: str
    overall_status: ComplianceLevel = ComplianceLevel.COMPLIANT
    issues: list[ComplianceIssue] = Field(default_factory=list)
    coding_validations: list[CodingValidation] = Field(default_factory=list)
    documentation_score: float = 0.0  # 0-100
    hipaa_compliant: bool = True
    recommendations: list[str] = Field(default_factory=list)


# Basic CPT code format validation
CPT_PATTERN = re.compile(r'^\d{5}$')
ICD10_PATTERN = re.compile(r'^[A-Z]\d{2}(\.\d{1,4})?$')
HCPCS_PATTERN = re.compile(r'^[A-V]\d{4}$')


def _validate_code_format(code: str, code_type: str) -> tuple[bool, str]:
    """Validate code format (not clinical accuracy — that's Gemma 4's job)."""
    if code_type == "CPT":
        if CPT_PATTERN.match(code):
            return True, ""
        return False, f"Invalid CPT format: {code} (expected 5 digits)"
    elif code_type == "ICD-10":
        if ICD10_PATTERN.match(code):
            return True, ""
        return False, f"Invalid ICD-10 format: {code} (expected letter + 2 digits + optional decimal)"
    elif code_type == "HCPCS":
        if HCPCS_PATTERN.match(code):
            return True, ""
        return False, f"Invalid HCPCS format: {code} (expected letter + 4 digits)"
    return True, ""


def _check_hipaa_fields(claim: dict) -> list[ComplianceIssue]:
    """Check HIPAA required fields in claim."""
    issues = []
    
    # Check patient reference
    patient = claim.get("patient", {})
    if not patient.get("reference"):
        issues.append(ComplianceIssue(
            category="hipaa",
            level=ComplianceLevel.CRITICAL,
            description="Missing patient reference in claim",
            recommendation="Add patient reference (Patient/{id})",
            reference="45 CFR § 162.1002 - Standard unique health identifier",
        ))
    
    # Check provider reference
    provider = claim.get("provider", {})
    if not provider.get("reference"):
        issues.append(ComplianceIssue(
            category="hipaa",
            level=ComplianceLevel.VIOLATION,
            description="Missing provider reference in claim",
            recommendation="Add provider NPI reference",
            reference="45 CFR § 162.410 - National Provider Identifier",
        ))
    
    # Check claim type
    claim_type = claim.get("type", {})
    if not claim_type.get("coding"):
        issues.append(ComplianceIssue(
            category="hipaa",
            level=ComplianceLevel.WARNING,
            description="Missing claim type coding",
            recommendation="Add claim type (professional/institutional/oral/pharmacy)",
            reference="X12 837 Transaction Set",
        ))
    
    # Check diagnosis codes
    diagnoses = claim.get("diagnosis", [])
    if not diagnoses:
        issues.append(ComplianceIssue(
            category="documentation",
            level=ComplianceLevel.VIOLATION,
            description="No diagnosis codes on claim",
            recommendation="Add at least one ICD-10 diagnosis code",
            reference="CMS ICD-10 Coding Guidelines",
        ))
    
    # Check service items
    items = claim.get("item", [])
    if not items:
        issues.append(ComplianceIssue(
            category="documentation",
            level=ComplianceLevel.CRITICAL,
            description="No service line items on claim",
            recommendation="Add service line items with CPT/HCPCS codes",
            reference="CMS Claims Processing Manual Ch. 12",
        ))
    
    return issues


def _check_documentation_completeness(claim: dict, eob: dict) -> tuple[float, list[ComplianceIssue]]:
    """Score documentation completeness (0-100)."""
    issues = []
    score = 100.0
    
    required_fields = [
        ("patient", 15, "Patient reference"),
        ("provider", 15, "Provider reference"),
        ("type", 10, "Claim type"),
        ("diagnosis", 15, "Diagnosis codes"),
        ("item", 15, "Service line items"),
        ("created", 10, "Claim creation date"),
        ("total", 10, "Claim total amount"),
        ("billablePeriod", 10, "Billable period"),
    ]
    
    for field, weight, label in required_fields:
        value = claim.get(field)
        if not value or (isinstance(value, list) and len(value) == 0):
            score -= weight
            issues.append(ComplianceIssue(
                category="documentation",
                level=ComplianceLevel.WARNING,
                description=f"Missing {label}",
                recommendation=f"Add {label} to claim for complete documentation",
            ))
    
    return max(0, score), issues


def check_compliance(
    claim: dict,
    eob: Optional[dict] = None,
) -> ComplianceReport:
    """
    Run compliance checks on a FHIR Claim resource.
    
    Checks:
    - HIPAA required fields
    - Code format validation (CPT, ICD-10, HCPCS)
    - Documentation completeness scoring
    
    Args:
        claim: FHIR Claim resource
        eob: Optional FHIR ExplanationOfBenefit resource
    
    Returns:
        ComplianceReport with issues and recommendations
    """
    claim_id = claim.get("id", "unknown")
    report = ComplianceReport(claim_id=claim_id)
    
    # 1. HIPAA field checks
    hipaa_issues = _check_hipaa_fields(claim)
    report.issues.extend(hipaa_issues)
    
    # 2. Code format validation
    # Check diagnosis codes
    for diag in claim.get("diagnosis", []):
        for coding in diag.get("diagnosisCodeableConcept", {}).get("coding", []):
            code = coding.get("code", "")
            if code:
                is_valid, issue = _validate_code_format(code, "ICD-10")
                report.coding_validations.append(CodingValidation(
                    code=code,
                    code_type="ICD-10",
                    is_valid=is_valid,
                    issue=issue,
                ))
    
    # Check procedure codes
    for item in claim.get("item", []):
        for coding in item.get("productOrService", {}).get("coding", []):
            code = coding.get("code", "")
            system = coding.get("system", "")
            if code:
                code_type = "CPT"
                if "hcpcs" in system.lower():
                    code_type = "HCPCS"
                is_valid, issue = _validate_code_format(code, code_type)
                report.coding_validations.append(CodingValidation(
                    code=code,
                    code_type=code_type,
                    is_valid=is_valid,
                    issue=issue,
                ))
    
    # 3. Documentation completeness
    doc_score, doc_issues = _check_documentation_completeness(claim, eob or {})
    report.documentation_score = doc_score
    report.issues.extend(doc_issues)
    
    # 4. Determine overall status
    has_critical = any(i.level == ComplianceLevel.CRITICAL for i in report.issues)
    has_violation = any(i.level == ComplianceLevel.VIOLATION for i in report.issues)
    has_warning = any(i.level == ComplianceLevel.WARNING for i in report.issues)
    invalid_codes = any(not v.is_valid for v in report.coding_validations)
    
    if has_critical:
        report.overall_status = ComplianceLevel.CRITICAL
        report.hipaa_compliant = False
    elif has_violation or invalid_codes:
        report.overall_status = ComplianceLevel.VIOLATION
        report.hipaa_compliant = False
    elif has_warning:
        report.overall_status = ComplianceLevel.WARNING
    
    # 5. Generate recommendations
    if not report.hipaa_compliant:
        report.recommendations.append(
            "⚠️ HIPAA compliance issues detected. Address critical and violation-level issues before submission."
        )
    if invalid_codes:
        report.recommendations.append(
            "🔍 Invalid code formats detected. Verify all CPT/ICD-10/HCPCS codes against current code sets."
        )
    if doc_score < 80:
        report.recommendations.append(
            f"📋 Documentation completeness score: {doc_score}%. Add missing fields to improve claim acceptance rate."
        )
    
    return report


# ============================================================================
# Gemma 4 Enhanced Compliance Checking
# ============================================================================

GEMMA4_COMPLIANCE_SYSTEM_PROMPT = """You are a healthcare compliance expert with deep knowledge of:
- HIPAA Privacy and Security Rules (45 CFR Parts 160, 162, 164)
- CMS coding guidelines (CPT, ICD-10-CM, HCPCS Level II)
- Medical necessity documentation requirements
- Claim submission standards (X12 837P/837I)
- Payer-specific compliance requirements

Analyze claims for compliance issues and provide specific, actionable recommendations.
Focus on preventing denials and ensuring regulatory compliance.
"""


def _build_compliance_prompt(claim: dict, base_report: ComplianceReport) -> str:
    """Build Gemma 4 prompt for enhanced compliance analysis."""
    # Summarize existing issues
    existing_issues = "\n".join(
        f"- [{i.level.value}] {i.category}: {i.description}"
        for i in base_report.issues[:10]
    )
    
    # Summarize codes
    codes = "\n".join(
        f"- {v.code_type} {v.code}: {'✅ valid' if v.is_valid else '❌ ' + v.issue}"
        for v in base_report.coding_validations[:10]
    )
    
    return f"""Review this healthcare claim for compliance issues:

**Claim ID:** {base_report.claim_id}
**Documentation Score:** {base_report.documentation_score}%
**HIPAA Compliant:** {base_report.hipaa_compliant}

**Existing Issues Found:**
{existing_issues or "None"}

**Code Validations:**
{codes or "No codes to validate"}

**Raw Claim Data (summary):**
- Type: {claim.get('type', {}).get('coding', [{}])[0].get('code', 'unknown') if claim.get('type', {}).get('coding') else 'unknown'}
- Diagnoses: {len(claim.get('diagnosis', []))}
- Line Items: {len(claim.get('item', []))}
- Total: ${claim.get('total', {}).get('value', 0)}

**Task:**
1. Identify any additional compliance risks not caught by rule-based checks
2. Validate diagnosis-procedure code pairing (medical necessity)
3. Check for common coding errors (upcoding, unbundling, modifier misuse)
4. Assess documentation sufficiency for the services billed
5. Provide specific remediation steps

**Output Format (JSON):**
{{
  "additional_issues": [
    {{"category": "coding", "level": "warning", "description": "...", "recommendation": "..."}}
  ],
  "code_pairing_analysis": "Assessment of diagnosis-procedure alignment",
  "risk_score": 25,
  "remediation_steps": ["Step 1", "Step 2"]
}}
"""


async def check_compliance_enhanced(
    claim: dict,
    eob: Optional[dict] = None,
    use_gemma4: bool = False,
    gemma4_client = None,
) -> ComplianceReport:
    """
    Enhanced compliance check with optional Gemma 4 analysis.
    
    Args:
        claim: FHIR Claim resource
        eob: Optional FHIR ExplanationOfBenefit resource
        use_gemma4: Whether to use Gemma 4 enhancement
        gemma4_client: Gemma4LLM instance
    
    Returns:
        ComplianceReport with optional Gemma 4 enhancements
    """
    import json
    
    # Run base compliance check
    report = check_compliance(claim, eob)
    
    # Enhance with Gemma 4 if requested
    if use_gemma4 and gemma4_client and gemma4_client.is_available():
        prompt = _build_compliance_prompt(claim, report)
        
        try:
            response = await gemma4_client.chat_completion(
                messages=[
                    {"role": "system", "content": GEMMA4_COMPLIANCE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            
            response_text = response.choices[0].message.content
            
            # Parse response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                # Add additional issues
                for issue_data in data.get("additional_issues", []):
                    report.issues.append(ComplianceIssue(
                        category=issue_data.get("category", "other"),
                        level=ComplianceLevel(issue_data.get("level", "warning")),
                        description=issue_data.get("description", ""),
                        recommendation=issue_data.get("recommendation", ""),
                    ))
                
                # Add remediation steps
                for step in data.get("remediation_steps", []):
                    report.recommendations.append(f"🔧 {step}")
                
                # Add code pairing analysis
                if "code_pairing_analysis" in data:
                    report.recommendations.append(
                        f"🏥 Code Pairing: {data['code_pairing_analysis']}"
                    )
                    
        except Exception as e:
            logger.error("Gemma 4 compliance enhancement failed: %s", e)
    
    return report
