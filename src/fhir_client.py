"""
FHIR R4 Client for HealthPay Reconciliation Agent.
Handles communication with HAPI FHIR server to fetch Claims, EOBs, Coverage, and Patient data.
"""

import logging
from typing import Optional, Any
from datetime import datetime, date

import httpx

logger = logging.getLogger(__name__)


class FHIRClient:
    """Async FHIR R4 client for healthcare payment data retrieval."""

    def __init__(self, base_url: str, access_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            }
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _search(self, resource_type: str, params: dict[str, Any]) -> list[dict]:
        """Generic FHIR search returning all entries from a Bundle."""
        client = await self._get_client()
        all_entries = []
        url = f"/{resource_type}"

        while url:
            response = await client.get(url, params=params if url.startswith("/") else None)
            response.raise_for_status()
            bundle = response.json()

            entries = bundle.get("entry", [])
            all_entries.extend([e.get("resource", e) for e in entries])

            # Handle pagination
            url = None
            for link in bundle.get("link", []):
                if link.get("relation") == "next":
                    url = link.get("url", "")
                    # Convert absolute URL to relative if needed
                    if url.startswith(self.base_url):
                        url = url[len(self.base_url):]
                    params = None  # params are embedded in the next URL
                    break

        return all_entries

    async def get_patient(self, patient_id: str) -> Optional[dict]:
        """Fetch a single Patient resource by ID."""
        client = await self._get_client()
        try:
            response = await client.get(f"/Patient/{patient_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def search_patients(self, name: Optional[str] = None, count: int = 50) -> list[dict]:
        """Search for patients by name or list all."""
        params: dict[str, Any] = {"_count": str(count)}
        if name:
            params["name"] = name
        return await self._search("Patient", params)

    async def get_claims(
        self,
        patient_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[dict]:
        """
        Fetch Claim resources for a patient.
        Args:
            patient_id: FHIR Patient resource ID
            date_from: ISO date string (YYYY-MM-DD) for start of range
            date_to: ISO date string (YYYY-MM-DD) for end of range
        """
        params: dict[str, Any] = {
            "patient": f"Patient/{patient_id}",
            "_count": "200",
        }
        if date_from:
            params["created"] = f"ge{date_from}"
        if date_to:
            if "created" in params:
                # FHIR allows multiple date params for range
                params["created"] = [params["created"], f"le{date_to}"]
            else:
                params["created"] = f"le{date_to}"

        return await self._search("Claim", params)

    async def get_eobs(
        self,
        patient_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[dict]:
        """
        Fetch ExplanationOfBenefit resources for a patient.
        Args:
            patient_id: FHIR Patient resource ID
            date_from: ISO date string for start of range
            date_to: ISO date string for end of range
        """
        params: dict[str, Any] = {
            "patient": f"Patient/{patient_id}",
            "_count": "200",
        }
        if date_from:
            params["created"] = f"ge{date_from}"
        if date_to:
            if "created" in params:
                params["created"] = [params["created"], f"le{date_to}"]
            else:
                params["created"] = f"le{date_to}"

        return await self._search("ExplanationOfBenefit", params)

    async def get_coverages(self, patient_id: str) -> list[dict]:
        """Fetch Coverage resources for a patient."""
        params = {
            "beneficiary": f"Patient/{patient_id}",
            "_count": "50",
        }
        return await self._search("Coverage", params)


    async def search_all(
        self,
        resource_type: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_results: int = 1000,
    ) -> list[dict]:
        """
        Fetch all resources of a type (no patient filter).
        Used for organization-wide reports.
        """
        params: dict[str, Any] = {"_count": "200"}
        if date_from:
            params["date"] = f"ge{date_from}"
        if date_to:
            if "date" in params:
                params["date"] = [params["date"], f"le{date_to}"]
            else:
                params["date"] = f"le{date_to}"

        results = await self._search(resource_type, params)
        return results[:max_results]

    async def get_resource_count(self, resource_type: str) -> int:
        """Get total count of a resource type on the server."""
        client = await self._get_client()
        response = await client.get(f"/{resource_type}", params={"_summary": "count"})
        response.raise_for_status()
        return response.json().get("total", 0)

    async def get_server_stats(self) -> dict:
        """Get server statistics for key resource types."""
        resource_types = ["Patient", "Claim", "ExplanationOfBenefit", "Coverage", "Organization"]
        stats = {}
        for rt in resource_types:
            try:
                stats[rt] = await self.get_resource_count(rt)
            except Exception as e:
                stats[rt] = f"error: {e}"
        return stats
