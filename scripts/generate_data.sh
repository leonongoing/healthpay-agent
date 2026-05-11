#!/bin/bash
# Generate synthetic FHIR patient data using Synthea
set -e

SYNTHEA_DIR="/home/taomi/projects/healthpay-agent/synthea"
OUTPUT_DIR="/home/taomi/projects/healthpay-agent/data/synthea_output"
NUM_PATIENTS=${1:-50}

mkdir -p "$OUTPUT_DIR"

cd "$SYNTHEA_DIR"

echo "Generating $NUM_PATIENTS synthetic patients..."
java -jar synthea-with-dependencies.jar \
    -p "$NUM_PATIENTS" \
    --exporter.baseDirectory "$OUTPUT_DIR" \
    --exporter.fhir.export true \
    --exporter.fhir.transaction_bundle true \
    --exporter.hospital.fhir.export true \
    --exporter.practitioner.fhir.export true \
    --exporter.fhir_stu3.export false \
    --exporter.ccda.export false \
    --exporter.csv.export false \
    Massachusetts

echo "Generation complete. Output in: $OUTPUT_DIR"
echo "Files generated:"
ls -la "$OUTPUT_DIR/fhir/" | head -20
echo "Total FHIR bundles: $(ls "$OUTPUT_DIR/fhir/"*.json 2>/dev/null | wc -l)"
