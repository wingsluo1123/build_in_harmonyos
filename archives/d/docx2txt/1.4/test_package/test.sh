#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for docx2txt executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# Find perl binary (may not be in conanrun PATH)
PERL_BIN="$(command -v perl 2>/dev/null || echo /data/service/hnp/bin/perl)"

# Find docx2txt.pl in the conan package bin/
DOCX2TXT_PL="$(command -v docx2txt.pl 2>/dev/null)"
if [ -z "$DOCX2TXT_PL" ]; then
    echo "❌ docx2txt.pl not found in PATH"
    exit 1
fi

echo "[test] docx2txt.pl -h (usage check)"
# docx2txt.pl uses die to print usage, so it exits non-zero
output=$("$PERL_BIN" "$DOCX2TXT_PL" -h 2>&1) || true
if echo "$output" | grep -qi "Usage"; then
    echo "✅ docx2txt.pl usage OK"
else
    echo "❌ docx2txt.pl failed to show usage"
    exit 1
fi

echo "[test] docx2txt.sh exists"
DOCX2TXT_SH="$(command -v docx2txt.sh 2>/dev/null)"
if [ -n "$DOCX2TXT_SH" ]; then
    echo "✅ docx2txt.sh found"
else
    echo "❌ docx2txt.sh not found"
    exit 1
fi

echo "[test] docx2txt.config exists"
PKG_DIR="$(dirname "$DOCX2TXT_PL")/.."
if find "$PKG_DIR" -name "docx2txt.config" -type f 2>/dev/null | head -1 | grep -q .; then
    echo "✅ docx2txt.config found"
else
    echo "❌ docx2txt.config not found"
    exit 1
fi
