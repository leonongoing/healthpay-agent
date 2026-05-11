"""
Accounts Receivable (A/R) Report Generator.
Generates financial vital signs for healthcare organizations.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgingBucket(BaseModel):
    label: str
    count: int = 0
    total_amount: float = 0.0
    percentage: float = 0.0


class PayerSummary(BaseModel):
    payer_name: str
    payer_id: str
    total_claims: int = 0
    total_billed: float = 0.0
    total_paid: float = 0.0
    total_outstanding: float = 0.0
    denial_count: int = 0
    denial_rate: float = 0.0
    avg_days_to_pay: float = 0.0


class FinancialVitalSigns(BaseModel):
    """Key financial health indicators — like clinical vital signs but for revenue."""
    total_billed: float = 0.0
    total_collected: float = 0.0
    total_outstanding: float = 0.0
    collection_rate: float = 0.0
    clean_claim_rate: float = 0.0
    denial_rate: float = 0.0
    avg_days_in_ar: float = 0.0
    net_collection_rate: float = 0.0


class ARReport(BaseModel):
    report_date: str
    date_range: Optional[str] = None
    total_patients: int = 0
    total_claims: int = 0
    vital_signs: FinancialVitalSigns = Field(default_factory=FinancialVitalSigns)
    aging_buckets: list[AgingBucket] = Field(default_factory=list)
    payer_summary: list[PayerSummary] = Field(default_factory=list)
    top_outstanding: list[dict] = Field(default_factory=list)
    trends: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return None


def _get_payer_info(eob: dict) -> tuple[str, str]:
    for ins in eob.get("insurance", []):
        cov = ins.get("coverage", {})
        return cov.get("reference", "unknown"), cov.get("display", "Unknown")
    ins = eob.get("insurer", {})
    return ins.get("reference", "unknown"), ins.get("display", "Unknown")


def generate_ar_report(
    claims: list[dict],
    eobs: list[dict],
    report_date: Optional[str] = None,
) -> ARReport:
    """Generate A/R report from FHIR Claims and EOBs across all patients."""
    now = datetime.now()
    report = ARReport(report_date=report_date or now.strftime("%Y-%m-%d"))

    # Build EOB lookup by claim reference
    eob_by_claim: dict[str, dict] = {}
    for eob in eobs:
        ref = eob.get("claim", {}).get("reference", "")
        claim_id = ref.split("/")[-1] if "/" in ref else ref
        eob_by_claim[claim_id] = eob

    # Track aging
    aging_ranges = [
        ("0-30 days", 0, 30),
        ("31-60 days", 31, 60),
        ("61-90 days", 61, 90),
        ("91-120 days", 91, 120),
        ("120+ days", 121, 99999),
    ]
    aging_data = {label: {"count": 0, "amount": 0.0} for label, _, _ in aging_ranges}

    # Track payers
    payer_data: dict[str, dict] = {}
    patient_ids = set()
    total_billed = 0.0
    total_collected = 0.0
    total_denied = 0
    total_clean = 0
    days_in_ar_sum = 0.0
    days_in_ar_count = 0
    outstanding_items = []

    report.total_claims = len(claims)

    for claim in claims:
        claim_id = claim.get("id", "")
        claim_amount = float(claim.get("total", {}).get("value", 0))
        claim_date = _parse_date(claim.get("created") or claim.get("billablePeriod", {}).get("start"))
        patient_ref = claim.get("patient", {}).get("reference", "")
        patient_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
        patient_ids.add(patient_id)

        total_billed += claim_amount

        eob = eob_by_claim.get(claim_id)
        paid_amount = 0.0
        is_denied = False

        if eob:
            paid_amount = float(eob.get("payment", {}).get("amount", {}).get("value", 0))
            outcome = eob.get("outcome", "")
            is_denied = (outcome == "denied") or (paid_amount == 0 and claim_amount > 10)

            if not is_denied and paid_amount > 0:
                total_clean += 1

            # Payer tracking
            payer_ref, payer_name = _get_payer_info(eob)
            if payer_ref not in payer_data:
                payer_data[payer_ref] = {
                    "name": payer_name, "claims": 0, "billed": 0.0,
                    "paid": 0.0, "denied": 0, "days_sum": 0.0, "days_count": 0
                }
            payer_data[payer_ref]["claims"] += 1
            payer_data[payer_ref]["billed"] += claim_amount
            payer_data[payer_ref]["paid"] += paid_amount
            if is_denied:
                payer_data[payer_ref]["denied"] += 1

            # Days in A/R
            eob_date = _parse_date(eob.get("created"))
            if claim_date and eob_date:
                days = (eob_date - claim_date).days
                if days >= 0:
                    payer_data[payer_ref]["days_sum"] += days
                    payer_data[payer_ref]["days_count"] += 1
                    days_in_ar_sum += days
                    days_in_ar_count += 1

        total_collected += paid_amount
        if is_denied:
            total_denied += 1

        # Aging calculation
        outstanding = claim_amount - paid_amount
        if outstanding > 0.01 and claim_date:
            age_days = (now - claim_date).days
            for label, min_d, max_d in aging_ranges:
                if min_d <= age_days <= max_d:
                    aging_data[label]["count"] += 1
                    aging_data[label]["amount"] += outstanding
                    break

            outstanding_items.append({
                "claim_id": claim_id,
                "patient_id": patient_id,
                "amount": round(outstanding, 2),
                "age_days": age_days,
                "claim_date": claim_date.strftime("%Y-%m-%d") if claim_date else None,
            })

    # Build report
    report.total_patients = len(patient_ids)
    total_outstanding = total_billed - total_collected

    report.vital_signs = FinancialVitalSigns(
        total_billed=round(total_billed, 2),
        total_collected=round(total_collected, 2),
        total_outstanding=round(total_outstanding, 2),
        collection_rate=round(total_collected / max(total_billed, 1) * 100, 1),
        clean_claim_rate=round(total_clean / max(len(claims), 1) * 100, 1),
        denial_rate=round(total_denied / max(len(claims), 1) * 100, 1),
        avg_days_in_ar=round(days_in_ar_sum / max(days_in_ar_count, 1), 1),
        net_collection_rate=round(
            total_collected / max(total_billed - (total_denied * total_billed / max(len(claims), 1)), 1) * 100, 1
        ),
    )

    # Aging buckets
    total_aging = sum(b["amount"] for b in aging_data.values())
    for label, _, _ in aging_ranges:
        d = aging_data[label]
        report.aging_buckets.append(AgingBucket(
            label=label,
            count=d["count"],
            total_amount=round(d["amount"], 2),
            percentage=round(d["amount"] / max(total_aging, 1) * 100, 1),
        ))

    # Payer summary
    for payer_ref, pd in sorted(payer_data.items(), key=lambda x: x[1]["billed"], reverse=True):
        avg_days = pd["days_sum"] / max(pd["days_count"], 1)
        report.payer_summary.append(PayerSummary(
            payer_name=pd["name"],
            payer_id=payer_ref,
            total_claims=pd["claims"],
            total_billed=round(pd["billed"], 2),
            total_paid=round(pd["paid"], 2),
            total_outstanding=round(pd["billed"] - pd["paid"], 2),
            denial_count=pd["denied"],
            denial_rate=round(pd["denied"] / max(pd["claims"], 1) * 100, 1),
            avg_days_to_pay=round(avg_days, 1),
        ))

    # Top outstanding
    report.top_outstanding = sorted(outstanding_items, key=lambda x: x["amount"], reverse=True)[:10]

    # Recommendations
    vs = report.vital_signs
    if vs.denial_rate > 10:
        report.recommendations.append(
            f"⚠️ Denial rate ({vs.denial_rate}%) exceeds 10% benchmark. Review denial patterns and implement preventive measures."
        )
    if vs.avg_days_in_ar > 45:
        report.recommendations.append(
            f"⚠️ Average days in A/R ({vs.avg_days_in_ar}) exceeds 45-day benchmark. Accelerate follow-up on aging claims."
        )
    if vs.clean_claim_rate < 90:
        report.recommendations.append(
            f"⚠️ Clean claim rate ({vs.clean_claim_rate}%) below 90% target. Invest in front-end eligibility verification."
        )
    if vs.collection_rate < 95:
        report.recommendations.append(
            f"💰 Collection rate ({vs.collection_rate}%) below 95% target. Focus on high-value outstanding claims."
        )

    # Aging alerts
    over_90 = aging_data["91-120 days"]["amount"] + aging_data["120+ days"]["amount"]
    if over_90 > 0:
        report.recommendations.append(
            f"🔴 ${over_90:,.2f} in claims aged 90+ days. Prioritize these for immediate follow-up or write-off review."
        )

    return report


# ============================================================================
# Phase 3: Gemma 4 Enhanced A/R Reporting
# ============================================================================

GEMMA4_AR_SYSTEM_PROMPT = """You are a healthcare financial analyst with expertise in:
- Revenue cycle management and A/R optimization
- Healthcare financial metrics and KPIs
- Trend analysis and forecasting
- Data visualization best practices
- Actionable insights generation

