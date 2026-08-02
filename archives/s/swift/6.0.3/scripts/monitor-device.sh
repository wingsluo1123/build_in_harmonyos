#!/usr/bin/env sh
set -eu

snapshot_dir="${TMPDIR:-${HOME:-/tmp}/tmp}"
snapshot="${snapshot_dir}/codex-ps-swift-check-$$.txt"
mkdir -p "$snapshot_dir" 2>/dev/null || true
trap 'rm -f "$snapshot"' EXIT

date || true
uptime || true
free -h || true

show_matches() {
  label="$1"
  pattern="$2"
  echo "--- $label ---"
  grep "$pattern" "$snapshot" || true
}

if ps -ef > "$snapshot"; then
  show_matches conan conan
  show_matches clang clang
  show_matches make make
  show_matches ninja ninja
  show_matches cmake cmake
  show_matches python python
  show_matches swift swift
else
  echo "--- ps snapshot failed ---"
fi

echo "--- top ---"
top -b -n 1 || true
