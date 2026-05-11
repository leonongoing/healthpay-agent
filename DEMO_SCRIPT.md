# HealthPay Demo Video Script (< 3 minutes)

## Setup
- Terminal with MCP server running
- FHIR server with Synthea data loaded
- Prompt Opinion platform open (if registered)

---

## Scene 1: The Problem (0:00 - 0:20)

**Narration:**
"Healthcare organizations in the US waste $262 billion a year on administrative overhead. One of the biggest pain points? Reconciling thousands of medical claims against insurance payments — manually."

**Visual:** Quick montage of spreadsheets, EOB documents, frustrated billing staff (stock footage or text overlay)

---

## Scene 2: Meet HealthPay (0:20 - 0:40)

**Narration:**
"HealthPay is an MCP server that plugs into any FHIR R4 system and gives you AI-powered financial intelligence — instantly."

**Visual:** Show the MCP server starting up, list of 5 tools appearing

**Command:**
```bash
python -m src
# Show tool list output
```

---

## Scene 3: Reconciliation (0:40 - 1:10)

**Narration:**
"Let's reconcile claims for a patient. HealthPay pulls Claims and EOBs from the FHIR server, matches them automatically, and flags every discrepancy."

**Demo:** Call `reconcile_claims` for patient 1617

**Key output to highlight:**
- 63 claims matched to 63 EOBs
- 22 denials ($45K)
- 37 partial payments ($60K gap)
- Total billed $324K vs paid $222K

**Narration:**
"In seconds, we see 22 denied claims worth $45,000 and 37 partial payments with a $60,000 gap. No spreadsheets. No guessing."

---

## Scene 4: Denial Analysis (1:10 - 1:40)

**Narration:**
"But finding denials is just the start. HealthPay classifies WHY each claim was denied and tells you exactly how to appeal."

**Demo:** Call `analyze_denials` for patient 1617

**Key output to highlight:**
- 15 denials classified (coding_error, eligibility, etc.)
- $33,700 estimated recovery potential
- Per-denial appeal strategy with priority, evidence list, deadlines
- Payer profile: Humana 23.8% denial rate

**Narration:**
"9 coding errors, $33,700 in recoverable revenue, and a specific appeal strategy for each denial — including what evidence to gather and which deadlines to hit."

---

## Scene 5: Financial Vital Signs (1:40 - 2:10)

**Narration:**
"For the big picture, HealthPay generates Financial Vital Signs — like clinical vitals, but for your revenue cycle."

**Demo:** Call `generate_ar_report`

**Key output to highlight:**
- Collection Rate: 74.5%
- Denial Rate: 45.6%
- A/R Aging chart (99.9% in 120+ days)
- Automated recommendations

**Narration:**
"Collection rate 74.5%, denial rate 45.6%, and $310K stuck in claims over 120 days old. The system automatically flags what needs attention first."

---

## Scene 6: Risk & Coding (2:10 - 2:35)

**Narration:**
"HealthPay also predicts which claims are at risk BEFORE they get denied, and suggests coding improvements to prevent future denials."

**Demo:** Quick flash of `predict_payment_risk` output (12 high-risk claims, $324K at risk) and `suggest_coding_optimization` output (56 claims with issues, modifier and documentation patterns)

**Narration:**
"12 high-risk claims flagged proactively. 56 coding optimization opportunities identified. Prevention, not just reaction."

---

## Scene 7: Closing (2:35 - 2:55)

**Narration:**
"HealthPay is built on open standards — FHIR R4, MCP, and SHARP. It works with any compliant EHR system, uses only synthetic data for privacy, and integrates natively with the Prompt Opinion marketplace."

**Visual:** Architecture diagram, FHIR/MCP/SHARP logos

**Narration:**
"Healthcare billing is broken. HealthPay fixes it — one claim at a time."

**Visual:** HealthPay logo + "Built for Agents Assemble 2026"

---

## Recording Notes
- Use asciinema for terminal demos (clean, no typos)
- Keep terminal font large (16pt+)
- Use jq for pretty JSON output
- Total target: 2:45 - 2:55 (under 3 min limit)
- Background music: subtle, professional
