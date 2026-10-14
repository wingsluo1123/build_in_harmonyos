#!/bin/sh
# End-to-end consumer test using the official IGMPlot water-dimer sample.
set -eu

IGMPLOT_BIN="${IGMPLOT_BIN:?IGMPLOT_BIN is required}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
WORK="${TMPDIR:-/tmp}/igmplot-consumer-test.$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

if [ ! -x "$IGMPLOT_BIN" ]; then
    echo "FAIL: IGMPlot executable not found: $IGMPLOT_BIN"
    exit 1
fi
echo "PASS: IGMPlot executable is installed"

cp "$SCRIPT_DIR/param.igm" "$SCRIPT_DIR/frag1.xyz" "$SCRIPT_DIR/frag2.xyz" "$WORK/"
cd "$WORK"

"$IGMPLOT_BIN" param.igm >run.log 2>&1
if ! grep -q "Done" run.log; then
    echo "FAIL: IGMPlot did not report successful completion"
    tail -80 run.log
    exit 1
fi
echo "PASS: official water-dimer sample completed"

for artifact in igm.vmd mol-dgInter.cube mol-dgIntra.cube mol-igm.dat; do
    if [ ! -s "$artifact" ]; then
        echo "FAIL: expected output artifact is missing: $artifact"
        exit 1
    fi
done
echo "PASS: expected IGMPlot output artifacts were generated"
echo "PASS: all IGMPlot consumer checks passed"
