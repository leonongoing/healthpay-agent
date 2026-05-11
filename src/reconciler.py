"""
Claims Reconciliation Engine.
Matches Claims against ExplanationOfBenefit (EOB) records and identifies discrepancies.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiscrepancyType(str, Enum):
    DENIED = "denied"
    PARTIAL_PAYMENT = "partial_payment"
    OVERPAYMENT = "overpayment"
    UNDERPAYMENT = "underpayment"
    NO_EOB = "no_eob_found"
    NO_CLAIM = "no_claim_found"
    AMOUNT_MISMATCH = "amount_mismatch"


class MatchedPair(BaseModel):
    claim_id: str
    eob_id: str
    claim_amount: float
    paid_amount: float
    patient_responsibility: float = 0.0
    status: str = "matched"
    discrepancy_type: Optional[DiscrepancyType] = None
    discrepancy_amount: float = 0.0
    claim_date: Optional[str] = None
    eob_date: Optional[str] = None
    claim_type: Optional[str] = None
    provider: Optional[str] = None


class UnmatchedItem(BaseModel):
    resource_type: str  # "Claim" or "ExplanationOfBenefit"
    resource_id: str
    amount: float
    date: Optional[str] = None
    status: Optional[str] = None
    reason: str = ""


class ReconciliationResult(BaseModel):
    patient_id: str
    date_range: Optional[str] = None
    total_claims: int = 0
    total_eobs: int = 0
    matched: list[MatchedPair] = Field(default_factory=list)
    unmatched: list[UnmatchedItem] = Field(default_factory=list)
    discrepancies: list[MatchedPair] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


def _extract_claim_total(claim: dict) -> float:
    """Extract total amount from a FHIR Claim resource."""
    total = claim.get("total", {})
    if isinstance(total, dict):
        return float(total.get("value", 0))
    return 0.0


def _extract_claim_date(claim: dict) -> Optional[str]:
    """Extract created/billable date from a Claim."""
    return claim.get("created") or claim.get("billablePeriod", {}).get("start")


def _extract_eob_claim_ref(eob: dict) -> Optional[str]:
    """Extract the Claim reference from an EOB."""
    claim_ref = eob.get("claim", {}).get("reference", "")
    # Could be "Claim/123" or "urn:uuid:xxx"
    if claim_ref.startswith("Claim/"):
        return claim_ref.split("/")[-1]
    if claim_ref.startswith("urn:uuid:"):
        return claim_ref.replace("urn:uuid:", "")
    return claim_ref or None


def _extract_eob_payment(eob: dict) -> float:
    """Extract payment amount from an EOB."""
    payment = eob.get("payment", {})
    amount = payment.get("amount", {})
    if isinstance(amount, dict):
        return float(amount.get("value", 0))
    return 0.0


def _extract_eob_total_by_category(eob: dict, category: str) -> float:
    """Extract a specific total from EOB totals by category code."""
    for total in eob.get("total", []):
        cat = total.get("category", {})
        codings = cat.get("coding", [])
        for coding in codings:
            if coding.get("code") == category:
                return float(total.get("amount", {}).get("value", 0))
    return 0.0


def _extract_adjudication_amount(eob: dict, adj_category: str) -> float:
    """Extract adjudication amount from EOB items by category."""
    total = 0.0
    for item in eob.get("item", []):
        for adj in item.get("adjudication", []):
            cat = adj.get("category", {})
            codings = cat.get("coding", [])
            for coding in codings:
                if coding.get("code") == adj_category:
                    total += float(adj.get("amount", {}).get("value", 0))
    return total


def _extract_eob_date(eob: dict) -> Optional[str]:
    """Extract date from an EOB."""
    return eob.get("created") or eob.get("billablePeriod", {}).get("start")


def _extract_eob_status(eob: dict) -> str:
    """Extract outcome/status from an EOB."""
    return eob.get("outcome", eob.get("status", "unknown"))


def _extract_claim_type(resource: dict) -> Optional[str]:
    """Extract claim type from Claim or EOB."""
    type_obj = resource.get("type", {})
    codings = type_obj.get("coding", [])
    if codings:
        return codings[0].get("code")
    return None


def _extract_provider(resource: dict) -> Optional[str]:
    """Extract provider reference from Claim or EOB."""
    provider = resource.get("provider", {})
    return provider.get("display") or provider.get("reference")


def reconcile(
    patient_id: str,
    claims: list[dict],
    eobs: list[dict],
    tolerance_amount: float = 0.01,
    tolerance_days: int = 3,
    date_range: Optional[str] = None,
) -> ReconciliationResult:
    """
    Reconcile Claims against EOBs for a patient.

    Matching strategy (in priority order):
    1. Direct reference: EOB.claim references the Claim ID
    2. Amount + date proximity: same total amount within tolerance window
    3. Claim type + date: same type and close date

    Returns matched pairs, unmatched items, and discrepancies.
    """
    result = ReconciliationResult(patient_id=patient_id, date_range=date_range)
    result.total_claims = len(claims)
    result.total_eobs = len(eobs)

    # Build lookup structures
    claims_by_id: dict[str, dict] = {}
    for c in claims:
        cid = c.get("id", "")
        claims_by_id[cid] = c

    matched_claim_ids: set[str] = set()
    matched_eob_ids: set[str] = set()

    # Pass 1: Match by direct Claim reference in EOB
    for eob in eobs:
        eob_id = eob.get("id", "")
        claim_ref = _extract_eob_claim_ref(eob)

        if claim_ref and claim_ref in claims_by_id:
            claim = claims_by_id[claim_ref]
            claim_amount = _extract_claim_total(claim)
            paid_amount = _extract_eob_payment(eob)
            patient_resp = _extract_adjudication_amount(eob, "copay") + \
                           _extract_adjudication_amount(eob, "deductible")
            eob_status = _extract_eob_status(eob)

            pair = MatchedPair(
                claim_id=claim_ref,
                eob_id=eob_id,
                claim_amount=claim_amount,
                paid_amount=paid_amount,
                patient_responsibility=patient_resp,
                claim_date=_extract_claim_date(claim),
                eob_date=_extract_eob_date(eob),
                claim_type=_extract_claim_type(claim),
                provider=_extract_provider(claim),
            )

            # Determine discrepancy
            diff = claim_amount - paid_amount - patient_resp
            if eob_status == "denied" or (claim_amount > 0 and paid_amount == 0):
                pair.discrepancy_type = DiscrepancyType.DENIED
                pair.discrepancy_amount = claim_amount
                pair.status = "discrepancy"
                result.discrepancies.append(pair)
            elif abs(diff) > tolerance_amount:
                if paid_amount > claim_amount:
                    pair.discrepancy_type = DiscrepancyType.OVERPAYMENT
                else:
                    pair.discrepancy_type = DiscrepancyType.PARTIAL_PAYMENT
                pair.discrepancy_amount = round(diff, 2)
                pair.status = "discrepancy"
                result.discrepancies.append(pair)
            else:
                pair.status = "matched"
                result.matched.append(pair)

            matched_claim_ids.add(claim_ref)
            matched_eob_ids.add(eob_id)

    # Pass 2: Fuzzy match remaining by amount + date
    unmatched_claims = [c for c in claims if c.get("id") not in matched_claim_ids]
    unmatched_eobs = [e for e in eobs if e.get("id") not in matched_eob_ids]

    for claim in unmatched_claims[:]:
        claim_id = claim.get("id", "")
        claim_amount = _extract_claim_total(claim)
        claim_date_str = _extract_claim_date(claim)

        best_match = None
        best_score = 0

        for eob in unmatched_eobs:
            eob_id = eob.get("id", "")
            if eob_id in matched_eob_ids:
                continue

            # Check amount similarity
            eob_submitted = _extract_eob_total_by_category(eob, "submitted")
            if eob_submitted == 0:
                eob_submitted = _extract_eob_payment(eob)

            amount_diff = abs(claim_amount - eob_submitted)
            if claim_amount > 0 and amount_diff / claim_amount > 0.2:
                continue  # More than 20% difference, skip

            # Check date proximity
            eob_date_str = _extract_eob_date(eob)
            date_score = 1.0
            if claim_date_str and eob_date_str:
                try:
                    cd = datetime.fromisoformat(claim_date_str[:10])
                    ed = datetime.fromisoformat(eob_date_str[:10])
                    day_diff = abs((cd - ed).days)
                    if day_diff > tolerance_days:
                        continue
                    date_score = 1.0 - (day_diff / (tolerance_days + 1))
                except (ValueError, TypeError):
                    pass

            # Check type match
            type_score = 1.0 if _extract_claim_type(claim) == _extract_claim_type(eob) else 0.5

            score = date_score * type_score * (1.0 - min(amount_diff / max(claim_amount, 1), 1.0))
            if score > best_score:
                best_score = score
                best_match = eob

        if best_match and best_score > 0.5:
            eob_id = best_match.get("id", "")
            paid_amount = _extract_eob_payment(best_match)
            patient_resp = _extract_adjudication_amount(best_match, "copay") + \
                           _extract_adjudication_amount(best_match, "deductible")

            pair = MatchedPair(
                claim_id=claim_id,
                eob_id=eob_id,
                claim_amount=claim_amount,
                paid_amount=paid_amount,
                patient_responsibility=patient_resp,
                claim_date=claim_date_str,
                eob_date=_extract_eob_date(best_match),
                claim_type=_extract_claim_type(claim),
                provider=_extract_provider(claim),
            )

            diff = claim_amount - paid_amount - patient_resp
            if abs(diff) > tolerance_amount:
                pair.discrepancy_type = DiscrepancyType.AMOUNT_MISMATCH
                pair.discrepancy_amount = round(diff, 2)
                pair.status = "discrepancy"
                result.discrepancies.append(pair)
            else:
                pair.status = "matched"
                result.matched.append(pair)

            matched_claim_ids.add(claim_id)
            matched_eob_ids.add(eob_id)
            unmatched_eobs = [e for e in unmatched_eobs if e.get("id") != eob_id]

    # Collect unmatched items
    for claim in claims:
        if claim.get("id") not in matched_claim_ids:
            result.unmatched.append(UnmatchedItem(
                resource_type="Claim",
                resource_id=claim.get("id", "unknown"),
                amount=_extract_claim_total(claim),
                date=_extract_claim_date(claim),
                status=claim.get("status"),
                reason="No matching EOB found",
            ))

    for eob in eobs:
        if eob.get("id") not in matched_eob_ids:
            result.unmatched.append(UnmatchedItem(
                resource_type="ExplanationOfBenefit",
                resource_id=eob.get("id", "unknown"),
                amount=_extract_eob_payment(eob),
                date=_extract_eob_date(eob),
                status=_extract_eob_status(eob),
                reason="No matching Claim found",
            ))

    # Build summary
    total_claimed = sum(m.claim_amount for m in result.matched) + \
                    sum(d.claim_amount for d in result.discrepancies)
    total_paid = sum(m.paid_amount for m in result.matched) + \
                 sum(d.paid_amount for d in result.discrepancies)
    total_discrepancy = sum(abs(d.discrepancy_amount) for d in result.discrepancies)

    result.summary = {
        "total_claims": result.total_claims,
        "total_eobs": result.total_eobs,
        "matched_count": len(result.matched),
        "discrepancy_count": len(result.discrepancies),
        "unmatched_count": len(result.unmatched),
        "total_claimed_amount": round(total_claimed, 2),
        "total_paid_amount": round(total_paid, 2),
        "total_discrepancy_amount": round(total_discrepancy, 2),
        "match_rate": round(len(result.matched) / max(result.total_claims, 1) * 100, 1),
        "discrepancy_breakdown": {},
    }

    # Breakdown by discrepancy type
    for d in result.discrepancies:
        dt = d.discrepancy_type.value if d.discrepancy_type else "unknown"
        if dt not in result.summary["discrepancy_breakdown"]:
            result.summary["discrepancy_breakdown"][dt] = {"count": 0, "total_amount": 0.0}
        result.summary["discrepancy_breakdown"][dt]["count"] += 1
        result.summary["discrepancy_breakdown"][dt]["total_amount"] += abs(d.discrepancy_amount)

    return result
