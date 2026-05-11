#!/usr/bin/env python3
"""
Gemma 4 Integration Test for HealthPay Agent
Tests Gemma 4 via Google AI Studio (Gemini API) for healthcare tasks.
"""
import os, sys, json, time

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

GEMMA4_MODELS = ["gemma-4-27b-it", "gemma-4-31b-it", "gemma-4-26b-a4b-it", "gemma-4-12b-it"]

RECONCILIATION_PROMPT = """You are a healthcare financial analyst. Analyze this claim:
- Claim ID: CLM-2024-001, Billed: $450.00, Allowed: $320.00, Paid: $256.00
- Denied: $130.00 (exceeds usual/customary charges)
Tasks: 1) Calculate discrepancy 2) Root cause 3) Appeal recommendation
Respond in JSON format."""

DENIAL_PROMPT = """Classify these denials:
Case 1: $2500 surgical, CARC 197 (no prior auth), 12 days old
Case 2: $800 lab, CARC 18 (duplicate), 45 days old
Case 3: $15000 inpatient, CARC 50 (medical necessity), 5 days old
For each: category, priority, recovery estimate, strategy. JSON format."""

REPORT_PROMPT = """Generate Financial Vital Signs from:
- Total Billed: $625K, Collected: $503K, Outstanding: $350K
- Aging: 0-30d $125K, 31-60d $85K, 61-90d $45K, 91-120d $30K, 120+d $65K
- Denial rates: BlueCross 8%, United 15%, Medicare 5%, Medicaid 22%
Provide: collection rate, recommendations, payer risk ranking. JSON format."""

def find_model(client):
    try:
        for m in client.models.list():
            name = getattr(m, 'name', str(m))
            if 'gemma-4' in name.lower() or 'gemma4' in name.lower():
                n = name.split('/')[-1] if '/' in name else name
                print(f"  Found: {n}")
                return n
    except Exception as e:
        print(f"  List failed: {e}")
    for mn in GEMMA4_MODELS:
        try:
            r = client.models.generate_content(model=mn, contents="Say OK", config={"max_output_tokens": 10})
            if r and r.text:
                print(f"  ✅ {mn} works")
                return mn
        except Exception as e:
            print(f"  ❌ {mn}: {e}")
    return None

def test_task(client, model, name, prompt):
    start = time.time()
    try:
        r = client.models.generate_content(model=model, contents=prompt, config={"temperature": 0.3, "max_output_tokens": 2048})
        ms = round((time.time() - start) * 1000)
        if r and r.text:
            text = r.text
            has_json = '{' in text and '}' in text
            length = len(text)
            print(f"  ✅ {name}: {ms}ms, {length} chars, JSON={'Y' if has_json else 'N'}")
            return {"task": name, "ok": True, "ms": ms, "len": length, "json": has_json, "preview": text[:500]}
        return {"task": name, "ok": False, "ms": ms, "error": "empty"}
    except Exception as e:
        ms = round((time.time() - start) * 1000)
        print(f"  ❌ {name}: {e}")
        return {"task": name, "ok": False, "ms": ms, "error": str(e)}

def main():
    if not HAS_GENAI:
        print("❌ pip install google-genai"); sys.exit(1)
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("❌ Set GEMINI_API_KEY"); sys.exit(1)
    
    print("=" * 50)
    print("🏥 HealthPay — Gemma 4 Test")
    print("=" * 50)
    
    client = genai.Client(api_key=key)
    model = find_model(client)
    if not model:
        print("❌ No Gemma 4 model available"); sys.exit(1)
    
    print(f"\nUsing: {model}\n")
    results = []
    for name, prompt in [("Reconciliation", RECONCILIATION_PROMPT), ("Denial Classification", DENIAL_PROMPT), ("Financial Report", REPORT_PROMPT)]:
        results.append(test_task(client, model, name, prompt))
    
    ok = sum(1 for r in results if r["ok"])
    avg_ms = sum(r["ms"] for r in results if r["ok"]) / max(ok, 1)
    print(f"\n{'='*50}")
    print(f"Results: {ok}/3 passed, avg {avg_ms:.0f}ms")
    
    out = {"model": model, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "passed": ok, "results": results}
    with open("/tmp/gemma4_test_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Saved: /tmp/gemma4_test_results.json")

if __name__ == "__main__":
    main()
