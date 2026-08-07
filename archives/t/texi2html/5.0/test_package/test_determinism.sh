#!/usr/bin/env bash
#
# test_determinism.sh — Verify texi2html produces byte-identical HTML for the
# same multi-node/multi-section input across two independent processes.
#
# Regression for perl hash-order determinism: node/anchor numbering and
# diagnostic order must follow document (parse) order, so two separate
# processes must yield identical output.
#
# Usage:
#   test_determinism.sh <texi2html_bin> <libintl_dir> <source_dir> <work_dir>
#
# Arguments:
#   texi2html_bin   Path to the texi2html executable (or basename if on PATH).
#   libintl_dir     Directory containing libintl-perl (for PERL5LIB).
#   source_dir      Directory containing the test scripts/sample data.
#   work_dir        Explicit writable working directory for the runs.
#
# Exit status: 0 on success, 1 on failure.
#

set -o nounset
set -o errexit
set -o pipefail

if [ $# -lt 4 ]; then
    echo "FATAL: Usage: $0 <texi2html_bin> <libintl_dir> <source_dir> <work_dir>" >&2
    exit 1
fi

TEXI2HTML="$1"
LIBINTL_DIR="$2"
SOURCE_DIR="$3"
WORK_DIR="$4"

mkdir -p "$WORK_DIR"

# --- Probe: verify the working directory is writable ---
PROBE_FILE="${WORK_DIR}/.texi2html-write-probe"
if ! (umask 022 && : > "${PROBE_FILE}") 2>/dev/null; then
    echo "FATAL: working directory not writable: ${WORK_DIR}" >&2
    exit 1
fi
rm -f "${PROBE_FILE}"

# --- Multi-node / multi-section input ---
INPUT="${WORK_DIR}/determinism.texi"
cat > "$INPUT" << 'EOF'
\input texinfo
@setfilename determinism.info
@node Top
@top Determinism test

@menu
* First::
* Second::
@end menu

@node First
@chapter First chapter

@node Second
@chapter Second chapter

@bye
EOF

export PERL5LIB="$LIBINTL_DIR"
RUN1="${WORK_DIR}/run1"
RUN2="${WORK_DIR}/run2"
rm -rf "$RUN1" "$RUN2"
mkdir -p "$RUN1" "$RUN2"

echo "Running (1st process): ${TEXI2HTML} --no-validate -o ${RUN1}/ ${INPUT}" >&2
if ! "$TEXI2HTML" --no-validate -o "$RUN1/" "$INPUT" > "$RUN1/stdout.log" 2> "$RUN1/stderr.log"; then
    echo "FAIL: first texi2html run exited with non-zero status" >&2
    exit 1
fi

echo "Running (2nd process): ${TEXI2HTML} --no-validate -o ${RUN2}/ ${INPUT}" >&2
if ! "$TEXI2HTML" --no-validate -o "$RUN2/" "$INPUT" > "$RUN2/stdout.log" 2> "$RUN2/stderr.log"; then
    echo "FAIL: second texi2html run exited with non-zero status" >&2
    exit 1
fi

# --- Assert: the two HTML outputs are byte-identical ---
if [ ! -f "$RUN1/determinism.html" ]; then
    echo "FAIL: determinism.html not generated in run1" >&2
    exit 1
fi
if ! cmp -s "$RUN1/determinism.html" "$RUN2/determinism.html"; then
    echo "FAIL: HTML output differs between two independent processes" >&2
    diff "$RUN1/determinism.html" "$RUN2/determinism.html" | head -20 >&2 || true
    exit 1
fi

echo "SUCCESS: two independent runs produced byte-identical HTML ($(wc -c < "$RUN1/determinism.html") bytes)" >&2
exit 0
