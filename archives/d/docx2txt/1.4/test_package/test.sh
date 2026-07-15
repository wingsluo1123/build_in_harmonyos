#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for docx2txt executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] docx2txt.pl -h (usage check)"
docx2txt.pl -h 2>&1 | grep -qi "Usage" && echo "✅ docx2txt.pl usage OK" || {
    echo "❌ docx2txt.pl failed to show usage"
    exit 1
}

echo "[test] docx2txt.sh exists"
test -f "$(command -v docx2txt.sh 2>/dev/null || echo /dev/null)" && echo "✅ docx2txt.sh found" || {
    echo "[test] docx2txt.sh not in PATH, checking bin dir..."
    ls $(dirname $(command -v docx2txt.pl))/docx2txt.sh >/dev/null 2>&1 && echo "✅ docx2txt.sh found in bin" || {
        echo "❌ docx2txt.sh not found"
        exit 1
    }
}

echo "[test] docx2txt.config exists"
find $(dirname $(command -v docx2txt.pl))/.. -name "docx2txt.config" -type f 2>/dev/null | head -1 | grep -q . && echo "✅ docx2txt.config found" || {
    echo "❌ docx2txt.config not found"
    exit 1
}
