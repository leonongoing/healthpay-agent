#!/usr/bin/env python3
"""
Enrich Synthea-generated EOB data with realistic adjudication details.
Synthea EOBs often lack detailed adjudication (copay, deductible, coinsurance).
This script patches existing EOBs on the FHIR server with richer payment data.
"""

import json
import random
import sys
import httpx

FHIR_BASE = "http://localhost:19911/fhir"
TIMEOUT = 30.0

# Realistic adjudication scenarios
SCENARIOS = [
    # (weight, name, paid_pct, copay, deductible, coinsurance, outcome)
    (40, "full_payment", 0.80, 25.0, 0.0, 0.0, "complete"),
    (20, "with_deductible", 0.70, 25.0, 200.0, 0.0, "complete"),
    (15, "partial_coinsurance", 0.60, 40.0, 100.0, 0.10, "partial"),
    (10, "denied_medical_necessity", 0.0, 0.0, 0.0, 0.0, "denied"),
    (5, "denied_auth_required", 0.0, 0.0, 0.0, 0.0, "denied"),
    (5, "overpayment", 1.05, 0.0, 0.0, 0.0, "complete"),
    (5, "minimal_coverage", 0.30, 50.0, 500.0, 0.20, "partial"),
]

DENIAL_REASONS = {
    "denied_medical_necessity": {
        "code": "MN",
        "display": "Medical Necessity",
        "system": "http://terminology.hl7.org/CodeSystem/adjudication-reason"
    },
    "denied_auth_required": {
        "code": "PA",
        "display": "Prior Authorization Required",
        "system": "http://terminology.hl7.org/CodeSystem/adjudication-reason"
    },
}


def pick_scenario():
    """Weighted random selection of payment scenario."""
    total = sum(s[0] for s in SCENARIOS)
    r = random.uniform(0, total)
    cumulative = 0
    for weight, name, paid_pct, copay, deductible, coinsurance, outcome in SCENARIOS:
        cumulative += weight
        if r <= cumulative:
            return name, paid_pct, copay, deductible, coinsurance, outcome
    return SCENARIOS[0][1:]


def build_adjudication(submitted: float, scenario_name: str, paid_pct: float,
                        copay: float, deductible: float, coinsurance: float):
    """Build FHIR adjudication entries."""
    eligible = max(submitted - deductible, 0)
    coinsurance_amount = eligible * coinsurance
    benefit = max(eligible * paid_pct - coinsurance_amount, 0)
    patient_pays = copay + deductible + coinsurance_amount + max(submitted - eligible - copay, 0)

    adjudication = [
        {
            "category": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/adjudication",
                            "code": "submitted", "display": "Submitted Amount"}]
            },
            "amount": {"value": round(submitted, 2), "currency": "USD"}
        },
        {
            "category": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/adjudication",
                            "code": "eligible", "display": "Eligible Amount"}]
            },
            "amount": {"value": round(eligible, 2), "currency": "USD"}
        },
        {
            "category": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/adjudication",
                            "code": "copay", "display": "CoPay"}]
            },
            "amount": {"value": round(copay, 2), "currency": "USD"}
        },
        {
            "category": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/adjudication",
                            "code": "deductible", "display": "Deductible"}]
            },
            "amount": {"value": round(deductible, 2), "currency": "USD"}
        },
        {
            "category": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/adjudication",
                            "code": "benefit", "display": "Benefit Amount"}]
            },
            "amount": {"value": round(benefit, 2), "currency": "USD"}
        },
    ]
    return adjudication, benefit


def enrich_eob(eob: dict) -> dict:
    """Add realistic adjudication to an EOB resource."""
    scenario_name, paid_pct, copay, deductible, coinsurance, outcome = pick_scenario()

    # Calculate submitted amount from items
    submitted_total = 0
    for item in eob.get("item", []):
        net = item.get("net", {}).get("value", 0)
        submitted_total += float(net) if net else 0

    if submitted_total == 0:
        # Try from total
        for total in eob.get("total", []):
            cat_code = ""
            for coding in total.get("category", {}).get("coding", []):
                cat_code = coding.get("code", "")
            if cat_code in ("submitted", ""):
                submitted_total = float(total.get("amount", {}).get("value", 0))
                break

    if submitted_total == 0:
        submitted_total = random.uniform(100, 5000)

    # Enrich each item with adjudication
    for item in eob.get("item", []):
        item_amount = float(item.get("net", {}).get("value", submitted_total / max(len(eob.get("item", [])), 1)))
        item_adj, _ = build_adjudication(item_amount, scenario_name, paid_pct, copay, deductible, coinsurance)
        item["adjudication"] = item_adj

    # Set overall adjudication and payment
    _, benefit_total = build_adjudication(submitted_total, scenario_name, paid_pct, copay, deductible, coinsurance)

    eob["payment"] = {
        "amount": {"value": round(benefit_total, 2), "currency": "USD"}
    }
    eob["outcome"] = outcome

    # Add totals
    eob["total"] = [
        {
            "category": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/adjudication",
                            "code": "submitted", "display": "Submitted Amount"}]
            },
            "amount": {"value": round(submitted_total, 2), "currency": "USD"}
        },
        {
            "category": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/adjudication",
                            "code": "benefit", "display": "Benefit Amount"}]
            },
            "amount": {"value": round(benefit_total, 2), "currency": "USD"}
        },
    ]

    # Add denial reason if denied
    if scenario_name in DENIAL_REASONS:
        reason = DENIAL_REASONS[scenario_name]
        if "processNote" not in eob:
            eob["processNote"] = []
        eob["processNote"].append({
            "type": "denial",
            "text": f"Claim denied: {reason['display']}"
        })

    return eob


def main():
    print(f"Enriching EOBs on FHIR server: {FHIR_BASE}")

    client = httpx.Client(
        base_url=FHIR_BASE,
        headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
        timeout=TIMEOUT,
    )

    # Fetch all EOBs
    all_eobs = []
    url = "/ExplanationOfBenefit?_count=200"
    while url:
        resp = client.get(url)
        resp.raise_for_status()
        bundle = resp.json()
        for entry in bundle.get("entry", []):
            all_eobs.append(entry.get("resource", entry))
        url = None
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                next_url = link["url"]
                if next_url.startswith(FHIR_BASE):
                    url = next_url[len(FHIR_BASE):]
                else:
                    url = next_url

    print(f"Found {len(all_eobs)} EOBs to enrich")

    enriched = 0
    errors = 0
    for i, eob in enumerate(all_eobs, 1):
        eob_id = eob.get("id", "")
        try:
            enriched_eob = enrich_eob(eob)
            resp = client.put(f"/ExplanationOfBenefit/{eob_id}", json=enriched_eob)
            if resp.status_code in (200, 201):
                enriched += 1
            else:
                errors += 1
                print(f"  Error updating EOB {eob_id}: {resp.status_code}")
            if i % 50 == 0:
                print(f"  Processed {i}/{len(all_eobs)}...")
        except Exception as e:
            errors += 1
            print(f"  Exception for EOB {eob_id}: {e}")

    client.close()
    print(f"\n=== Enrichment Complete ===")
    print(f"Total EOBs: {len(all_eobs)}")
    print(f"Enriched: {enriched}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
