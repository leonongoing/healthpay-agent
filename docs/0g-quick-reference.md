# 0G Integration Quick Reference

## SDK Versions
- **0G Storage:** `@0gfoundation/0g-ts-sdk` v1.2.1 (npm)
- **0G Compute:** `python-0g` v0.6.1.2 (PyPI)

## Testnet Endpoints
```bash
# 0G Storage
ZG_EVM_RPC=https://evmrpc-testnet.0g.ai
ZG_INDEXER_RPC=https://indexer-storage-testnet-turbo.0g.ai

# 0G Compute
A0G_RPC_URL=https://evmrpc-testnet.0g.ai
```

## Quick Start

### 0G Storage (Upload)
```bash
cd /home/taomi/projects/healthpay-agent/scripts
node 0g-bridge.js upload /path/to/file.json
# Returns: {"rootHash": "0xabc123...", "txHash": "0xdef456..."}
```

### 0G Compute (AI Inference)
```python
from a0g import A0G

client = A0G(private_key="0x...", network="testnet")
services = client.get_all_services()
provider = services[0].provider

openai_client = client.get_openai_client(provider)
response = openai_client.chat.completions.create(
    model="qwen/qwen-2.5-7b-instruct",
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Files Modified
- ✅ `scripts/package.json` — Updated to `@0gfoundation/0g-ts-sdk`
- ✅ `scripts/0g-bridge.js` — Updated import statement
- ⏱️ `src/zero_g_compute.py` — Needs import fix (zerog → a0g.A0G)
- ⏱️ `requirements.txt` — Needs python-0g added

## Get Testnet Tokens
1. Visit: https://faucet.0g.ai
2. Enter your Ethereum address
3. Request 0.1 0G (daily limit)
4. Wait ~1 minute for confirmation

## Test Commands
```bash
# Test 0G Storage SDK
cd scripts && node -e "const {ZgFile} = require('@0gfoundation/0g-ts-sdk'); console.log('OK');"

# Test python-0g
cd .. && source venv/bin/activate && python -c "from a0g import A0G; print('OK')"

# Run integration test
python scripts/test_0g_integration.py
```

## Troubleshooting

### "Module not found: @0glabs/0g-ts-sdk"
→ Run: `cd scripts && npm install`

### "No module named 'zerog'"
→ Fix: Change `import zerog` to `from a0g import A0G` in `src/zero_g_compute.py`

### "Private key is required"
→ Set: `export ZG_PRIVATE_KEY=0x...` or `export A0G_PRIVATE_KEY=0x...`

### "No 0G Compute providers available"
→ Check: Network connection, RPC URL, testnet status

## Cost Estimates (Testnet)
- **Storage upload:** ~0.001 0G (~$0.001)
- **AI inference:** ~0.0002 0G per request (~$0.0002)
- **Monthly (1000 ops):** ~$0.20-1.00

## Links
- Docs: https://docs.0g.ai
- Faucet: https://faucet.0g.ai
- Storage SDK: https://github.com/0gfoundation/0g-ts-sdk
- Compute marketplace: https://compute-marketplace.0g.ai
