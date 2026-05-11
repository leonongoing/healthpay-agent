"""
HealthPay Reconciliation Agent — Prompt Opinion Compatible MCP Server.
Uses FastMCP with Streamable HTTP transport for Prompt Opinion Marketplace integration.
"""

import json
import logging
from typing import Annotated, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field
import jwt

from .config import settings
from .fhir_client import FHIRClient
from .reconciler import reconcile
from .denial_analyzer import analyze_denials
from .ar_reporter import generate_ar_report
from .risk_predictor import predict_payment_risk
from .coding_optimizer import suggest_coding_optimization

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for SHARP-on-MCP headers
FHIR_SERVER_URL_HEADER = "x-fhir-server-url"
FHIR_ACCESS_TOKEN_HEADER = "x-fhir-access-token"
PATIENT_ID_HEADER = "x-patient-id"

# FastMCP instance
mcp = FastMCP("HealthPay Reconciliation Agent", stateless_http=True, host="0.0.0.0")

# Patch capabilities to declare FHIR context support
_original_get_capabilities = mcp._mcp_server.get_capabilities

def _patched_get_capabilities(notification_options, experimental_capabilities):
    caps = _original_get_capabilities(notification_options, experimental_capabilities)
    caps.model_extra["extensions"] = {"ai.promptopinion/fhir-context": {}}
    return caps

mcp._mcp_server.get_capabilities = _patched_get_capabilities


def _get_fhir_context(ctx: Context) -> tuple[str, Optional[str]]:
    """Extract FHIR server URL and access token from SHARP context headers."""
    req = ctx.request_context.request
    url = req.headers.get(FHIR_SERVER_URL_HEADER, settings.fhir_server_url)
    token = req.headers.get(FHIR_ACCESS_TOKEN_HEADER, settings.fhir_access_token)
    return url, token


def _get_patient_id(ctx: Context, provided_id: Optional[str] = None) -> Optional[str]:
    """Get patient ID from explicit param, JWT token, or header."""
    if provided_id:
        return provided_id
    req = ctx.request_context.request
    # Try JWT first
    fhir_token = req.headers.get(FHIR_ACCESS_TOKEN_HEADER)
    if fhir_token:
        try:
            claims = jwt.decode(fhir_token, options={"verify_signature": False})
            patient = claims.get("patient")
            if patient:
                return str(patient)
        except Exception:
            pass
    # Fall back to header
    return req.headers.get(PATIENT_ID_HEADER)


def _get_fhir_client(ctx: Context) -> FHIRClient:
    url, token = _get_fhir_context(ctx)
    return FHIRClient(base_url=url, access_token=token)


# ─── Tools ───────────────────────────────────────────────────────────────────

@mcp.tool(
    name="ReconcileClaims",
    description=(
        "Reconcile healthcare claims against insurance EOBs for a patient. "
        "Identifies matched payments, denials, partial payments, and overpayments."
    ),
)
async def reconcile_claims(
    patientId: Annotated[
        str | None,
        Field(description="FHIR Patient resource ID. Optional if patient context exists."),
    ] = None,
    dateFrom: Annotated[
        str | None,
        Field(description="Start date (YYYY-MM-DD) for claim date range filter"),
    ] = None,
    dateTo: Annotated[
        str | None,
        Field(description="End date (YYYY-MM-DD) for claim date range filter"),
    ] = None,
    ctx: Context = None,
) -> str:
    pid = _get_patient_id(ctx, patientId)
    if not pid:
        raise ValueError("No patient ID provided and no patient context found")

    fhir = _get_fhir_client(ctx)
    try:
        claims = await fhir.get_claims(pid, dateFrom, dateTo)
        eobs = await fhir.get_eobs(pid, dateFrom, dateTo)

        if not claims and not eobs:
            return json.dumps({"patient_id": pid, "message": "No claims or EOBs found."})

        result = reconcile(
            patient_id=pid, claims=claims, eobs=eobs,
            tolerance_amount=settings.match_tolerance_amount,
            tolerance_days=settings.match_tolerance_days,
        )
        return json.dumps(result.model_dump(), indent=2, default=str)
    finally:
        await fhir.close()


@mcp.tool(
    name="AnalyzeDenials",
    description=(
        "Analyze claim denials for a patient. Classifies denial reasons, "
        "identifies patterns, and generates prioritized appeal recommendations."
    ),
)
async def analyze_denials_tool(
    patientId: Annotated[
        str | None,
        Field(description="FHIR Patient resource ID"),
    ] = None,
    ctx: Context = None,
) -> str:
    pid = _get_patient_id(ctx, patientId)
    if not pid:
        raise ValueError("No patient ID provided and no patient context found")

    fhir = _get_fhir_client(ctx)
    try:
        claims = await fhir.get_claims(pid)
        eobs = await fhir.get_eobs(pid)
        if not claims and not eobs:
            return json.dumps({"patient_id": pid, "message": "No claims or EOBs found."})
        report = analyze_denials(patient_id=pid, claims=claims, eobs=eobs)
        return json.dumps(report.model_dump(), indent=2, default=str)
    finally:
        await fhir.close()


