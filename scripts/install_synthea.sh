#!/bin/bash
# Install Synthea patient data generator
set -e

SYNTHEA_DIR="/home/taomi/projects/healthpay-agent/synthea"

# Install Java if not present
if ! command -v java &> /dev/null; then
    echo "Installing Java JDK..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq default-jdk
fi

echo "Java version: $(java -version 2>&1 | head -1)"

# Download Synthea
if [ ! -f "$SYNTHEA_DIR/synthea-with-dependencies.jar" ]; then
    mkdir -p "$SYNTHEA_DIR"
    cd "$SYNTHEA_DIR"
    echo "Downloading Synthea..."
    curl -L -o synthea-with-dependencies.jar \
        "https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar"
    echo "Synthea downloaded successfully"
else
    echo "Synthea already downloaded"
fi

echo "Done. Run generate_data.sh to generate patient data."
