#!/usr/bin/env python3
"""
Import Synthea-generated FHIR bundles into HAPI FHIR server.
Handles transaction bundles and individual resources.
"""

import json
import os
import sys
import time
import httpx

FHIR_BASE = os.environ.get("FHIR_SERVER_URL", "http://localhost:19911/fhir")
DATA_DIR = os.environ.get("SYNTHEA_OUTPUT", "/home/taomi/projects/healthpay-agent/data/synthea_output/fhir")
TIMEOUT = 60.0


def import_bundle(client: httpx.Client, filepath: str) -> dict:
    """Import a single FHIR bundle file."""
    with open(filepath, "r") as f:
        bundle = json.load(f)

    resource_type = bundle.get("resourceType", "")
    bundle_type = bundle.get("type", "")

    if resource_type == "Bundle" and bundle_type == "transaction":
        # Post as transaction bundle
        resp = client.post("/", json=bundle)
        if resp.status_code in (200, 201):
            result = resp.json()
            entries = result.get("entry", [])
            return {"status": "ok", "entries": len(entries)}
        else:
            return {"status": "error", "code": resp.status_code, "body": resp.text[:200]}
    elif resource_type == "Bundle":
        # Convert to transaction bundle
        bundle["type"] = "transaction"
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            rt = resource.get("resourceType", "")
            rid = resource.get("id", "")
            if rt and rid:
                entry["request"] = {
                    "method": "PUT",
                    "url": f"{rt}/{rid}"
                }
            elif rt:
                entry["request"] = {
                    "method": "POST",
                    "url": rt
                }
        resp = client.post("/", json=bundle)
        if resp.status_code in (200, 201):
            result = resp.json()
            entries = result.get("entry", [])
            return {"status": "ok", "entries": len(entries)}
        else:
            return {"status": "error", "code": resp.status_code, "body": resp.text[:200]}
    else:
        # Single resource
        rt = bundle.get("resourceType", "Unknown")
        rid = bundle.get("id", "")
        if rid:
            resp = client.put(f"/{rt}/{rid}", json=bundle)
        else:
            resp = client.post(f"/{rt}", json=bundle)
        if resp.status_code in (200, 201):
            return {"status": "ok", "entries": 1}
        else:
            return {"status": "error", "code": resp.status_code, "body": resp.text[:200]}


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else DATA_DIR
    print(f"Importing FHIR data from: {data_dir}")
    print(f"FHIR server: {FHIR_BASE}")

    if not os.path.isdir(data_dir):
        print(f"ERROR: Directory not found: {data_dir}")
        sys.exit(1)

    json_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")])
    print(f"Found {len(json_files)} JSON files to import")

    # Import hospital and practitioner bundles first
    priority_files = []
    patient_files = []
    for f in json_files:
        if f.startswith("hospital") or f.startswith("practitioner"):
            priority_files.append(f)
        else:
            patient_files.append(f)

    ordered_files = priority_files + patient_files

    client = httpx.Client(
        base_url=FHIR_BASE,
        headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
        timeout=TIMEOUT,
    )

    total_entries = 0
    success = 0
    errors = 0
    start = time.time()

    for i, filename in enumerate(ordered_files, 1):
        filepath = os.path.join(data_dir, filename)
        try:
            result = import_bundle(client, filepath)
            if result["status"] == "ok":
                total_entries += result["entries"]
                success += 1
                if i % 10 == 0 or i == len(ordered_files):
                    elapsed = time.time() - start
                    print(f"  [{i}/{len(ordered_files)}] {filename}: {result['entries']} entries "
                          f"({elapsed:.0f}s elapsed)")
            else:
                errors += 1
                print(f"  [{i}/{len(ordered_files)}] ERROR {filename}: {result.get('code')} - {result.get('body', '')[:100]}")
        except Exception as e:
            errors += 1
            print(f"  [{i}/{len(ordered_files)}] EXCEPTION {filename}: {e}")

    elapsed = time.time() - start
    client.close()

    print(f"\n=== Import Complete ===")
    print(f"Files processed: {success + errors}")
    print(f"Successful: {success}")
    print(f"Errors: {errors}")
    print(f"Total entries imported: {total_entries}")
    print(f"Time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