@mcp.tool(
    name="GenerateARReport",
    description=(
        "Generate an Accounts Receivable report with Financial Vital Signs. "
        "Shows aging buckets, payer performance, collection rates, and recommendations."
    ),
)
async def generate_ar_report_tool(
    dateFrom: Annotated[
        str | None,
        Field(description="Start date (YYYY-MM-DD)"),
    ] = None,
    dateTo: Annotated[
        str | None,
        Field(description="End date (YYYY-MM-DD)"),
    ] = None,
    ctx: Context = None,
) -> str:
    fhir = _get_fhir_client(ctx)
    try:
        claims = await fhir.search_all("Claim", dateFrom, dateTo)
        eobs = await fhir.search_all("ExplanationOfBenefit", dateFrom, dateTo)
        if not claims:
            return json.dumps({"message": "No claims found."})
        report = generate_ar_report(claims=claims, eobs=eobs, report_date=dateFrom)
        return json.dumps(report.model_dump(), indent=2, default=str)
    finally:
        await fhir.close()


@mcp.tool(
    name="PredictPaymentRisk",
    description=(
        "Predict payment risk for a patient's claims based on historical patterns. "
        "Returns risk scores, payment probabilities, and risk factors."
    ),
)
async def predict_risk_tool(
    patientId: Annotated[
        str | None,
        Field(description="FHIR Patient resource ID"),
    ] = None,
    ctx: Context = None,
) -> str:
    pid = _get_patient_id(ctx, patientId)
    if not pid:
        raise ValueError("No patient ID provided and no patient context found")

    fhir = _get_fhir_client(ctx)
    try:
        claims = await fhir.get_claims(pid)
        eobs = await fhir.get_eobs(pid)
        if not claims:
            return json.dumps({"patient_id": pid, "message": "No claims found."})
        report = predict_payment_risk(
            target_claims=claims, historical_claims=claims,
            historical_eobs=eobs, patient_id=pid,
        )
        return json.dumps(report.model_dump(), indent=2, default=str)
    finally:
        await fhir.close()


@mcp.tool(
    name="SuggestCodingOptimization",
    description=(
        "Analyze claims for ICD-10/CPT coding optimization opportunities. "
        "Identifies specificity issues, missing modifiers, and documentation gaps."
    ),
)
async def suggest_coding_tool(
    patientId: Annotated[
        str | None,
        Field(description="FHIR Patient resource ID"),
    ] = None,
    ctx: Context = None,
) -> str:
    pid = _get_patient_id(ctx, patientId)
    if not pid:
        raise ValueError("No patient ID provided and no patient context found")

    fhir = _get_fhir_client(ctx)
    try:
        claims = await fhir.get_claims(pid)
        eobs = await fhir.get_eobs(pid)
        if not claims:
            return json.dumps({"patient_id": pid, "message": "No claims found."})
        report = suggest_coding_optimization(patient_id=pid, claims=claims, eobs=eobs)
        return json.dumps(report.model_dump(), indent=2, default=str)
    finally:
        await fhir.close()


@mcp.tool(
    name="GetServerStats",
    description="Get FHIR server resource counts for Patients, Claims, EOBs, Coverage, and Organizations.",
)
async def get_server_stats(ctx: Context = None) -> str:
    fhir = _get_fhir_client(ctx)
    try:
        stats = await fhir.get_server_stats()
        return json.dumps({"fhir_server": fhir.base_url, "resource_counts": stats}, indent=2)
    finally:
        await fhir.close()


@mcp.tool(
    name="ListPatients",
    description="List patients available in the FHIR server.",
)
async def list_patients_tool(
    name: Annotated[
        str | None,
        Field(description="Patient name to search for"),
    ] = None,
    count: Annotated[
        int,
        Field(description="Max patients to return", default=20),
    ] = 20,
    ctx: Context = None,
) -> str:
    fhir = _get_fhir_client(ctx)
    try:
        patients = await fhir.search_patients(name=name, count=count)
        patient_list = []
        for p in patients:
            names = p.get("name", [])
            display_name = "Unknown"
            if names:
                n = names[0]
                given = " ".join(n.get("given", []))
                family = n.get("family", "")
                display_name = f"{given} {family}".strip()
            patient_list.append({
                "id": p.get("id"),
                "name": display_name,
                "gender": p.get("gender"),
                "birthDate": p.get("birthDate"),
            })
        return json.dumps({"total_found": len(patient_list), "patients": patient_list}, indent=2)
    finally:
        await fhir.close()


# ─── FastAPI App ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield

app = FastAPI(
    title="HealthPay Reconciliation Agent",
    description="Healthcare payment reconciliation MCP server for Prompt Opinion",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/", mcp.streamable_http_app())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
