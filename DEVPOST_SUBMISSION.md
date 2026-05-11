# Devpost Submission Draft — HealthPay Reconciliation Agent

## Project Name
HealthPay — AI-Powered Healthcare Payment Reconciliation Agent

## Tagline
Turn $262B in healthcare admin waste into actionable financial intelligence — automatically.

## Inspiration
Working in fintech payment systems for 10+ years, I've seen how reconciliation automation transforms businesses. Healthcare is the last major industry still doing this manually. When I saw the Agents Assemble challenge, I knew the intersection of payment expertise and FHIR standards could create something genuinely useful.

## What it does
HealthPay is an MCP server that connects to FHIR R4 systems and provides 5 AI-powered financial intelligence tools:

1. **Claim Reconciliation** — Automatically matches Claims against EOBs, identifying denials ($45K), partial payments ($60K gap), and overpayments
2. **Denial Analysis** — Classifies denial root causes using CARC codes, generates prioritized appeal strategies with estimated recovery ($33.7K potential)
3. **Financial Vital Signs** — A/R aging dashboard, collection rates, payer performance metrics
4. **Payment Risk Prediction** — Scores claims by payment probability before submission (12 high-risk claims flagged proactively)
5. **Coding Optimization** — Identifies ICD-10/CPT coding issues that cause denials (56 optimization opportunities found)

## How I built it
- **MCP SDK** for the server framework — 5 tools exposed via Model Context Protocol
- **HAPI FHIR R4** server (Docker) with **Synthea**-generated synthetic data (59 patients, 8,041 claims)
- **SHARP Extension Specs** for healthcare context propagation (patient_id, FHIR URL, access token)
- **Python 3.11+** with Pydantic for data validation, httpx for async FHIR API calls
- **Prompt Opinion** platform integration for marketplace publishing

Total: 2,220 lines of Python across 11 modules.

## Challenges I ran into
- FHIR's ExplanationOfBenefit resource is complex — adjudication data is nested 4 levels deep with multiple coding systems
- Synthea generates realistic clinical data but limited financial detail in EOBs — had to enrich denial patterns
- Matching Claims to EOBs requires both direct reference matching and fuzzy matching (amount + date proximity) for real-world robustness
- Balancing between rule-based classification (CARC codes) and AI-powered analysis for denial root cause identification

## Accomplishments that I'm proud of
- **$33,700 estimated recovery** identified from just 63 claims for a single patient — extrapolate that across an organization
- **100% claim-to-EOB match rate** using a two-pass matching algorithm (direct reference + fuzzy)
- **Financial Vital Signs** concept — presenting revenue cycle health like clinical vital signs is intuitive for healthcare staff
- Built the entire system in under a week, from FHIR server setup to working MCP tools

## What I learned
- FHIR R4 is remarkably well-designed for financial data — Claim, EOB, and Coverage resources map cleanly to payment reconciliation workflows
- The MCP + SHARP combination makes healthcare AI tools genuinely interoperable — no custom integration needed
- Healthcare billing denial patterns are surprisingly predictable — most denials fall into a small number of categories that can be prevented

## What's next for HealthPay
- **LLM-powered appeal letter generation** — auto-draft appeal letters with supporting evidence
- **Real-time claim scrubbing** — catch coding issues before submission
- **Multi-organization benchmarking** — compare financial vital signs across practices
- **Payer contract analysis** — identify underpayments based on contracted rates
- **Integration with clearinghouses** — real-time claim status tracking

## Built With
python, mcp, fhir, hapi-fhir, synthea, pydantic, httpx, docker, sharp, prompt-opinion

## Try it out
- [GitHub Repository](TBD)
- [Demo Video](TBD)
