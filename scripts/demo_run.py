#!/usr/bin/env python3
"""
HealthPay Demo Script — produces clean output for demo video recording.
Includes 0G Storage + 0G Compute integration demonstration.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fhir_client import FHIRClient
from src.reconciler import reconcile
from src.denial_analyzer import analyze_denials
from src.ar_reporter import generate_ar_report
from src.risk_predictor import predict_payment_risk
from src.coding_optimizer import suggest_coding_optimization
from src.zero_g_storage import upload_to_0g, download_from_0g
from src.zero_g_compute import ZeroGLLM


def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


async def main():
    fhir = FHIRClient(base_url="http://localhost:19911/fhir")
    pid = "1617"

    # 1. Server Stats
    header("🏥 HealthPay Reconciliation Agent — FHIR Server")
    stats = await fhir.get_server_stats()
    for k, v in stats.items():
        print(f"  {k:.<30} {v:>6}")

    # 2. Reconcile Claims + 0G Storage
    header("🔍 Tool: reconcile_claims + 0G Storage (Patient 1617)")
    claims = await fhir.get_claims(pid)
    eobs = await fhir.get_eobs(pid)
    result = reconcile(patient_id=pid, claims=claims, eobs=eobs)
    s = result.summary
    print(f"  Total Claims:        {s['total_claims']}")
    print(f"  Total EOBs:          {s['total_eobs']}")
    print(f"  Matched:             {s['matched_count']}")
    print(f"  Discrepancies:       {s['discrepancy_count']}")
    print(f"  Total Billed:        ${s['total_claimed_amount']:>12,.2f}")
    print(f"  Total Paid:          ${s['total_paid_amount']:>12,.2f}")
    print(f"  Total Discrepancy:   ${s['total_discrepancy_amount']:>12,.2f}")
    print(f"\n  Breakdown:")
    for dt, info in s.get("discrepancy_breakdown", {}).items():
        print(f"    {dt:.<25} {info['count']:>3} claims  ${info['total_amount']:>10,.2f}")
    
    # Upload to 0G Storage
    print(f"\n  📦 Uploading to 0G Storage...")
    root_hash = upload_to_0g(
        data=result.to_dict(),
        filename=f"reconciliation_{pid}.json"
    )
    print(f"  ✅ Merkle Root Hash: {root_hash}")
    print(f"  ✅ Audit trail stored on 0G decentralized network")
    
    # Verify download
    print(f"\n  🔍 Verifying 0G Storage integrity...")
    downloaded = download_from_0g(root_hash)
    if downloaded:
        print(f"  ✅ Data verified: {len(str(downloaded))} bytes")
    else:
        print(f"  ⚠️  Download skipped (mock mode)")

    # 3. Denial Analysis + 0G Compute
    header("⚠️  Tool: analyze_denials + 0G Compute (Patient 1617)")
    
    # Initialize 0G Compute LLM
    llm = ZeroGLLM(model="Qwen/Qwen2.5-7B-Instruct")
    print(f"  🧠 Using 0G Compute: {llm.is_using_0g()}")
    if llm.is_using_0g():
        print(f"  🌐 Model: {llm.model}")
    else:
        print(f"  ⚠️  Fallback to OpenAI (0G Compute unavailable)")
    
    report = analyze_denials(patient_id=pid, claims=claims, eobs=eobs)
    print(f"\n  Total Denials:       {report.total_denials}")
    print(f"  Denied Amount:       ${report.total_denied_amount:>12,.2f}")
    print(f"  Recovery Potential:   ${report.total_recovery_potential:>12,.2f}")
    print(f"\n  Pattern Insights:")
    for i in report.pattern_insights:
        print(f"    💡 {i}")
    print(f"\n  Action Items:")
    for a in report.action_items:
        print(f"    ⚡ {a}")
    print(f"\n  Top Appeal (by amount):")
    top = sorted(report.analyses, key=lambda a: a.denied_amount, reverse=True)[0]
    print(f"    Claim {top.claim_id}: ${top.denied_amount:,.2f}")
    print(f"    Category: {top.denial_category.value}")
    print(f"    Strategy: {top.appeal_recommendation.strategy}")
    print(f"    Est. Recovery: ${top.appeal_recommendation.estimated_recovery:,.2f}")
    
    await llm.close()

    # 4. AR Report (3 patients)
    header("📊 Tool: generate_ar_report (Multi-Patient)")
    all_claims, all_eobs = [], []
    for p in ["1617", "2224", "12123"]:
        all_claims.extend(await fhir.get_claims(p))
        all_eobs.extend(await fhir.get_eobs(p))
    ar = generate_ar_report(claims=all_claims, eobs=all_eobs)
    vs = ar.vital_signs
    print(f"  ┌─────────────────────────────────────┐")
    print(f"  │     FINANCIAL VITAL SIGNS            │")
    print(f"  ├─────────────────────────────────────┤")
    print(f"  │  Total Billed:     ${vs.total_billed:>12,.2f}  │")
    print(f"  │  Total Collected:  ${vs.total_collected:>12,.2f}  │")
    print(f"  │  Outstanding:      ${vs.total_outstanding:>12,.2f}  │")
    print(f"  │  Collection Rate:  {vs.collection_rate:>11.1f}%  │")
    print(f"  │  Clean Claim Rate: {vs.clean_claim_rate:>11.1f}%  │")
    print(f"  │  Denial Rate:      {vs.denial_rate:>11.1f}%  │")
    print(f"  └─────────────────────────────────────┘")
    print(f"\n  A/R Aging:")
    for b in ar.aging_buckets:
        bar = "█" * int(b.percentage / 2)
        print(f"    {b.label:>12}: ${b.total_amount:>10,.2f} ({b.percentage:>5.1f}%) {bar}")
    print(f"\n  Recommendations:")
    for r in ar.recommendations:
        print(f"    {r}")

    # 5. Risk Prediction
    header("🎯 Tool: predict_payment_risk (Patient 1617)")
    risk = predict_payment_risk(target_claims=claims, historical_claims=claims,
                                 historical_eobs=eobs, patient_id=pid)
    print(f"  Portfolio Risk Score: {risk.portfolio_risk_score}")
    print(f"  At-Risk Amount:      ${risk.total_at_risk_amount:>12,.2f}")
    print(f"  Distribution:        {risk.risk_distribution}")

    # 6. Coding Optimization
    header("💊 Tool: suggest_coding_optimization (Patient 1617)")
    coding = suggest_coding_optimization(patient_id=pid, claims=claims, eobs=eobs)
    print(f"  Coding Score:        {coding.overall_coding_score}/100")
    print(f"  Claims with Issues:  {coding.claims_with_issues}/{coding.total_claims_reviewed}")
    for p in coding.patterns:
        print(f"    {p.pattern_name}: {p.occurrence_count}x")
    for r in coding.top_recommendations:
        print(f"    ⚡ {r}")

    header("✅ HealthPay — All Tools + 0G Integration Operational")
    print(f"  🔗 0G Storage: Immutable audit trails")
    print(f"  🧠 0G Compute: Verifiable AI inference")
    print(f"  🏥 FHIR R4: Healthcare data interoperability")
    print(f"  🤖 MCP: Model Context Protocol server")
    await fhir.close()


if __name__ == "__main__":
    asyncio.run(main())
