"""
AI-Powered Denial Analysis Engine.
Analyzes claim denials, identifies patterns, and generates appeal recommendations.
"""

import logging
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DenialCategory(str, Enum):
    CODING_ERROR = "coding_error"
    MISSING_AUTH = "missing_prior_authorization"
    ELIGIBILITY = "eligibility_issue"
    DUPLICATE = "duplicate_claim"
    TIMELY_FILING = "timely_filing"
    MEDICAL_NECESSITY = "medical_necessity"
    BUNDLING = "bundling_issue"
    COORDINATION = "coordination_of_benefits"
    INCOMPLETE_INFO = "incomplete_information"
    OTHER = "other"


class AppealRecommendation(BaseModel):
    priority: str  # "high", "medium", "low"
    estimated_recovery: float = 0.0
    strategy: str = ""
    key_points: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    deadline_note: str = ""


class DenialAnalysis(BaseModel):
    claim_id: str
    eob_id: str
    denied_amount: float
    denial_category: DenialCategory
    denial_reason: str
    root_cause: str
    appeal_recommendation: AppealRecommendation
    similar_denials_count: int = 0
    payer_denial_rate: Optional[float] = None


class PayerProfile(BaseModel):
    payer_name: str
    payer_id: str
    total_claims: int = 0
    denied_claims: int = 0
    denial_rate: float = 0.0
    avg_payment_days: float = 0.0
    top_denial_reasons: list[dict] = Field(default_factory=list)
    total_denied_amount: float = 0.0
    recovery_potential: float = 0.0


class DenialReport(BaseModel):
    patient_id: str
    total_denials: int = 0
    total_denied_amount: float = 0.0
    total_recovery_potential: float = 0.0
    analyses: list[DenialAnalysis] = Field(default_factory=list)
    payer_profiles: list[PayerProfile] = Field(default_factory=list)
    pattern_insights: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)


# Common denial reason codes (CARC - Claim Adjustment Reason Codes)
CARC_MAPPING = {
    "1": ("DEDUCTIBLE", DenialCategory.ELIGIBILITY, "Deductible amount"),
    "2": ("COINSURANCE", DenialCategory.ELIGIBILITY, "Coinsurance amount"),
    "3": ("COPAY", DenialCategory.ELIGIBILITY, "Co-payment amount"),
    "4": ("BUNDLING", DenialCategory.BUNDLING, "Procedure code inconsistent with modifier"),
    "5": ("BUNDLING", DenialCategory.BUNDLING, "Procedure code inconsistent with place of service"),
    "16": ("MISSING_INFO", DenialCategory.INCOMPLETE_INFO, "Claim lacks information for adjudication"),
    "18": ("DUPLICATE", DenialCategory.DUPLICATE, "Exact duplicate claim"),
    "29": ("TIMELY_FILING", DenialCategory.TIMELY_FILING, "Timely filing limit exceeded"),
    "50": ("MEDICAL_NECESSITY", DenialCategory.MEDICAL_NECESSITY, "Not medically necessary"),
    "96": ("NON_COVERED", DenialCategory.OTHER, "Non-covered charge"),
    "97": ("BUNDLING", DenialCategory.BUNDLING, "Payment included in another service"),
    "197": ("PRIOR_AUTH", DenialCategory.MISSING_AUTH, "Prior authorization absent"),
}


def _classify_denial(eob: dict, claim: dict) -> tuple[DenialCategory, str]:
    """Classify denial based on EOB adjudication data and reason codes."""
    reasons = []

    for item in eob.get("item", []):
        for adj in item.get("adjudication", []):
            reason = adj.get("reason", {})
            for coding in reason.get("coding", []):
                code = coding.get("code", "")
                if code in CARC_MAPPING:
                    _, category, desc = CARC_MAPPING[code]
                    return category, f"CARC {code}: {desc}"
                reasons.append(coding.get("display", code))

    for note in eob.get("processNote", []):
        text = note.get("text", "").lower()
        if "authorization" in text or "precert" in text:
            return DenialCategory.MISSING_AUTH, note.get("text", "Missing authorization")
        if "duplicate" in text:
            return DenialCategory.DUPLICATE, note.get("text", "Duplicate claim")
        if "timely" in text or "filing" in text:
            return DenialCategory.TIMELY_FILING, note.get("text", "Timely filing issue")
        if "medical necessity" in text:
            return DenialCategory.MEDICAL_NECESSITY, note.get("text", "Medical necessity")

    payment = eob.get("payment", {}).get("amount", {}).get("value", 0)
    submitted = _get_submitted_amount(eob)

    if payment == 0 and submitted > 0:
        claim_type = _get_claim_type_code(claim)
        if claim_type == "professional":
            return DenialCategory.CODING_ERROR, "Full denial on professional claim - likely coding or eligibility issue"
        elif claim_type == "institutional":
            return DenialCategory.MISSING_AUTH, "Full denial on institutional claim - likely authorization issue"

    if reasons:
        return DenialCategory.OTHER, "; ".join(reasons)

    return DenialCategory.OTHER, "Denial reason not specified in EOB data"


