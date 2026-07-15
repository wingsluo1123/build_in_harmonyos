#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for latex2rtf executable
# Runs in conanrun env (PATH includes installed bin/)
# latex2rtf doesn't support --version, so we test actual conversion
set -eu

TMPDIR="${TMPDIR:-/tmp}"

# Create a minimal LaTeX document
TEX_FILE="$TMPDIR/l2r_test_input.tex"
cat > "$TEX_FILE" << 'TEXEOF'
\documentclass{article}
\begin{document}
Hello World
\end{document}
TEXEOF

# Run latex2rtf to convert .tex to .rtf
echo "[test] latex2rtf $TEX_FILE"
latex2rtf "$TEX_FILE" || {
    echo "❌ latex2rtf conversion failed"
    exit 1
}

# Verify RTF output exists and has valid header
RTF_FILE="$TMPDIR/l2r_test_input.rtf"
if [ ! -f "$RTF_FILE" ]; then
    echo "❌ RTF output file not created"
    exit 1
fi

if ! head -1 "$RTF_FILE" | grep -q '{\\rtf'; then
    echo "❌ Invalid RTF header"
    exit 1
fi

echo "✅ latex2rtf conversion test passed"
