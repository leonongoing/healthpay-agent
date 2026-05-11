#!/usr/bin/env python3
"""
Test core HealthPay scenarios with Gemma 4 integration.
Tests the fallback chain: Gemma 4 → 0G → OpenAI
"""
import sys
import asyncio
sys.path.insert(0, 'src')

from zero_g_compute import ZeroGLLM, ZeroGComputeError

# Test prompts for 3 core scenarios
SCENARIOS = {
    "reconciliation": {
        "name": "Claim Reconciliation Analysis",
        "prompt": """Analyze this healthcare claim reconciliation:
- Claim ID: CLM-2024-001
- Billed Amount: $450.00
- Allowed Amount: $320.00
- Paid Amount: $256.00
- Denied Amount: $130.00
- Denial Reason: Exceeds usual and customary charges

Tasks:
1. Calculate the discrepancy between billed and paid
2. Identify root cause of denial
3. Recommend appeal strategy

Respond in JSON format with keys: discrepancy, root_cause, appeal_recommendation"""
    },
    "denial": {
        "name": "Denial Classification",
        "prompt": """Classify these insurance claim denials:

Case 1:
- Amount: $2,500
- Service: Surgical procedure
- CARC Code: 197 (No prior authorization)
- Days since denial: 12

Case 2:
- Amount: $800
- Service: Laboratory tests
- CARC Code: 18 (Duplicate claim)
- Days since denial: 45

Case 3:
- Amount: $15,000
- Service: Inpatient stay
- CARC Code: 50 (Medical necessity not established)
- Days since denial: 5

For each case, provide:
- Category (administrative/clinical/technical)
- Priority (high/medium/low)
- Recovery estimate (%)
- Recommended strategy

Respond in JSON format."""
    },
    "report": {
        "name": "Financial Report Generation",
        "prompt": """Generate a Financial Vital Signs report from this data:

Revenue Metrics:
- Total Billed: $625,000
- Total Collected: $503,000
- Outstanding AR: $350,000

Aging Buckets:
- 0-30 days: $125,000
- 31-60 days: $85,000
- 61-90 days: $45,000
- 91-120 days: $30,000
- 120+ days: $65,000

Denial Rates by Payer:
- BlueCross: 8%
- United Healthcare: 15%
- Medicare: 5%
- Medicaid: 22%

Provide:
1. Collection rate (%)
2. Days in AR
3. Top 3 recommendations
4. Payer risk ranking

Respond in JSON format."""
    }
}

async def test_scenario(llm: ZeroGLLM, scenario_name: str, scenario_data: dict):
    """Test a single scenario."""
    print(f"\n{'='*60}")
    print(f"Testing: {scenario_data['name']}")
    print(f"{'='*60}")
    
    try:
        response = await llm.chat_completion(
            messages=[{"role": "user", "content": scenario_data["prompt"]}],
            stream=False,
            temperature=0.3,
            max_tokens=2048
        )
        
        provider = llm.get_active_provider()
        content = response.choices[0].message.content
        
        print(f"✅ Success using provider: {provider}")
        print(f"   Response length: {len(content)} chars")
        print(f"   Has JSON: {'Yes' if '{' in content and '}' in content else 'No'}")
        print(f"   Preview: {content[:200]}...")
        
        return {
            "scenario": scenario_name,
            "success": True,
            "provider": provider,
            "response_length": len(content),
            "has_json": '{' in content and '}' in content
        }
        
    except ZeroGComputeError as e:
        print(f"❌ All providers failed: {str(e)[:200]}")
        return {
            "scenario": scenario_name,
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {
            "scenario": scenario_name,
            "success": False,
            "error": str(e)
        }

async def main():
    print("="*60)
    print("HealthPay Agent — Core Scenarios Test")
    print("Testing Gemma 4 → 0G → OpenAI fallback chain")
    print("="*60)
    
    llm = ZeroGLLM()
    results = []
    
    for scenario_name, scenario_data in SCENARIOS.items():
        result = await test_scenario(llm, scenario_name, scenario_data)
        results.append(result)
    
    await llm.close()
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    success_count = sum(1 for r in results if r.get("success"))
    print(f"Passed: {success_count}/{len(results)}")
    
    if success_count == 0:
        print("\n⚠️  No API keys configured. This is expected.")
        print("   To test with real API:")
        print("   1. Get Gemini API key: https://aistudio.google.com/apikey")
        print("   2. Set: export GEMINI_API_KEY=your_key")
        print("   3. Run: python scripts/test_core_scenarios.py")
    else:
        for r in results:
            if r.get("success"):
                print(f"  ✅ {r['scenario']}: {r['provider']}")
            else:
                print(f"  ❌ {r['scenario']}: {r.get('error', 'Unknown error')[:50]}")

if __name__ == "__main__":
    asyncio.run(main())