def _get_submitted_amount(eob: dict) -> float:
    for total in eob.get("total", []):
        for coding in total.get("category", {}).get("coding", []):
            if coding.get("code") == "submitted":
                return float(total.get("amount", {}).get("value", 0))
    return 0.0


def _get_claim_type_code(resource: dict) -> str:
    for coding in resource.get("type", {}).get("coding", []):
        return coding.get("code", "unknown")
    return "unknown"


def _get_payer_ref(eob: dict) -> tuple[str, str]:
    """Extract payer reference and name from EOB."""
    for ins in eob.get("insurance", []):
        coverage = ins.get("coverage", {})
        ref = coverage.get("reference", "")
        display = coverage.get("display", ref)
        return ref, display
    insurer = eob.get("insurer", {})
    return insurer.get("reference", "unknown"), insurer.get("display", "Unknown Payer")


def _generate_appeal_strategy(category: DenialCategory, denied_amount: float,
                               claim: dict, eob: dict) -> AppealRecommendation:
    """Generate appeal recommendation based on denial category."""
    strategies = {
        DenialCategory.CODING_ERROR: AppealRecommendation(
            priority="high",
            estimated_recovery=denied_amount * 0.75,
            strategy="Correct coding and resubmit with documentation",
            key_points=[
                "Review CPT/ICD-10 codes for accuracy",
                "Verify modifier usage matches procedure documentation",
                "Cross-reference with payer-specific coding guidelines",
            ],
            supporting_evidence=[
                "Original clinical documentation",
                "Corrected CMS-1500 or UB-04 form",
                "Coding reference materials",
            ],
            deadline_note="Most payers allow 90-180 days for corrected claims",
        ),
        DenialCategory.MISSING_AUTH: AppealRecommendation(
            priority="high",
            estimated_recovery=denied_amount * 0.60,
            strategy="Obtain retroactive authorization or demonstrate emergency exception",
            key_points=[
                "Request retroactive authorization from payer",
                "Document medical necessity and urgency",
                "Cite emergency exception clauses if applicable",
            ],
            supporting_evidence=[
                "Clinical notes demonstrating urgency",
                "Physician letter of medical necessity",
                "Payer authorization policy documentation",
            ],
            deadline_note="Retroactive auth requests typically must be filed within 30 days",
        ),
        DenialCategory.ELIGIBILITY: AppealRecommendation(
            priority="medium",
            estimated_recovery=denied_amount * 0.40,
            strategy="Verify patient eligibility and coordination of benefits",
            key_points=[
                "Confirm patient coverage was active on date of service",
                "Check for secondary insurance",
                "Verify correct subscriber information",
            ],
            supporting_evidence=[
                "Insurance card copy",
                "Eligibility verification records",
                "Patient registration documents",
            ],
            deadline_note="Re-verify eligibility before resubmission",
        ),
        DenialCategory.MEDICAL_NECESSITY: AppealRecommendation(
            priority="high",
            estimated_recovery=denied_amount * 0.55,
            strategy="Submit peer-to-peer review request with clinical evidence",
            key_points=[
                "Request peer-to-peer review with payer medical director",
                "Provide comprehensive clinical documentation",
                "Reference clinical guidelines supporting the service",
            ],
            supporting_evidence=[
                "Clinical notes and test results",
                "Published clinical guidelines",
                "Peer-reviewed literature supporting treatment",
            ],
            deadline_note="Peer-to-peer reviews typically requested within 14 days",
        ),
        DenialCategory.TIMELY_FILING: AppealRecommendation(
            priority="low",
            estimated_recovery=denied_amount * 0.15,
            strategy="Document proof of timely submission or request exception",
            key_points=[
                "Gather proof of original submission",
                "Document system issues that caused delay",
                "Request exception based on extenuating circumstances",
            ],
            supporting_evidence=[
                "Clearinghouse transmission reports",
                "System downtime documentation",
            ],
            deadline_note="Timely filing appeals have strict deadlines - act immediately",
        ),
        DenialCategory.DUPLICATE: AppealRecommendation(
            priority="low",
            estimated_recovery=denied_amount * 0.20,
            strategy="Review for true duplicate vs legitimate separate service",
            key_points=[
                "Compare dates of service and procedure codes",
                "Document distinct services if not a true duplicate",
                "Include modifier -59 or -XE if appropriate",
            ],
            supporting_evidence=["Operative notes", "Procedure documentation"],
            deadline_note="Resubmit with corrected claim if services were distinct",
        ),
    }

    return strategies.get(category, AppealRecommendation(
        priority="medium",
        estimated_recovery=denied_amount * 0.30,
        strategy="Review denial details and submit formal appeal with supporting documentation",
        key_points=["Review EOB for specific denial reason", "Gather supporting documentation"],
        supporting_evidence=["Clinical documentation", "Payer policy references"],
        deadline_note="Check payer-specific appeal deadlines",
    ))


