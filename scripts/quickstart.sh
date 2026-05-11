#!/bin/bash
# HealthPay Agent — One-Click Setup & Demo
# Run this script to get the full demo running in ~3 minutes
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FHIR_URL="${FHIR_SERVER_URL:-http://localhost:19911/fhir}"
FHIR_PORT=19911

cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════════════╗"
echo "║  🏥 HealthPay Agent — Quick Setup & Demo     ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Step 1: Check Docker
echo "▶ Step 1: Checking Docker..."
if ! command -v docker &>/dev/null; then
    echo "  ❌ Docker not found. Please install Docker first."
    exit 1
fi

# Step 2: Start FHIR server if not running
echo "▶ Step 2: Starting FHIR server..."
if docker ps --format '{{.Names}}' | grep -q healthpay-fhir; then
    echo "  ✅ FHIR server already running"
else
    echo "  Starting HAPI FHIR R4 server on port $FHIR_PORT..."
    docker run -d \
        --name healthpay-fhir \
        -p ${FHIR_PORT}:8080 \
        -v healthpay-fhir-data:/data/hapi \
        -e hapi.fhir.fhir_version=R4 \
        -e hapi.fhir.allow_multiple_delete=true \
        -e hapi.fhir.allow_external_references=true \
        --restart unless-stopped \
        hapiproject/hapi:latest
    echo "  ⏳ Waiting for FHIR server to start (up to 60s)..."
    for i in $(seq 1 60); do
        if curl -sf "$FHIR_URL/metadata" >/dev/null 2>&1; then
            echo "  ✅ FHIR server ready (${i}s)"
            break
        fi
        sleep 1
        if [ "$i" -eq 60 ]; then
            echo "  ❌ FHIR server failed to start"
            exit 1
        fi
    done
fi

# Step 3: Check if data exists
echo "▶ Step 3: Checking FHIR data..."
PATIENT_COUNT=$(curl -sf "$FHIR_URL/Patient?_summary=count" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo 0)

if [ "$PATIENT_COUNT" -gt 0 ]; then
    echo "  ✅ Data already loaded ($PATIENT_COUNT patients)"
else
    echo "  📥 Importing Synthea data..."
    if [ -d "synthea/output/fhir" ]; then
        source venv/bin/activate 2>/dev/null || true
        python scripts/import_to_fhir.py synthea/output/fhir
    else
        echo "  ❌ Synthea data not found. Run scripts/generate_data.sh first."
        exit 1
    fi
fi

# Step 4: Run tests
echo ""
echo "▶ Step 4: Running integration tests..."
source venv/bin/activate 2>/dev/null || true
python -m pytest tests/test_integration.py -v --tb=short 2>&1 | tail -20

# Step 5: Run demo
echo ""
echo "▶ Step 5: Running full demo..."
echo ""
python scripts/demo_run.py

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ HealthPay Agent — Setup Complete!         ║"
echo "║                                              ║"
echo "║  FHIR Server: http://localhost:$FHIR_PORT/fhir  ║"
echo "║  MCP Server:  python -m src                  ║"
echo "║  PO Server:   python src/po_server.py        ║"
echo "╚══════════════════════════════════════════════╝"
