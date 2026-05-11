#!/bin/bash
# Kaggle Submission Verification Script

set -e

echo "🔍 Verifying Kaggle Submission Readiness..."
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $1"
    else
        echo -e "${RED}❌${NC} $1 MISSING"
        ((ERRORS++))
    fi
}

check_word_count() {
    local file=$1
    local max=$2
    local count=$(wc -w < "$file")
    if [ $count -le $max ]; then
        echo -e "${GREEN}✅${NC} $file: $count words (≤$max)"
    else
        echo -e "${RED}❌${NC} $file: $count words (>$max limit)"
        ((ERRORS++))
    fi
}

check_no_real_secrets() {
    local file=$1
    # Check for real OpenAI keys (not placeholders)
    if grep -q "sk-proj-" "$file" 2>/dev/null || grep -q "sk-[A-Za-z0-9]\{48\}" "$file" 2>/dev/null; then
        echo -e "${RED}❌${NC} $file contains potential real API keys"
        ((ERRORS++))
    # Check for real Ethereum private keys (64 hex chars, not placeholder)
    elif grep -E "0x[0-9a-fA-F]{64}" "$file" 2>/dev/null | grep -v "your_ethereum_private_key" | grep -v "MOCK" > /dev/null; then
        echo -e "${RED}❌${NC} $file contains potential real private keys"
        ((ERRORS++))
    else
        echo -e "${GREEN}✅${NC} $file: No real secrets detected"
    fi
}

echo "📄 Required Files:"
check_file "docs/kaggle-writeup.md"
check_file "docs/demo-video-script.md"
check_file "docs/impact-analysis.md"
check_file "KAGGLE_SUBMISSION.md"
check_file "LICENSE"
check_file ".gitignore"
check_file "README.md"
check_file ".env.example"
echo ""

echo "📝 Word Count Verification:"
check_word_count "docs/kaggle-writeup.md" 1500
echo ""

echo "🔒 Security Check:"
check_no_real_secrets "README.md"
check_no_real_secrets ".env.example"
check_no_real_secrets "src/config.py"
echo ""

echo "📦 Source Files:"
check_file "src/mcp_server.py"
check_file "src/gemma4_client.py"
check_file "src/denial_analyzer.py"
check_file "src/ar_reporter.py"
check_file "src/compliance_checker.py"
check_file "src/fhir_client.py"
check_file "requirements.txt"
echo ""

echo "🧪 Test Files:"
check_file "tests/test_enhanced_tools.py"
check_file "tests/test_integration.py"
echo ""

echo "📜 License Check:"
if grep -q "Apache License" LICENSE; then
    echo -e "${GREEN}✅${NC} Apache 2.0 license present"
else
    echo -e "${RED}❌${NC} Apache 2.0 license not found"
    ((ERRORS++))
fi
echo ""

echo "🔍 .gitignore Check:"
if grep -q ".env" .gitignore && grep -q "__pycache__" .gitignore; then
    echo -e "${GREEN}✅${NC} .gitignore covers secrets and Python artifacts"
else
    echo -e "${YELLOW}⚠️${NC} .gitignore may be incomplete"
    ((WARNINGS++))
fi
echo ""

echo "📊 Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Ready for Kaggle submission. Remaining tasks:"
    echo "  1. Record demo video (3 minutes)"
    echo "  2. Upload video to YouTube/Google Drive"
    echo "  3. Run: python tests/test_enhanced_tools.py"
    echo "  4. Submit to Kaggle before May 18, 2026"
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s) found${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $WARNINGS warning(s)${NC}"
    fi
    echo ""
    echo "Fix errors before submission."
    exit 1
fi
