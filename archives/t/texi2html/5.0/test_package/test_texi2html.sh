#!/usr/bin/env bash
#
# test_texi2html.sh — Verify texi2html can convert a .texi document to HTML.
#
# Usage:
#   test_texi2html.sh <texi2html_bin> <libintl_dir> <source_dir> <work_dir>
#
# Arguments:
#   texi2html_bin   Path to the texi2html executable (or basename if on PATH).
#   libintl_dir     Directory containing libintl-perl (for PERL5LIB).
#   source_dir      Directory containing sample.texi.
#   work_dir        Explicit writable working directory for the conversion run.
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

# --- Create the explicit working directory ---
mkdir -p "$WORK_DIR"

# --- Probe: verify the working directory is writable before running ---
PROBE_FILE="${WORK_DIR}/.texi2html-write-probe"
if ! (umask 022 && : > "${PROBE_FILE}") 2>/dev/null; then
    echo "FATAL: working directory not writable: ${WORK_DIR}" >&2
    exit 1
fi
rm -f "${PROBE_FILE}"

# --- Pre-check: sample.texi exists ---
SAMPLE_TEXI="${SOURCE_DIR}/sample.texi"
if [ ! -f "$SAMPLE_TEXI" ]; then
    echo "FATAL: sample.texi not found at ${SAMPLE_TEXI}" >&2
    exit 1
fi

cp "$SAMPLE_TEXI" "$WORK_DIR/sample.texi"

# --- Run texi2html conversion ---
export PERL5LIB="$LIBINTL_DIR"
cd "$WORK_DIR"

echo "Running: ${TEXI2HTML} --no-validate sample.texi" >&2
if ! "$TEXI2HTML" --no-validate sample.texi 2>&1; then
    echo "FAIL: texi2html exited with non-zero status" >&2
    exit 1
fi

# --- Assert sample.html was generated ---
if [ ! -f sample.html ]; then
    echo "FAIL: sample.html was not generated after running texi2html" >&2
    exit 1
fi

# --- Assert sample.html contains expected content ---
if ! grep -q 'Hello from texi2html' sample.html; then
    echo "FAIL: sample.html does not contain expected text 'Hello from texi2html'" >&2
    exit 1
fi

echo "SUCCESS: texi2html converted sample.texi to HTML (sample.html, $(wc -c < sample.html) bytes, contains 'Hello from texi2html')" >&2
exit 0