def analyze_denials(
    patient_id: str,
    claims: list[dict],
    eobs: list[dict],
) -> DenialReport:
    """
    Analyze claim denials for a patient.
    Identifies denial patterns, classifies root causes, generates appeal recommendations.
    """
    report = DenialReport(patient_id=patient_id)
    claims_by_id = {c.get("id", ""): c for c in claims}
    payer_stats: dict[str, dict] = {}

    for eob in eobs:
        eob_id = eob.get("id", "")
        payment = eob.get("payment", {}).get("amount", {}).get("value", 0)
        submitted = _get_submitted_amount(eob)
        outcome = eob.get("outcome", "")

        claim_ref = eob.get("claim", {}).get("reference", "")
        claim_id = claim_ref.split("/")[-1] if "/" in claim_ref else claim_ref
        claim = claims_by_id.get(claim_id, {})
        claim_amount = float(claim.get("total", {}).get("value", 0)) if claim else submitted

        payer_ref, payer_name = _get_payer_ref(eob)
        if payer_ref not in payer_stats:
            payer_stats[payer_ref] = {
                "name": payer_name, "total": 0, "denied": 0,
                "denied_amount": 0.0, "reasons": {}
            }
        payer_stats[payer_ref]["total"] += 1

        is_denied = (outcome == "denied") or (payment == 0 and claim_amount > 10)
        if not is_denied:
            continue

        category, reason = _classify_denial(eob, claim)
        appeal_rec = _generate_appeal_strategy(category, claim_amount, claim, eob)

        analysis = DenialAnalysis(
            claim_id=claim_id,
            eob_id=eob_id,
            denied_amount=claim_amount,
            denial_category=category,
            denial_reason=reason,
            root_cause=f"{category.value}: {reason}",
            appeal_recommendation=appeal_rec,
        )

        report.analyses.append(analysis)
        report.total_denials += 1
        report.total_denied_amount += claim_amount
        report.total_recovery_potential += appeal_rec.estimated_recovery

        payer_stats[payer_ref]["denied"] += 1
        payer_stats[payer_ref]["denied_amount"] += claim_amount
        cat_key = category.value
        payer_stats[payer_ref]["reasons"][cat_key] = \
            payer_stats[payer_ref]["reasons"].get(cat_key, 0) + 1

    # Build payer profiles
    for payer_ref, stats in payer_stats.items():
        if stats["total"] == 0:
            continue
        top_reasons = sorted(stats["reasons"].items(), key=lambda x: x[1], reverse=True)[:5]
        profile = PayerProfile(
            payer_name=stats["name"],
            payer_id=payer_ref,
            total_claims=stats["total"],
            denied_claims=stats["denied"],
            denial_rate=round(stats["denied"] / stats["total"] * 100, 1),
            top_denial_reasons=[{"reason": r, "count": c} for r, c in top_reasons],
            total_denied_amount=round(stats["denied_amount"], 2),
            recovery_potential=round(stats["denied_amount"] * 0.45, 2),
        )
        report.payer_profiles.append(profile)

    # Generate pattern insights
    if report.total_denials > 0:
        cat_counts = {}
        for a in report.analyses:
            cat_counts[a.denial_category.value] = cat_counts.get(a.denial_category.value, 0) + 1

        top_cat = max(cat_counts, key=cat_counts.get) if cat_counts else "unknown"
        report.pattern_insights.append(
            f"Most common denial category: {top_cat} ({cat_counts.get(top_cat, 0)} occurrences)"
        )

        high_priority = [a for a in report.analyses if a.appeal_recommendation.priority == "high"]
        if high_priority:
            total_high = sum(a.appeal_recommendation.estimated_recovery for a in high_priority)
            report.pattern_insights.append(
                f"{len(high_priority)} high-priority appeals with ${total_high:,.2f} estimated recovery"
            )

            report.action_items.append(
                f"Appeal {len(high_priority)} high-priority denials first (${total_high:,.2f} potential recovery)"
            )
        if cat_counts.get("coding_error", 0) > 2:
            report.action_items.append("Review coding practices - multiple coding-related denials detected")
        if cat_counts.get("missing_prior_authorization", 0) > 2:
            report.action_items.append("Implement prior authorization tracking workflow")

    return report


