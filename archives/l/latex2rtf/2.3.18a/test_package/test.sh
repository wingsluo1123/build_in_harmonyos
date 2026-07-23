#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for latex2rtf executable
# Args: $1 = path to latex2rtf binary, $2 = path to cfg directory
set -euo pipefail

LATEX2RTF_BIN="${1:?Usage: test.sh <latex2rtf_path> <cfg_dir>}"
CFG_DIR="${2:-}"
TMPDIR="${TMPDIR:-/tmp}"

# Set RTFPATH so the binary can find its configuration files
if [ -n "$CFG_DIR" ] && [ -d "$CFG_DIR" ]; then
    export RTFPATH="$CFG_DIR"
fi

# Create a minimal LaTeX document
TEX_FILE="$TMPDIR/l2r_test_input.tex"
cat > "$TEX_FILE" << 'TEXEOF'
\documentclass{article}
\begin{document}
Hello World
\end{document}
TEXEOF

# Run latex2rtf to convert .tex to .rtf
echo "[step] latex2rtf functional test"
if ! "$LATEX2RTF_BIN" "$TEX_FILE"; then
    echo "        [fail] latex2rtf conversion failed"
    exit 1
fi

# Verify RTF output exists
RTF_FILE="$TMPDIR/l2r_test_input.rtf"
if [ ! -f "$RTF_FILE" ]; then
    echo "        [fail] RTF output file not created"
    exit 1
fi

# Verify RTF header is valid
RTF_HEADER=$(head -1 "$RTF_FILE")
case "$RTF_HEADER" in
    *"{\\rtf"*)
        echo "        [ok] valid RTF output detected"
        ;;
    *)
        echo "        [fail] invalid RTF header: $RTF_HEADER"
        exit 1
        ;;
esac

echo "        [ok] latex2rtf smoke test passed"
