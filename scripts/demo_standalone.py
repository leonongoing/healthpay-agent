#!/usr/bin/env python3
"""
HealthPay Agent — Standalone Demo Script
No external services required. Uses built-in synthetic FHIR data.
Demonstrates: Reconciliation + 0G Storage + Denial Analysis + 0G Compute + Financial Vitals

Usage:
    python scripts/demo_standalone.py
    python scripts/demo_standalone.py --fast   # skip delays
"""

import sys
import os
import time
import json
import hashlib
import random
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAST = "--fast" in sys.argv

def sleep(s):
    if not FAST:
        time.sleep(s)

def header(title, emoji=""):
    print(f"\n{'═'*62}")
    print(f"  {emoji}  {title}")
    print(f"{'═'*62}\n")

def step(msg):
    print(f"  ▶  {msg}")
    sleep(0.3)

def result(label, value, width=32):
    print(f"  {label:<{width}} {value}")

def ok(msg):
    print(f"  ✅  {msg}")

def warn(msg):
    print(f"  ⚠️   {msg}")

def section(msg):
    print(f"\n  ── {msg} ──")

# ─── Synthetic Data ────────────────────────────────────────────────────────────

PATIENTS = [
    {"id": "P-1001", "name": "Alice Johnson", "dob": "1978-03-15"},
    {"id": "P-1002", "name": "Bob Martinez",  "dob": "1965-07-22"},
    {"id": "P-1003", "name": "Carol Chen",    "dob": "1990-11-08"},
]

CLAIMS = [
    {"id": "CLM-001", "patient": "P-1001", "amount": 1250.00, "date": "2026-03-01", "type": "professional", "codes": ["99213", "J0696"]},
    {"id": "CLM-002", "patient": "P-1001", "amount":  890.50, "date": "2026-03-15", "type": "professional", "codes": ["99214"]},
    {"id": "CLM-003", "patient": "P-1002", "amount": 3400.00, "date": "2026-03-10", "type": "institutional", "codes": ["99285", "71046"]},
    {"id": "CLM-004", "patient": "P-1002", "amount":  560.00, "date": "2026-03-20", "type": "professional", "codes": ["99212", "93000"]},
    {"id": "CLM-005", "patient": "P-1003", "amount": 2100.00, "date": "2026-04-01", "type": "professional", "codes": ["99215", "36415"]},
    {"id": "CLM-006", "patient": "P-1003", "amount":  780.00, "date": "2026-04-05", "type": "professional", "codes": ["99213"]},
    {"id": "CLM-007", "patient": "P-1001", "amount": 4500.00, "date": "2026-04-10", "type": "institutional", "codes": ["99291", "93306"]},
    {"id": "CLM-008", "patient": "P-1002", "amount":  320.00, "date": "2026-04-12", "type": "professional", "codes": ["99211"]},
]

EOBS = [
    {"id": "EOB-001", "claim_ref": "CLM-001", "paid": 1100.00, "status": "partial",  "denial_code": None},
    {"id": "EOB-002", "claim_ref": "CLM-002", "paid":    0.00, "status": "denied",   "denial_code": "CO-4"},
    {"id": "EOB-003", "claim_ref": "CLM-003", "paid": 3400.00, "status": "paid",     "denial_code": None},
    {"id": "EOB-004", "claim_ref": "CLM-004", "paid":  504.00, "status": "partial",  "denial_code": None},
    {"id": "EOB-005", "claim_ref": "CLM-005", "paid":    0.00, "status": "denied",   "denial_code": "CO-11"},
    {"id": "EOB-006", "claim_ref": "CLM-006", "paid":  780.00, "status": "paid",     "denial_code": None},
    # CLM-007 and CLM-008 have no EOB yet (unmatched)
]

DENIAL_DESCRIPTIONS = {
    "CO-4":  "Procedure code inconsistent with modifier used",
    "CO-11": "Diagnosis inconsistent with the procedure",
    "CO-16": "Claim lacks information needed for adjudication",
    "CO-29": "Time limit for filing has expired",
}

# ─── Mock 0G Storage ───────────────────────────────────────────────────────────

def mock_0g_upload(data: dict, label: str) -> str:
    """Simulate 0G Storage upload — returns deterministic content hash."""
    payload = json.dumps(data, sort_keys=True).encode()
    root_hash = "0x" + hashlib.sha256(payload).hexdigest()
    sleep(0.4)
    return root_hash

def mock_0g_verify(root_hash: str) -> bool:
    """Simulate 0G Storage verification."""
    sleep(0.2)
    return True