# ============================================================================
# Phase 3: Gemma 4 Enhanced Denial Analysis
# ============================================================================

GEMMA4_DENIAL_SYSTEM_PROMPT = """You are a medical billing expert with deep knowledge of:
- Healthcare claim denial patterns and root causes
- CPT, ICD-10, and HCPCS coding standards
- Payer-specific policies and appeal procedures
- Medical necessity documentation requirements
- HIPAA compliance and healthcare regulations

Your task is to analyze claim denials and provide actionable appeal strategies.
Focus on evidence-based recommendations that maximize recovery potential.
"""


def _build_medical_context(claim: dict, eob: dict) -> dict:
    """Extract medical context from FHIR resources for Gemma 4 analysis."""
    context = {
        "claim_type": _get_claim_type_code(claim),
        "diagnosis_codes": [],
        "procedure_codes": [],
        "service_date": claim.get("billablePeriod", {}).get("start", ""),
        "provider": claim.get("provider", {}).get("display", ""),
        "payer": eob.get("insurer", {}).get("display", ""),
        "denial_codes": [],
        "process_notes": [],
    }
    
    # Extract diagnosis codes
    for diag in claim.get("diagnosis", []):
        for coding in diag.get("diagnosisCodeableConcept", {}).get("coding", []):
            context["diagnosis_codes"].append({
                "code": coding.get("code", ""),
                "display": coding.get("display", ""),
            })
    
    # Extract procedure codes
    for item in claim.get("item", []):
        for coding in item.get("productOrService", {}).get("coding", []):
            context["procedure_codes"].append({
                "code": coding.get("code", ""),
                "display": coding.get("display", ""),
            })
    
    # Extract denial codes and notes
    for item in eob.get("item", []):
        for adj in item.get("adjudication", []):
            reason = adj.get("reason", {})
            for coding in reason.get("coding", []):
                context["denial_codes"].append({
                    "code": coding.get("code", ""),
                    "display": coding.get("display", ""),
                })
    
    for note in eob.get("processNote", []):
        context["process_notes"].append(note.get("text", ""))
    
    return context


def _build_denial_analysis_prompt(analysis: DenialAnalysis, context: dict) -> str:
    """Build Gemma 4 prompt for enhanced denial analysis."""
    return f"""Analyze this healthcare claim denial and provide enhanced appeal strategy:

**Claim Information:**
- Claim ID: {analysis.claim_id}
- Denied Amount: ${analysis.denied_amount:,.2f}
- Service Date: {context['service_date']}
- Claim Type: {context['claim_type']}
- Provider: {context['provider']}
- Payer: {context['payer']}

**Diagnosis Codes:**
{chr(10).join(f"- {d['code']}: {d['display']}" for d in context['diagnosis_codes'][:5])}

**Procedure Codes:**
{chr(10).join(f"- {p['code']}: {p['display']}" for p in context['procedure_codes'][:5])}

**Denial Information:**
- Category: {analysis.denial_category.value}
- Reason: {analysis.denial_reason}
- Denial Codes: {', '.join(d['code'] for d in context['denial_codes'])}
- Process Notes: {'; '.join(context['process_notes'][:3])}

**Current Appeal Strategy:**
- Priority: {analysis.appeal_recommendation.priority}
- Strategy: {analysis.appeal_recommendation.strategy}

**Task:**
1. Provide deeper root cause analysis using medical billing expertise
2. Identify specific documentation gaps or coding errors
3. Generate 3-5 specific, actionable appeal points
4. Suggest evidence to gather (clinical notes, policies, etc.)
5. Estimate realistic recovery probability (0-100%)

**Output Format (JSON):**
{{
  "root_cause_analysis": "Detailed explanation of why this claim was denied",
  "appeal_points": ["Point 1", "Point 2", "Point 3"],
  "evidence_needed": ["Evidence 1", "Evidence 2"],
  "recovery_probability": 75,
  "appeal_letter_draft": "Professional appeal letter text (2-3 paragraphs)"
}}
"""