Your task is to analyze A/R data and provide strategic recommendations
to improve cash flow, reduce days in A/R, and optimize collections.
"""


def _build_ar_analysis_prompt(report: ARReport) -> str:
    """Build Gemma 4 prompt for enhanced A/R analysis."""
    vs = report.vital_signs
    
    # Build aging summary
    aging_summary = "\n".join(
        f"- {b.label}: ${b.total_amount:,.2f} ({b.percentage}%)"
        for b in report.aging_buckets
    )
    
    # Build payer summary
    payer_summary = "\n".join(
        f"- {p.payer_name}: {p.total_claims} claims, ${p.total_outstanding:,.2f} outstanding, "
        f"{p.denial_rate}% denial rate, {p.avg_days_to_pay} days avg"
        for p in report.payer_summary[:5]
    )
    
    return f"""Analyze this healthcare A/R report and provide strategic insights:

**Financial Vital Signs:**
- Total Billed: ${vs.total_billed:,.2f}
- Total Collected: ${vs.total_collected:,.2f}
- Total Outstanding: ${vs.total_outstanding:,.2f}
- Collection Rate: {vs.collection_rate}%
- Clean Claim Rate: {vs.clean_claim_rate}%
- Denial Rate: {vs.denial_rate}%
- Avg Days in A/R: {vs.avg_days_in_ar}
- Net Collection Rate: {vs.net_collection_rate}%