# ─── Mock 0G Compute ───────────────────────────────────────────────────────────

APPEAL_TEMPLATES = {
    "CO-4":  "Appeal basis: Modifier was medically necessary per clinical documentation. Attach operative report and modifier justification letter.",
    "CO-11": "Appeal basis: Diagnosis directly supports the procedure per ICD-10-CM guidelines. Attach physician attestation and clinical notes.",
    "CO-16": "Appeal basis: Resubmitting with complete documentation including NPI, taxonomy code, and place of service.",
    "CO-29": "Appeal basis: Timely filing exception — claim was submitted within 30 days of receiving corrected patient insurance information.",
}

def mock_0g_compute(denial_code: str, claim_data: dict) -> dict:
    """Simulate 0G Compute verifiable AI inference for appeal strategy."""
    sleep(0.5)
    appeal = APPEAL_TEMPLATES.get(denial_code, "Review claim documentation and resubmit with supporting clinical evidence.")
    inference_hash = "0x" + hashlib.sha256(f"{denial_code}:{claim_data['id']}".encode()).hexdigest()[:16]
    return {
        "appeal_strategy": appeal,
        "confidence": 0.87,
        "inference_hash": inference_hash,
        "model": "DeepSeek-V3 via 0G Compute",
        "verifiable": True,
    }

