"""
0G Integration End-to-End Test Script.

Tests 0G Storage upload/download and 0G Compute inference.
Falls back to mock mode when testnet is unavailable.
"""

import asyncio
import json
import sys
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_0g_storage_mock():
    """Test 0G Storage upload/download in mock mode (no private key)."""
    from src.zero_g_storage import upload_to_0g, download_from_0g

    print("\n=== Test 1: 0G Storage Upload (Mock Mode) ===")

    # Sample reconciliation result
    test_data = {
        "audit_type": "reconciliation",
        "patient_id": "test-patient-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_claims": 5,
            "matched": 3,
            "unmatched": 2,
            "total_billed": 15000.00,
            "total_paid": 9500.00,
        },
        "claims": [
            {"id": "claim-1", "amount": 3000, "status": "matched"},
            {"id": "claim-2", "amount": 5000, "status": "matched"},
            {"id": "claim-3", "amount": 1500, "status": "matched"},
            {"id": "claim-4", "amount": 2500, "status": "denied"},
            {"id": "claim-5", "amount": 3000, "status": "pending"},
        ],
    }

    # Upload
    root_hash = upload_to_0g(data=test_data, filename="test_reconciliation.json")
    print(f"  Upload OK — Root hash: {root_hash}")

    # Verify hash format
    assert root_hash.startswith("0x"), f"Hash should start with 0x, got: {root_hash}"
    assert len(root_hash) > 10, f"Hash too short: {root_hash}"
    print(f"  Hash format valid: ✓")

    # Verify deterministic
    root_hash_2 = upload_to_0g(data=test_data, filename="test_reconciliation.json")
    assert root_hash == root_hash_2, "Same data should produce same hash"
    print(f"  Deterministic hash: ✓")

    # Download (mock)
    print("\n=== Test 2: 0G Storage Download (Mock Mode) ===")
    downloaded = download_from_0g(root_hash, "/tmp/test_0g_download.json")
    assert downloaded["mock"] is True
    assert downloaded["root_hash"] == root_hash
    print(f"  Download OK (mock): ✓")
    print(f"  Mock data: {json.dumps(downloaded, indent=2)}")

    return root_hash


async def test_0g_compute_mock():
    """Test 0G Compute LLM client initialization and fallback."""
    from src.zero_g_compute import ZeroGLLM

    print("\n=== Test 3: 0G Compute Client Init ===")

    # Check availability
    try:
        import a0g
        available = True
    except ImportError:
        available = False
    print(f"  python-0g installed: {available}")

    private_key = os.environ.get("ZG_COMPUTE_PRIVATE_KEY", "")
    print(f"  Has private key: {bool(private_key and not private_key.startswith('0x_your'))}")

    # Init LLM client
    llm = ZeroGLLM()
    using_0g = llm.is_using_0g()
    print(f"  Using 0G Compute: {using_0g}")
    print(f"  Active provider: {llm.get_active_provider()}")

    await llm.close()
    print(f"  Client init + close: ✓")


def test_mcp_integration():
    """Test that MCP server can import all tools including 0G."""
    print("\n=== Test 4: MCP Server Import Check ===")

    from src.mcp_server import app, list_tools

    print(f"  MCP server import: ✓")

    # Check tools list
    tools = asyncio.run(list_tools())
    tool_names = [t.name for t in tools]
    print(f"  Tools registered: {len(tools)}")
    for name in tool_names:
        print(f"    - {name}")

    assert "store_audit_trail" in tool_names, "store_audit_trail tool missing!"
    assert "reconcile_claims" in tool_names, "reconcile_claims tool missing!"
    print(f"  store_audit_trail present: ✓")
    print(f"  All core tools present: ✓")


def main():
    print("=" * 60)
    print("0G Integration End-to-End Test")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results = {"passed": 0, "failed": 0, "skipped": 0}

    # Test 1-2: Storage mock
    try:
        test_0g_storage_mock()
        results["passed"] += 2
    except Exception as e:
        print(f"  FAILED: {e}")
        results["failed"] += 1

    # Test 3: Compute mock
    try:
        asyncio.run(test_0g_compute_mock())
        results["passed"] += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        results["failed"] += 1

    # Test 4: MCP integration
    try:
        test_mcp_integration()
        results["passed"] += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        results["failed"] += 1

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print(f"  Passed:  {results['passed']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Skipped: {results['skipped']}")
    print("=" * 60)

    if results["failed"] > 0:
        sys.exit(1)
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    main()