**Aging Buckets:**
{aging_summary}

**Top Payers:**
{payer_summary}

**Current Recommendations:**
{chr(10).join(f"- {r}" for r in report.recommendations)}

**Task:**
1. Identify 3-5 key trends (improving/declining metrics)
2. Compare against industry benchmarks (provide context)
3. Suggest 2-3 visualization types to track these metrics
4. Generate 3-5 actionable insights with specific next steps
5. Estimate potential revenue impact of recommendations

**Output Format (JSON):**
{{
  "trend_analysis": [
    {{"metric": "collection_rate", "trend": "declining", "change": "-2.3%", "insight": "..."}},
    ...
  ],
  "benchmark_comparison": [
    {{"metric": "days_in_ar", "current": 45, "benchmark": 35, "gap": "+10 days", "impact": "..."}},
    ...
  ],
  "visualization_recommendations": [
    {{"chart_type": "line", "metrics": ["collection_rate", "denial_rate"], "purpose": "..."}},
    ...
  ],
  "actionable_insights": [
    {{"priority": "high", "action": "...", "expected_impact": "$50K", "timeline": "30 days"}},
    ...
  ],
  "executive_summary": "2-3 sentence summary for leadership"
}}
"""


def _parse_gemma4_ar_response(report: ARReport, response_text: str) -> ARReport:
    """Parse Gemma 4 response and enhance ARReport."""
    import json
    import re
    
    # Try to extract JSON from response
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if not json_match:
        logger.warning("No JSON found in Gemma 4 response")
        return report
    
    try:
        data = json.loads(json_match.group())
        
        # Add trend analysis to trends list
        if "trend_analysis" in data:
            for trend in data["trend_analysis"]:
                report.trends.append(
                    f"{trend.get('metric', 'Unknown')}: {trend.get('trend', 'stable')} "
                    f"({trend.get('change', 'N/A')}) - {trend.get('insight', '')}"
                )
        
        # Add benchmark comparisons to trends
        if "benchmark_comparison" in data:
            for bench in data["benchmark_comparison"]:
                report.trends.append(
                    f"Benchmark: {bench.get('metric', 'Unknown')} is {bench.get('gap', 'N/A')} "
                    f"vs industry standard - {bench.get('impact', '')}"
                )
        
        # Add visualization recommendations
        if "visualization_recommendations" in data:
            for viz in data["visualization_recommendations"]:
                report.recommendations.append(
                    f"📊 Visualization: {viz.get('chart_type', 'chart')} chart for "
                    f"{', '.join(viz.get('metrics', []))} - {viz.get('purpose', '')}"
                )
        
        # Add actionable insights
        if "actionable_insights" in data:
            for insight in data["actionable_insights"]:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    insight.get("priority", "medium"), "⚪"
                )
                report.recommendations.append(
                    f"{priority_emoji} {insight.get('action', 'Action')} - "
                    f"Expected impact: {insight.get('expected_impact', 'TBD')} "
                    f"(Timeline: {insight.get('timeline', 'TBD')})"
                )
        
        # Add executive summary to trends
        if "executive_summary" in data:
            report.trends.insert(0, f"📋 Executive Summary: {data['executive_summary']}")
        
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemma 4 JSON: %s", e)
    
    return report


async def enhance_ar_with_gemma4(
    report: ARReport,
    gemma4_client = None,
) -> ARReport:
    """
    Enhance A/R report using Gemma 4's financial analysis capabilities.
    
    Adds:
    - Trend analysis (YoY, MoM comparisons)
    - Benchmark comparisons
    - Visualization recommendations
    - Actionable insights with impact estimates
    
    Args:
        report: Base A/R report
        gemma4_client: Gemma4LLM instance (optional)
    
    Returns:
        Enhanced ARReport with Gemma 4 insights
    """
    if not gemma4_client or not gemma4_client.is_available():
        logger.warning("Gemma 4 not available, returning base report")
        return report
    
    # Generate enhanced analysis using Gemma 4
    prompt = _build_ar_analysis_prompt(report)
    
    try:
        response = await gemma4_client.chat_completion(
            messages=[
                {"role": "system", "content": GEMMA4_AR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        
        enhanced_text = response.choices[0].message.content
        
        # Parse Gemma 4 response and enhance report
        report = _parse_gemma4_ar_response(report, enhanced_text)
        
    except Exception as e:
        logger.error("Gemma 4 enhancement failed: %s", e)
    
    return report


async def generate_ar_report_enhanced(
    claims: list[dict],
    eobs: list[dict],
    report_date: Optional[str] = None,
    use_gemma4: bool = False,
    gemma4_client = None,
) -> ARReport:
    """
    Enhanced A/R report generation with optional Gemma 4 integration.
    
    Args:
        claims: List of FHIR Claim resources
        eobs: List of FHIR ExplanationOfBenefit resources
        report_date: Report date (default: today)
        use_gemma4: Whether to use Gemma 4 enhancement
        gemma4_client: Gemma4LLM instance (required if use_gemma4=True)
    
    Returns:
        ARReport with optional Gemma 4 enhancements
    """
    # Run base report generation
    report = generate_ar_report(claims, eobs, report_date)
    
    # Enhance with Gemma 4 if requested
    if use_gemma4 and gemma4_client:
        report = await enhance_ar_with_gemma4(report, gemma4_client)
    
    return report