# ─── Main Demo ─────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█"*62)
    print("█" + " "*18 + "HealthPay Agent" + " "*27 + "█")
    print("█" + " "*8 + "AI Healthcare Payment Reconciliation" + " "*16 + "█")
    print("█" + " "*14 + "Powered by 0G Network" + " "*25 + "█")
    print("█"*62)
    sleep(1)

    # ── Scene 1: Data Overview ──────────────────────────────────────────────────
    header("Scene 1: Healthcare Data Overview", "🏥")
    result("Patients loaded:", str(len(PATIENTS)))
    result("Claims submitted:", str(len(CLAIMS)))
    result("EOBs received:", str(len(EOBS)))
    total_billed = sum(c["amount"] for c in CLAIMS)
    result("Total billed:", f"${total_billed:,.2f}")
    sleep(0.5)

    # ── Scene 2: Reconciliation + 0G Storage ───────────────────────────────────
    header("Scene 2: Claim Reconciliation + 0G Storage", "🔍")
    step("Matching claims against EOBs...")
    sleep(0.6)

    eob_map = {e["claim_ref"]: e for e in EOBS}
    matched, discrepancies, unmatched = [], [], []

    for claim in CLAIMS:
        eob = eob_map.get(claim["id"])
        if eob is None:
            unmatched.append(claim)
        elif eob["status"] == "paid" and abs(eob["paid"] - claim["amount"]) < 0.01:
            matched.append((claim, eob))
        else:
            discrepancies.append((claim, eob))

    total_paid = sum(e["paid"] for e in EOBS)
    total_discrepancy = total_billed - total_paid

    section("Reconciliation Results")
    result("Total claims:", str(len(CLAIMS)))
    result("Matched (full payment):", str(len(matched)))
    result("Discrepancies:", str(len(discrepancies)))
    result("Unmatched (no EOB):", str(len(unmatched)))
    result("Total billed:", f"${total_billed:,.2f}")
    result("Total paid:", f"${total_paid:,.2f}")
    result("Outstanding:", f"${total_discrepancy:,.2f}")

    section("Discrepancy Details")
    for claim, eob in discrepancies:
        diff = claim["amount"] - eob["paid"]
        status = eob["status"].upper()
        denial = f" [{eob['denial_code']}]" if eob.get("denial_code") else ""
        print(f"  {claim['id']}  ${claim['amount']:>8,.2f} billed  →  ${eob['paid']:>8,.2f} paid  [{status}{denial}]  Δ${diff:,.2f}")

    sleep(0.5)
    step("Uploading reconciliation result to 0G Storage for immutable audit trail...")
    recon_payload = {"claims": len(CLAIMS), "matched": len(matched), "discrepancies": len(discrepancies), "total_billed": total_billed, "total_paid": total_paid}
    root_hash = mock_0g_upload(recon_payload, "reconciliation")
    ok(f"0G Storage upload complete")
    result("  Root hash:", root_hash[:42] + "...")
    step("Verifying data integrity on 0G Network...")
    verified = mock_0g_verify(root_hash)
    ok(f"Cryptographic verification: {'PASSED' if verified else 'FAILED'}")
    print(f"\n  💡 Every reconciliation result is now immutably stored on 0G Network.")
    print(f"     Auditors can verify the exact data used — no tampering possible.")

    # ── Scene 3: Denial Analysis + 0G Compute ──────────────────────────────────
    header("Scene 3: Denial Analysis + 0G Compute AI", "🤖")
    denied = [(c, e) for c, e in discrepancies if e["status"] == "denied"]
    step(f"Analyzing {len(denied)} denied claims...")
    sleep(0.5)

    total_denied_amount = sum(c["amount"] for c, e in denied)
    result("Denied claims:", str(len(denied)))
    result("Total denied amount:", f"${total_denied_amount:,.2f}")

    section("AI-Powered Appeal Strategies (via 0G Compute)")
    for claim, eob in denied:
        code = eob.get("denial_code", "UNKNOWN")
        desc = DENIAL_DESCRIPTIONS.get(code, "Unknown denial reason")
        print(f"\n  Claim: {claim['id']}  |  Amount: ${claim['amount']:,.2f}  |  Code: {code}")
        print(f"  Reason: {desc}")
        step(f"  Running verifiable AI inference on 0G Compute...")
        ai_result = mock_0g_compute(code, claim)
        print(f"  Strategy: {ai_result['appeal_strategy']}")
        print(f"  Confidence: {ai_result['confidence']*100:.0f}%  |  Model: {ai_result['model']}")
        print(f"  Inference hash: {ai_result['inference_hash']} (verifiable on-chain)")
        ok(f"  Appeal strategy generated and verified")

    print(f"\n  💡 0G Compute ensures AI inference is verifiable — not a black box.")
    print(f"     Payers and auditors can independently verify the AI's reasoning.")

    # ── Scene 4: Financial Vitals ───────────────────────────────────────────────
    header("Scene 4: Financial Vitals Dashboard", "📊")

    # A/R Aging
    section("A/R Aging Report")
    aging_buckets = {"0-30 days": 0, "31-60 days": 0, "61-90 days": 0, "90+ days": 0}
    import datetime
    today = datetime.date(2026, 5, 12)
    for claim in CLAIMS:
        eob = eob_map.get(claim["id"])
        if eob and eob["status"] == "paid":
            continue
        claim_date = datetime.date.fromisoformat(claim["date"])
        days = (today - claim_date).days
        outstanding = claim["amount"] - (eob["paid"] if eob else 0)
        if days <= 30:
            aging_buckets["0-30 days"] += outstanding
        elif days <= 60:
            aging_buckets["31-60 days"] += outstanding
        elif days <= 90:
            aging_buckets["61-90 days"] += outstanding
        else:
            aging_buckets["90+ days"] += outstanding

    for bucket, amount in aging_buckets.items():
        bar = "█" * int(amount / 200)
        print(f"  {bucket:<12}  ${amount:>8,.2f}  {bar}")

    total_ar = sum(aging_buckets.values())
    result("\n  Total A/R Outstanding:", f"${total_ar:,.2f}")

    # Collection Rate
    section("Collection Rate")
    collection_rate = (total_paid / total_billed * 100) if total_billed > 0 else 0
    result("Total billed:", f"${total_billed:,.2f}")
    result("Total collected:", f"${total_paid:,.2f}")
    result("Collection rate:", f"{collection_rate:.1f}%")
    if collection_rate < 85:
        warn(f"Collection rate below 85% benchmark — review denial patterns")
    else:
        ok(f"Collection rate within acceptable range")

    # ── Scene 5: Summary ───────────────────────────────────────────────────────
    header("Scene 5: Executive Summary", "📋")
    print("  HealthPay Agent processed your revenue cycle data and found:\n")
    print(f"  • {len(discrepancies)} claims with payment issues (${total_discrepancy:,.2f} at risk)")
    print(f"  • {len(denied)} denied claims with AI-generated appeal strategies")
    print(f"  • {len(unmatched)} claims awaiting EOB response")
    print(f"  • Collection rate: {collection_rate:.1f}% (industry benchmark: 85%+)")
    print(f"\n  All results cryptographically stored on 0G Network:")
    print(f"  • Reconciliation audit trail: {root_hash[:20]}...")
    print(f"  • AI inference hashes: verifiable on 0G testnet")
    print(f"\n  Estimated recoverable revenue: ${total_denied_amount:,.2f}")
    print(f"  (via appeal of {len(denied)} denied claims)")

    print("\n" + "═"*62)
    print("  HealthPay Agent — Built for 0G APAC Hackathon 2026")
    print("  Track: Verifiable Finance + Agentic Infrastructure")
    print("  Team: Leon Huang (Fintech CTO)")
    print("═"*62 + "\n")

if __name__ == "__main__":
    main()
