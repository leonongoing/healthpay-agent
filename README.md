# HealthPay Reconciliation Agent 🏥💰

> AI-powered healthcare payment reconciliation via FHIR R4 — with verifiable audit trails on [0G Network](https://0g.ai/).
>
> 🏆 Built for the [0G APAC Hackathon](https://0g.ai/) (Verifiable Finance Track) and [Agents Assemble Hackathon](https://agents-assemble.devpost.com/)

## The Problem

Healthcare organizations in the US lose **$262 billion annually** to administrative waste. A major contributor: the painful, manual process of reconciling medical claims against insurance payments. Staff spend hours cross-referencing Explanation of Benefits (EOBs) with submitted claims, chasing denials, and guessing which claims need attention first.

## The Solution

**HealthPay** is an MCP (Model Context Protocol) server that connects to any FHIR R4-compliant EHR system and provides AI-powered financial intelligence tools. It turns raw claims data into actionable insights — automatically.

### What It Does

| Tool | Description |
|------|-------------|
| `reconcile_claims` | Matches Claims against EOBs, identifies denials, partial payments, and overpayments |
| `analyze_denials` | Classifies denial root causes (CARC codes), generates prioritized appeal strategies with estimated recovery. **Phase 3:** Enhanced with Gemma 4 for deep medical reasoning and appeal letter generation |
| `generate_ar_report` | Produces Financial Vital Signs dashboard — aging buckets, collection rates, payer performance. **Phase 3:** Enhanced with Gemma 4 for trend analysis and actionable insights |
| `predict_payment_risk` | Scores claims by payment probability using payer history, claim type, and amount patterns |
| `suggest_coding_optimization` | Identifies ICD-10/CPT coding issues that cause denials — specificity, modifiers, documentation gaps |
| `check_compliance` | **Phase 3 NEW:** Validates HIPAA compliance, code formats (CPT/ICD-10/HCPCS), and documentation completeness. Enhanced with Gemma 4 for diagnosis-procedure code pairing analysis |

### Financial Vital Signs (Sample Output)

```
Total Billed:      $1,006,189.62
Total Collected:   $  749,476.36
Total Outstanding: $  256,713.26
Collection Rate:          74.5%
Clean Claim Rate:         50.3%
Denial Rate:              45.6%

A/R Aging:
  0-30 days:   $      0.00 (  0.0%)
  31-60 days:  $    364.23 (  0.1%)
  120+ days:   $309,928.12 ( 99.9%) ████████████████████████
```

## 0G Integration

HealthPay integrates **two** 0G core components for verifiable healthcare finance:

### 0G Storage — Immutable Audit Trails
Every reconciliation result is uploaded to 0G decentralized storage via `src/zero_g_storage.py`. The Merkle root hash provides cryptographic proof of data integrity — auditors can independently verify any result.

### 0G Compute — Verifiable AI Inference
AI-powered denial analysis and risk prediction run on 0G's decentralized compute network via `src/zero_g_compute.py` (using `python-0g` SDK). Execution attestation proves the model actually processed the data.

### Setup

#### Prerequisites
- Python 3.11+
- Ethereum wallet with testnet tokens from https://faucet.0g.ai

#### Install Dependencies

```bash
# Python dependencies (includes python-0g)
pip install -r requirements.txt
```

#### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# 0G Storage
ZG_PRIVATE_KEY=0x_your_ethereum_private_key_here

# 0G Compute
ZG_COMPUTE_PRIVATE_KEY=0x_your_ethereum_private_key_here
ZG_COMPUTE_MODEL=Qwen/Qwen2.5-7B-Instruct

# Fallback (when 0G unavailable)
OPENAI_API_KEY=sk-your-openai-key-here
```

**Note:** You can use the same private key for both `ZG_PRIVATE_KEY` and `ZG_COMPUTE_PRIVATE_KEY`.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HealthPay MCP Server                      │
│                      (Python 3.11+)                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Reconciler   │  │ Denial       │  │ Risk         │      │
│  │              │  │ Analyzer     │  │ Predictor    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │              │
│  ┌──────▼─────────────────▼──────────────────▼──────────┐   │
│  │           FHIR R4 Client (httpx async)               │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │         SHARP Context Propagation                    │   │
│  │   (patient_id + FHIR URL + access_token)             │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────┬──────────────────┬──────────────────────────────┘
             │                  │
     ┌───────▼───────┐  ┌──────▼────────┐
     │  0G Storage   │  │  0G Compute   │
     │               │  │               │
     │ • Upload via  │  │ • Service     │
     │   python-0g   │  │   discovery   │
     │ • Merkle root │  │ • LLM         │
     │   hash return │  │   inference   │
     │               │  │ • Attestation │
     └───────┬───────┘  └──────┬────────┘
             │                  │
     ┌───────▼──────────────────▼────────┐
     │    0G Decentralized Network       │
     │      (Testnet / Mainnet)          │
     └───────────────────────────────────┘
             │
     ┌───────▼───────┐
     │  HAPI FHIR R4 │
     │  Server       │
     │  (Docker)     │
     └───────────────┘
```

### How It Works

#### 0G Storage Flow

1. **Reconciliation** — Agent processes Claims vs EOBs
2. **Serialization** — Results converted to JSON
3. **Upload** — `python-0g` (A0G client) uploads to 0G Storage network
4. **Hash Return** — Merkle root hash returned (66-char hex string)
5. **Storage** — Hash stored alongside reconciliation result

```python
# Example usage
from src.zero_g_storage import upload_to_0g

root_hash = upload_to_0g(
    data={"patient_id": "1617", "total_billed": 324000},
    filename="reconciliation_1617.json"
)
# Returns: "0x7a3f8b2c...e91b" (66-char hex string)
```

#### 0G Compute Flow

1. **Prompt Preparation** — Denial analyzer structures prompt with CARC codes
2. **Client Init** — `ZeroGLLM` connects to 0G Compute network via `python-0g`
3. **Service Discovery** — SDK discovers available compute providers
4. **Inference** — LLM processes prompt on decentralized nodes
5. **Attestation** — Response includes execution proof
6. **Fallback** — Automatic OpenAI fallback if 0G unavailable

```python
# Example usage
from src.zero_g_compute import ZeroGLLM

llm = ZeroGLLM(model="Qwen/Qwen2.5-7B-Instruct")
response = await llm.chat_completion(
    messages=[{"role": "user", "content": "Analyze this denial..."}],
    temperature=0.3
)
```

### Enable/Disable 0G Features

#### Disable 0G Storage (use mock hashes)
```bash
# Remove or comment out in .env
# ZG_PRIVATE_KEY=...
```

When `ZG_PRIVATE_KEY` is not set, the system generates deterministic mock hashes prefixed with `0xMOCK_`. All other functionality works normally.

#### Disable 0G Compute (use OpenAI fallback)
```bash
# Remove or comment out in .env
# ZG_COMPUTE_PRIVATE_KEY=...

# Ensure OpenAI key is set
OPENAI_API_KEY=sk-your-key-here
```

When `ZG_COMPUTE_PRIVATE_KEY` is not set, the system automatically falls back to OpenAI's API.

#### Disable Both (development mode)
```bash
# .env file with no 0G credentials
OPENAI_API_KEY=sk-your-key-here
```

The agent works fully in development mode with mock storage and OpenAI inference.

### Testing

Run the integration test suite:

```bash
# Basic test (mock mode, no credentials needed)
python scripts/test_0g_integration.py

# Expected output:
# ✅ Test 1: 0G Storage Upload (Mock Mode) — PASSED
# ✅ Test 2: 0G Storage Download (Mock Mode) — PASSED
# ⏭️  Test 3: 0G Storage Real Upload — SKIPPED (no credentials)
# ✅ Test 4: 0G Compute Client Init — PASSED
# ⏭️  Test 5: 0G Compute Real Inference — SKIPPED (no credentials)
```

With 0G credentials configured:

```bash
# Set credentials
export ZG_PRIVATE_KEY=0x...
export ZG_COMPUTE_PRIVATE_KEY=0x...

# Run full test
python scripts/test_0g_integration.py

# Expected: Tests 1-5 PASSED (Test 6 may fail if mcp not installed)
```

### Troubleshooting

#### Error: "python-0g not installed"

**Solution:**
```bash
pip install python-0g>=0.6.1
```

#### Error: "ZG_PRIVATE_KEY not set"

**Solution:**
```bash
# Add to .env file
ZG_PRIVATE_KEY=0x_your_private_key_here
```

#### Error: "0G Storage upload failed: insufficient funds"

**Cause:** Wallet has no testnet tokens.

**Solution:**
1. Visit https://faucet.0g.ai
2. Enter your wallet address
3. Request 0.1 0G tokens
4. Wait 1-2 minutes for confirmation

#### Error: "0G Compute: no providers found"

**Cause:** 0G Compute network unavailable or wrong network configured.

**Solution:**
- Verify testnet tokens in wallet
- Wait 5-10 minutes and retry
- Use OpenAI fallback if urgent

#### Slow 0G Compute inference (>30s)

**Solution:**
- Use `temperature=0.3` for faster inference
- Reduce `max_tokens` if possible
- Consider OpenAI fallback for time-sensitive operations

### Performance

| Operation | 0G Network | Fallback | Notes |
|-----------|------------|----------|-------|
| Storage upload | 5-15s | N/A | Includes Merkle tree generation |
| Storage download | 2-5s | N/A | Direct indexer query |
| Compute inference | 8-20s | 2-5s | Depends on model and prompt length |
| Hash generation | <1s | <1s | Deterministic, local computation |

### Security

- **Private keys** are never logged or transmitted in plaintext
- **0G Compute** runs in isolated execution environments
- **Fallback mode** uses OpenAI's API with standard TLS encryption
- **Mock mode** generates deterministic hashes from SHA-256 (no network calls)

### Mainnet Deployment

To deploy on 0G Mainnet:

1. Update network in `.env`:
```bash
ZG_NETWORK=mainnet
ZG_COMPUTE_NETWORK=mainnet
```

2. Fund your wallet with mainnet 0G tokens

3. Test with small uploads first

## Tech Stack

- **Python 3.11+** — Core language
- **MCP SDK** — Model Context Protocol server implementation
- **HAPI FHIR R4** — FHIR-compliant healthcare data server (Docker)
- **Synthea** — Synthetic patient data generation (59 patients, 8000+ claims)
- **python-0g** (`DormintLab/python-0g`) — 0G Storage + Compute SDK
- **Pydantic** — Data validation and serialization
- **httpx** — Async HTTP client for FHIR API

## FHIR Resources Used

| Resource | Purpose |
|----------|---------|
| `Patient` | Patient demographics |
| `Claim` | Medical bills submitted to payers |
| `ExplanationOfBenefit` | Insurance adjudication results |
| `Coverage` | Insurance coverage details |
| `Organization` | Payers and providers |

## SHARP Integration

HealthPay uses the SHARP Extension Specs for healthcare context propagation:

```python
{
    "patient_id": "1617",
    "fhir_server_url": "http://...",
    "fhir_access_token": "Bearer ..."
}
```

Every tool accepts SHARP context, enabling seamless integration within the Prompt Opinion platform's multi-agent ecosystem.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (for HAPI FHIR server)
- Java 11+ (for Synthea data generation)

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd healthpay-agent

# Start FHIR server
docker run -d --name healthpay-fhir -p 19911:8080 \
  -e hapi.fhir.fhir_version=R4 hapiproject/hapi:latest

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Generate and import synthetic data
cd synthea && bash ../scripts/install_synthea.sh
bash ../scripts/generate_data.sh
python ../scripts/import_to_fhir.py

# Configure 0G (optional)
cp .env.example .env
# Edit .env with your credentials

# Run MCP server
python -m src
```

### Test a Tool

```python
import asyncio
from src.fhir_client import FHIRClient
from src.reconciler import reconcile

async def demo():
    fhir = FHIRClient(base_url="http://localhost:19911/fhir")
    claims = await fhir.get_claims("1617")
    eobs = await fhir.get_eobs("1617")
    result = reconcile(patient_id="1617", claims=claims, eobs=eobs)
    print(f"Matched: {result.summary['matched_count']}")
    print(f"Discrepancies: {result.summary['discrepancy_count']}")
    await fhir.close()

asyncio.run(demo())
```


## Phase 3: Gemma 4 Integration 🧠

> **Hackathon:** [Gemma 4 Good](https://www.kaggle.com/competitions/gemma-4-good) ($200K, Google DeepMind + Kaggle)  
> **Track:** Health & Sciences ($10K track prize)  
> **Status:** ✅ Completed (2026-04-20)

HealthPay Agent now leverages **Gemma 4's medical domain knowledge** to provide deeper insights and more accurate recommendations.

### What's New

#### 1. Enhanced Denial Analyzer
- **Deep Root Cause Analysis**: Uses Gemma 4's medical knowledge to identify specific documentation gaps and coding errors
- **Personalized Appeal Letters**: Generates draft appeal letters with evidence-based arguments
- **Evidence Recommendations**: Suggests specific clinical documentation to gather
- **Recovery Probability**: Estimates realistic recovery probability (0-100%)

```python
# Enable Gemma 4 enhancement
{
  "name": "analyze_denials",
  "arguments": {
    "patient_id": "patient-001",
    "use_gemma4": true  # ← New parameter
  }
}
```

#### 2. Enhanced A/R Reporter
- **Trend Analysis**: Identifies improving/declining metrics with percentage changes
- **Benchmark Comparisons**: Compares against industry standards (e.g., 35 days in A/R)
- **Visualization Recommendations**: Suggests chart types (line, bar, pie) for tracking metrics
- **Actionable Insights**: Generates prioritized action items with expected impact and timeline
- **Executive Summary**: 2-3 sentence summary for leadership

```python
# Enable Gemma 4 enhancement
{
  "name": "generate_ar_report",
  "arguments": {
    "date_from": "2026-03-01",
    "use_gemma4": true  # ← New parameter
  }
}
```

#### 3. New Compliance Checker Tool
- **HIPAA Compliance**: Validates required fields per 45 CFR Parts 160, 162, 164
- **Code Format Validation**: Checks CPT (5 digits), ICD-10 (letter + digits), HCPCS (letter + 4 digits)
- **Documentation Scoring**: 0-100 score based on completeness of required fields
- **Gemma 4 Enhancement**: Validates diagnosis-procedure code pairing and identifies coding errors

```python
# New tool
{
  "name": "check_compliance",
  "arguments": {
    "claim_id": "claim-001",
    "use_gemma4": true  # ← Optional enhancement
  }
}
```

### Gemma 4 Setup

```bash
# Install Gemma 4 client
pip install google-genai

# Get API key from https://aistudio.google.com/apikey
export GEMINI_API_KEY="your_key_here"

# Optional configuration
export GEMMA4_MODEL="gemma-4-27b-it"  # Default model
export GEMMA4_TEMPERATURE="0.3"       # Low temp for medical accuracy
export GEMMA4_MAX_TOKENS="4096"       # Max output tokens
```

### Backward Compatibility

All Gemma 4 enhancements are **opt-in** via `use_gemma4` parameter:
- **Without Gemma 4** (default): Tools work as before using rule-based logic
- **With Gemma 4**: Enhanced analysis with medical reasoning and personalized recommendations

If Gemma 4 is unavailable (no API key, network error), tools gracefully fall back to base implementation.

### Performance

| Tool | Base (ms) | Enhanced (ms) | Overhead |
|------|-----------|---------------|----------|
| Denial Analyzer | 50 | 2,500 | +2,450ms |
| A/R Reporter | 100 | 2,800 | +2,700ms |
| Compliance Checker | 30 | 2,200 | +2,170ms |

**Note:** Enhanced tools make 1 LLM API call per analysis. Latency depends on Gemini API response time (~2-3 seconds).

### Documentation

- **Phase 3 Enhancements**: `docs/phase3-enhancements.md` — Detailed technical documentation
- **Integration Plan**: `docs/gemma4-integration-plan.md` — Original integration plan and evaluation
- **Tests**: `tests/test_enhanced_tools.py` — Comprehensive test suite

### Why Gemma 4?

1. **Medical Domain Knowledge**: Pre-trained on medical literature and coding standards
2. **256K Context Window**: Processes large claim datasets with full context
3. **Thinking Mode**: Complex medical billing logic requires multi-step reasoning
4. **Cost-Effective**: Free tier (15 RPM, 1M TPM) sufficient for demo
5. **Open Source**: Apache 2.0 license, can be self-hosted

### Hackathon Differentiation

- **Real Healthcare Problem**: Solves $262B administrative waste problem
- **FHIR R4 Standard**: Interoperable with any EHR system
- **0G Blockchain**: Immutable audit trail for compliance
- **Gemma 4 Integration**: Deep medical reasoning, not just text generation
- **Production-Ready**: Backward compatible, graceful degradation, comprehensive tests

## Why This Matters

1. **Real Pain Point** — US healthcare billing is broken. $262B wasted annually on admin.
2. **AI Where It Counts** — Not replacing clinicians, but automating financial drudgery.
3. **Standards-First** — Built on FHIR R4, MCP, and SHARP. No vendor lock-in.
4. **Actionable Output** — Every tool produces specific, prioritized recommendations with dollar amounts.
5. **Privacy-Safe** — Uses only synthetic data. No PHI. No clinical decisions.
6. **Verifiable** — 0G Storage provides immutable audit trails; 0G Compute provides verifiable AI inference.

## Judging Criteria Alignment

- **The AI Factor**: AI-powered denial classification, risk prediction, and coding optimization go far beyond rule-based systems.
- **Potential Impact**: Addresses a $262B problem. Every healthcare org needs better payment reconciliation.
- **Feasibility**: Uses established standards (FHIR R4, MCP). Respects data privacy (synthetic data only). No clinical risk.

## License

Apache 2.0 — See [LICENSE](LICENSE)

## Team

Built by Leon Huang — fintech CTO with 10+ years in payment systems, now applying that expertise to healthcare finance + decentralized infrastructure (0G Network).
