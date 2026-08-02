#!/usr/bin/env sh
set -eu

snapshot="${TMPDIR:-${HOME:-/tmp}/tmp}/codex-ps-swift-check.txt"
mkdir -p "$(dirname "$snapshot")" 2>/dev/null || true

date
uptime
free -h
ps -ef > "$snapshot"

echo "--- conan ---"
grep conan "$snapshot" || true
echo "--- clang ---"
grep clang "$snapshot" || true
echo "--- make ---"
grep make "$snapshot" || true
echo "--- ninja ---"
grep ninja "$snapshot" || true
echo "--- cmake ---"
grep cmake "$snapshot" || true
echo "--- python ---"
grep python "$snapshot" || true
echo "--- swift ---"
grep swift "$snapshot" || true

rm -f "$snapshot"
echo "--- top ---"
top -b -n 1 || true
