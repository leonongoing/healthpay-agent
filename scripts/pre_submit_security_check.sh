#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "🔐 HealthPay pre-submit security check"

fail=0

# 1) .env must not be tracked
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "❌ .env is tracked by git — remove it before pushing: git rm --cached .env"
  fail=1
else
  echo "✅ .env is not tracked"
fi

# 2) staged/tracked files must not contain Google API keys
if git grep -nE "AIza[0-9A-Za-z_-]{20,}" -- . \':!.env\' >/tmp/healthpay_secret_scan.txt 2>/dev/null; then
  echo "❌ Possible Google API key found in tracked files:"
  cat /tmp/healthpay_secret_scan.txt
  fail=1
else
  echo "✅ no Google API key pattern in tracked files"
fi

# 3) checklist must use placeholder only
if grep -qE "AIza[0-9A-Za-z_-]{20,}" docs/kaggle-submission-checklist.md; then
  echo "❌ checklist contains raw API key"
  fail=1
else
  echo "✅ checklist is sanitized"
fi

# 4) notebook exists
test -f kaggle_notebook.ipynb && echo "✅ kaggle_notebook.ipynb exists" || { echo "❌ missing kaggle_notebook.ipynb"; fail=1; }

if [ "$fail" -eq 0 ]; then
  echo "\n✅ SAFE TO PUSH public GitHub repo"
else
  echo "\n❌ NOT SAFE TO PUSH — fix issues above"
  exit 1
fi
