#!/bin/sh
# k2pdfopt 2.55 — L1 functional test (test source for CI L0c).
# Runs the packaged k2pdfopt executable end-to-end: converts the embedded
# one-page test PDF (MuPDF render -> k2pdfopt page optimization -> PDF out)
# and verifies the output is a real PDF.
#
# Usage: run_test.sh <path-to-k2pdfopt> <path-to-test.pdf>
set -e

EXE="$1"
SRC="$2"

if [ ! -x "$EXE" ]; then
    echo "FAIL: k2pdfopt executable not found or not executable: $EXE" >&2
    exit 1
fi
if [ ! -f "$SRC" ]; then
    echo "FAIL: test PDF not found: $SRC" >&2
    exit 1
fi

rm -f k2out.pdf
# k2pdfopt waits for keypress on stdin after conversion; CI stdin is an
# always-open pipe so it would block forever (CI #90582: 14400s timeout).
# Redirect stdin from /dev/null and add a hard timeout as a safety net.
timeout 300 "$EXE" -ui- -o k2out.pdf "$SRC" < /dev/null

if [ ! -f k2out.pdf ]; then
    echo "FAIL: k2pdfopt did not produce k2out.pdf" >&2
    exit 1
fi

head=$(head -c 5 k2out.pdf)
if [ "$head" != "%PDF-" ]; then
    echo "FAIL: output is not a PDF (head=$head)" >&2
    exit 1
fi

echo "k2pdfopt 2.55: PDF conversion OK -> k2out.pdf"