def _parse_gemma4_denial_response(analysis: DenialAnalysis, response_text: str) -> DenialAnalysis:
    """Parse Gemma 4 response and enhance DenialAnalysis."""
    import json
    import re
    
    # Try to extract JSON from response
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if not json_match:
        logger.warning("No JSON found in Gemma 4 response")
        return analysis
    
    try:
        data = json.loads(json_match.group())
        
        # Enhance root cause
        if "root_cause_analysis" in data:
            analysis.root_cause = data["root_cause_analysis"]
        
        # Enhance appeal points
        if "appeal_points" in data:
            analysis.appeal_recommendation.key_points = data["appeal_points"]
        
        # Enhance evidence
        if "evidence_needed" in data:
            analysis.appeal_recommendation.supporting_evidence = data["evidence_needed"]
        
        # Update recovery estimate
        if "recovery_probability" in data:
            prob = float(data["recovery_probability"]) / 100.0
            analysis.appeal_recommendation.estimated_recovery = analysis.denied_amount * prob
        
        # Store appeal letter draft (add to strategy)
        if "appeal_letter_draft" in data:
            analysis.appeal_recommendation.strategy += f"\n\n**Draft Appeal Letter:**\n{data['appeal_letter_draft']}"
        
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemma 4 JSON: %s", e)
    
    return analysis


async def enhance_denial_with_gemma4(
    analysis: DenialAnalysis,
    claim: dict,
    eob: dict,
    gemma4_client = None,
) -> DenialAnalysis:
    """
    Enhance denial analysis using Gemma 4's medical domain knowledge.
    
    Adds:
    - Deeper root cause analysis using medical reasoning
    - Personalized appeal letter generation
    - Evidence-based recommendations
    
    Args:
        analysis: Base denial analysis from rule engine
        claim: FHIR Claim resource
        eob: FHIR ExplanationOfBenefit resource
        gemma4_client: Gemma4LLM instance (optional)
    
    Returns:
        Enhanced DenialAnalysis with Gemma 4 insights
    """
    if not gemma4_client or not gemma4_client.is_available():
        logger.warning("Gemma 4 not available, returning base analysis")
        return analysis
    
    # Build medical context from FHIR resources
    context = _build_medical_context(claim, eob)
    
    # Generate enhanced analysis using Gemma 4
    prompt = _build_denial_analysis_prompt(analysis, context)
    
    try:
        response = await gemma4_client.chat_completion(
            messages=[
                {"role": "system", "content": GEMMA4_DENIAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        
        enhanced_text = response.choices[0].message.content
        
        # Parse Gemma 4 response and enhance analysis
        analysis = _parse_gemma4_denial_response(analysis, enhanced_text)
        
    except Exception as e:
        logger.error("Gemma 4 enhancement failed: %s", e)
    
    return analysis


async def analyze_denials_enhanced(
    patient_id: str,
    claims: list[dict],
    eobs: list[dict],
    use_gemma4: bool = False,
    gemma4_client = None,
) -> DenialReport:
    """
    Enhanced denial analysis with optional Gemma 4 integration.
    
    Args:
        patient_id: Patient identifier
        claims: List of FHIR Claim resources
        eobs: List of FHIR ExplanationOfBenefit resources
        use_gemma4: Whether to use Gemma 4 enhancement
        gemma4_client: Gemma4LLM instance (required if use_gemma4=True)
    
    Returns:
        DenialReport with optional Gemma 4 enhancements
    """
    # Run base analysis
    report = analyze_denials(patient_id, claims, eobs)
    
    # Enhance with Gemma 4 if requested
    if use_gemma4 and gemma4_client:
        claims_by_id = {c.get("id", ""): c for c in claims}
        eobs_by_claim = {}
        for eob in eobs:
            ref = eob.get("claim", {}).get("reference", "")
            claim_id = ref.split("/")[-1] if "/" in ref else ref
            eobs_by_claim[claim_id] = eob
        
        # Enhance each denial analysis
        enhanced_analyses = []
        for analysis in report.analyses:
            claim = claims_by_id.get(analysis.claim_id, {})
            eob = eobs_by_claim.get(analysis.claim_id, {})
            
            if claim and eob:
                enhanced = await enhance_denial_with_gemma4(
                    analysis, claim, eob, gemma4_client
                )
                enhanced_analyses.append(enhanced)
            else:
                enhanced_analyses.append(analysis)
        
        report.analyses = enhanced_analyses
    
    return report
