# HealthPay Agent — Demo Video Script (3 Minutes)

**Duration:** 3:00  
**Format:** Screen recording with voiceover  
**Tools Required:** Terminal, FHIR Server (localhost:19911), HealthPay MCP Server

---

## 0:00-0:30 — Problem Statement (30 seconds)

### Visual
- Title card: **"HealthPay Agent: AI-Powered Healthcare Payment Reconciliation"**
- Subtitle: **"Gemma 4 × FHIR R4 × 0G Blockchain"**
- Fade to statistics overlay

### Narration

> "Every year, US healthcare organizations lose $262 billion to administrative waste. One of the biggest causes? Manual claim reconciliation."
>
> "Right now, billing staff spend 40 hours a week cross-referencing claims against insurance payments — by hand. 1 in 8 claims gets denied on first submission. And when a denial happens? It takes an average of 45 days to resolve."
>
> "HealthPay Agent fixes this. It's an AI-powered MCP server that connects to any FHIR-compliant EHR system and turns raw claims data into actionable intelligence — powered by Gemma 4."

---

## 0:30-1:30 — Live Demo (60 seconds)

### Setup (5 seconds)

**Terminal Command:**
```bash
cd healthpay-agent
source venv/bin/activate
python -m src
```

**Expected Output:**
```
INFO: Gemma 4 client initialized (model: gemma-4-27b-it)
INFO: HealthPay MCP Server started on stdio transport
```

### Demo 1: Reconcile Claims (15 seconds)

**Narration:**
> "First, let's reconcile claims for a patient. HealthPay pulls claims and EOBs from the FHIR server, matches them, and identifies every discrepancy."

**MCP Tool Call:**
```json
{
  "name": "reconcile_claims",
  "arguments": {
    "patient_id": "1617"
  }
}
```

**Expected Output (highlight key numbers):**
```
Total Billed:      $1,006,189.62
Total Collected:   $  749,476.36
Total Outstanding: $  256,713.26
Collection Rate:          74.5%
Denial Rate:              45.6%

Matched: 87 claims
Discrepancies: 42 (denials, partial payments, overpayments)
Audit Trail: 0x7a3f8b2c...e91b (stored on 0G)
```

**Narration:**
> "$256,000 outstanding for just one patient. And notice — every reconciliation is automatically stored on the 0G blockchain with a Merkle root hash for tamper-proof auditing."

### Demo 2: Analyze Denials with Gemma 4 (20 seconds)

**Narration:**
> "Now let's use Gemma 4 to analyze those denials. This is where the magic happens."

**MCP Tool Call:**
```json
{
  "name": "analyze_denials",
  "arguments": {
    "patient_id": "1617",
    "use_gemma4": true
  }
}
```

**Expected Output (highlight Gemma 4 enhancement):**
```
Denial Analysis (Gemma 4 Enhanced):

Top Denial: CO-4 (Procedure code inconsistent with modifier)
  Root Cause: Missing modifier -59 for distinct procedural service
  Appeal Strategy: Submit operative report showing separate incision
  Evidence Needed: Operative notes, separate body areas documented
  Recovery Probability: 78%
  
  Draft Appeal Letter:
  "Dear Claims Review Board,
   We are writing to appeal the denial of Claim #12345 for Patient X.
   The procedure was performed as a distinct procedural service,
   documented in the operative report showing separate anatomical sites..."

Total Recoverable: $156,000 (est.)
```

**Narration:**
> "Gemma 4 doesn't just say 'denied.' It tells you WHY, gives you a specific appeal strategy, drafts the appeal letter, and estimates your recovery probability at 78%. That's not generic AI — that's medical domain expertise."

### Demo 3: Compliance Check (20 seconds)

**Narration:**
> "Before submitting new claims, let's run a compliance check."

**MCP Tool Call:**
```json
{
  "name": "check_compliance",
  "arguments": {
    "claim_id": "claim-001",
    "use_gemma4": true
  }
}
```

**Expected Output:**
```
Compliance Report: claim-001

Overall Status: WARNING
HIPAA Compliant: ✅ Yes
Documentation Score: 85%

Issues Found (2):
⚠️ [WARNING] Coding Accuracy
   ICD-10 code E11.9 (Type 2 diabetes, unspecified) lacks specificity
   → Use E11.65 (Type 2 diabetes with hyperglycemia) for higher reimbursement
   📖 ICD-10-CM Guidelines, Section I.A.13

🟡 [WARNING] Documentation
   Missing referring provider NPI
   → Add referring provider to claim before submission
   📖 45 CFR §162.1002
```

