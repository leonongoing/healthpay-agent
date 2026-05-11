"""
SHARP Extension Specs context handler.
Manages healthcare-specific context propagation (patient IDs, FHIR tokens, org context).
"""

from typing import Optional
from pydantic import BaseModel, Field


class SharpContext(BaseModel):
    """
    SHARP (Secure Healthcare Agent Resource Protocol) context.
    Propagated through MCP tool calls to provide healthcare-specific context.
    """
    patient_id: Optional[str] = Field(
        None,
        description="FHIR Patient resource ID for the current context"
    )
    fhir_server_url: str = Field(
        "http://localhost:19911/fhir",
        description="Base URL of the FHIR R4 server"
    )
    fhir_access_token: Optional[str] = Field(
        None,
        description="Bearer token for FHIR API authentication"
    )
    organization_id: Optional[str] = Field(
        None,
        description="FHIR Organization resource ID for the healthcare org context"
    )

    def to_headers(self) -> dict[str, str]:
        """Convert context to HTTP headers for FHIR requests."""
        headers = {}
        if self.fhir_access_token:
            headers["Authorization"] = f"Bearer {self.fhir_access_token}"
        return headers


def extract_sharp_context(arguments: dict) -> SharpContext:
    """
    Extract SHARP context from MCP tool call arguments.
    The context can be passed as a nested 'context' object or as top-level fields.
    """
    ctx_data = arguments.get("context", {})
    if not ctx_data:
        # Try extracting from top-level arguments
        ctx_data = {
            k: arguments[k]
            for k in ["patient_id", "fhir_server_url", "fhir_access_token", "organization_id"]
            if k in arguments
        }
    return SharpContext(**ctx_data)
