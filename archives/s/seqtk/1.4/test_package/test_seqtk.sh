#!/bin/sh
set -eu

input="$(mktemp "${TMPDIR:-.}/seqtk-test.XXXXXX")"
fasta="$(mktemp "${TMPDIR:-.}/seqtk-test.XXXXXX")"
sizes="$(mktemp "${TMPDIR:-.}/seqtk-test.XXXXXX")"
trap 'rm -f "$input" "$fasta" "$sizes"' EXIT HUP INT TERM

printf '%s\n' '@read1' 'ACGT' '+' 'IIII' > "$input"
seqtk seq -a "$input" > "$fasta"
seqtk size "$input" > "$sizes"

grep -Fqx '>read1' "$fasta"
grep -Fqx 'ACGT' "$fasta"
grep -Fqx 'read1	4' "$sizes"