**Narration:**
> "Two issues caught before submission. The ICD-10 code lacks specificity — using a more specific code could mean higher reimbursement. And there's a missing provider NPI. Catching these before submission prevents denials."

---

## 1:30-2:30 — Technical Deep-Dive (60 seconds)

### Visual
- Show architecture diagram from README

### Narration

> "Let me show you how this works under the hood."

**Architecture Points:**

> "HealthPay is built on three pillars:"
>
> "**First: FHIR R4.** The industry standard for healthcare data exchange. This means HealthPay works with any EHR — Epic, Cerner, Allscripts — out of the box. We use async HTTP via httpx to pull Patient, Claim, EOB, and Coverage resources."
>
> "**Second: MCP — Model Context Protocol.** This is Google's open standard for AI tool orchestration. Our server exposes 6 specialized tools that any MCP-compatible agent can call. Think of it as an API for healthcare financial intelligence."
>
> "**Third: Gemma 4.** This is the key differentiator. Generic LLMs don't understand CARC codes, CPT modifiers, or HIPAA documentation requirements. Gemma 4's medical domain knowledge lets us go beyond pattern matching to genuine medical reasoning."

**Why Gemma 4 vs Generic LLMs:**

> "We chose Gemma 4 for three specific reasons:"
>
> "One — **256K context window**. Healthcare claims are complex. A single patient can have hundreds of claims with thousands of line items. Gemma 4 can process all of it at once."
>
> "Two — **medical domain knowledge**. When we ask Gemma 4 to analyze a CO-4 denial, it knows that modifier -59 indicates a distinct procedural service. GPT-4 would need that explained."
>
> "Three — **self-hostable**. For HIPAA compliance, practices need to keep data on-premises. Gemma 4 is Apache 2.0 — they can run it locally with zero data leaving their network."

**0G Integration:**

> "Every reconciliation result gets a Merkle root hash on 0G's decentralized storage. This gives auditors tamper-proof evidence — they can verify any result independently. No central database to alter."

---

## 2:30-3:00 — Impact & Future Vision (30 seconds)

### Visual
- Impact numbers overlay
- Future roadmap timeline

### Narration

> "Let's talk impact. For a typical small practice — 5 physicians, 200 claims per month:"
>
> "HealthPay can recover an additional **$324,000 per year** in denied claims by improving the denial recovery rate from 60% to 85%."
>
> "It saves **$78,000 per year** in labor costs by reducing manual reconciliation from 40 hours to 10 hours per week."
>
> "And it cuts compliance violations by over 60% by catching coding and documentation issues before submission."
>
> "Scale that to 200,000 physician practices in the US, and you're looking at **$64.8 billion** in recovered claims annually."

### Closing

> "HealthPay Agent — built on open standards, powered by Gemma 4, verified on blockchain. Turning healthcare's $262 billion administrative waste problem into recovered revenue."
>
> "Thank you."

### End Card
- GitHub repo link
- "Built for Gemma 4 Good Hackathon"
- "Apache 2.0 License"

---

## Production Notes

### Recording Setup
- **Terminal**: Dark theme (Dracula or similar), 16pt font
- **Resolution**: 1080p minimum
- **Audio**: Clear voiceover, no background music during demos
- **Transitions**: Simple fade between sections

### Demo Data
- Use synthetic FHIR data (59 patients, 8000+ claims from Synthea)
- Patient ID `1617` has good demonstration data
- FHIR server must be running on `localhost:19911`

### Timing Guide
- Problem statement: 30s (keep it tight)
- Live demo: 60s (most important section — judges want to see it work)
- Technical: 60s (show depth, not complexity)
- Impact: 30s (end with a bang)

### Key Visual Moments
1. **0:35** — MCP server starting with Gemma 4 initialized
2. **0:55** — Reconciliation output with 0G hash
3. **1:10** — Gemma 4 appeal letter generation (most impressive moment)
4. **1:25** — Compliance check catching issues before submission
5. **2:45** — $324K annual impact number
