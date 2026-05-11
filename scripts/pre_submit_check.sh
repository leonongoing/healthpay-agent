#!/bin/bash
# Pre-submission checklist for 0G APAC Hackathon

set -e

echo "============================================================"
echo "  HealthPay Agent — Pre-Submission Checklist"
echo "============================================================"
echo ""

PROJECT_ROOT="/home/taomi/projects/healthpay-agent"
cd "$PROJECT_ROOT"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. Check required files exist
echo "1. Checking required files..."
required_files=(
    "README.md"
    "0G_APAC_SUBMISSION.md"
    "0G_DEMO_SCRIPT.md"
    "LEON_SUBMIT_GUIDE.md"
    "LICENSE"
    "requirements.txt"
    ".gitignore"
    "src/zero_g_storage.py"
    "src/zero_g_compute.py"
    "scripts/demo_run.py"
    "scripts/test_0g_integration.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file exists"
    else
        check_fail "$file missing"
    fi
done

# 2. Check .env is in .gitignore
echo ""
echo "2. Checking .gitignore..."
if grep -q "^\.env$" .gitignore; then
    check_pass ".env is in .gitignore"
else
    check_fail ".env not in .gitignore"
fi

# 3. Check for sensitive data leaks
echo ""
echo "3. Checking for sensitive data leaks..."
if grep -r "sk-[a-zA-Z0-9]\{20,\}" --include="*.py" --include="*.md" . 2>/dev/null | grep -v ".env" | grep -v "example" | grep -v "your-key-here" > /dev/null; then
    check_fail "Found potential OpenAI API key in code"
else
    check_pass "No OpenAI API keys found in code"
fi

if grep -r "0x[a-fA-F0-9]\{64\}" --include="*.py" --include="*.md" . 2>/dev/null | grep -v "MOCK" | grep -v "example" | grep -v "your_private_key" | grep -v "venv" | grep -v "node_modules" > /dev/null; then
    check_warn "Found potential private keys (check manually)"
else
    check_pass "No private keys found in code"
fi

# 4. Check Python dependencies
echo ""
echo "4. Checking Python dependencies..."
if [ -f "requirements.txt" ]; then
    if grep -q "python-0g" requirements.txt; then
        check_pass "python-0g in requirements.txt"
    else
        check_fail "python-0g missing from requirements.txt"
    fi
    
    if grep -q "mcp" requirements.txt; then
        check_pass "mcp in requirements.txt"
    else
        check_fail "mcp missing from requirements.txt"
    fi
fi

# 5. Check 0G integration files
echo ""
echo "5. Checking 0G integration..."
if grep -q "upload_to_0g" src/zero_g_storage.py; then
    check_pass "0G Storage upload function exists"
else
    check_fail "0G Storage upload function missing"
fi

if grep -q "ZeroGLLM" src/zero_g_compute.py; then
    check_pass "0G Compute LLM class exists"
else
    check_fail "0G Compute LLM class missing"
fi

# 6. Check README completeness
echo ""
echo "6. Checking README.md..."
readme_keywords=(
    "0G Storage"
    "0G Compute"
    "Merkle root"
    "python-0g"
    "Verifiable"
)

for keyword in "${readme_keywords[@]}"; do
    if grep -q "$keyword" README.md; then
        check_pass "README mentions '$keyword'"
    else
        check_warn "README missing '$keyword'"
    fi
done

# 7. Check demo script
echo ""
echo "7. Checking demo script..."
if [ -x "scripts/demo_run.py" ]; then
    check_pass "demo_run.py is executable"
else
    check_warn "demo_run.py not executable (run: chmod +x scripts/demo_run.py)"
fi

# 8. Check test script
echo ""
echo "8. Checking test script..."
if [ -f "scripts/test_0g_integration.py" ]; then
    check_pass "test_0g_integration.py exists"
else
    check_fail "test_0g_integration.py missing"
fi

# 9. Check file sizes
echo ""
echo "9. Checking file sizes..."
large_files=$(find . -type f -size +10M -not -path "./venv/*" -not -path "./node_modules/*" -not -path "./.git/*" 2>/dev/null)
if [ -z "$large_files" ]; then
    check_pass "No large files (>10MB) found"
else
    check_warn "Large files found (may slow down git clone):"
    echo "$large_files"
fi

# 10. Summary
echo ""
echo "============================================================"
echo "  Pre-Submission Checklist Complete"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Review any ❌ or ⚠️  items above"
echo "  2. Run: git status (check what will be committed)"
echo "  3. Run: git add . && git commit -m 'HealthPay Agent - 0G APAC Hackathon'"
echo "  4. Create GitHub repo and push"
echo "  5. Submit to HackQuest"
echo ""
echo "See LEON_SUBMIT_GUIDE.md for detailed instructions."
echo ""
