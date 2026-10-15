#!/bin/sh
# Consumer test for the cascade package (installed through Conan, run on the OHOS profile).
# usage: sh test_cascade.sh <package>/bin/cascade <package-folder> <writable-work-dir>
#
# The consumer feeds its own RF cascades to the installed tool and checks the
# computed numbers against an independent Friis-formula evaluation done by the
# system awk, so the installed sh script, the awk name baked in by the recipe
# and the awk dialect on the target are all exercised end to end.
set -u

CASCADE=$1
PKG=$2
pass=0
fail=0
WORK=$3
work=$WORK/cascade-consumer.$$
mkdir -p "$work" || exit 1
trap 'rm -rf "$work"' EXIT HUP INT TERM

ok() { pass=$((pass + 1)); echo "PASS: $1"; }
ko() { fail=$((fail + 1)); echo "FAIL: $1"; }
check() { # check <description> <command...>
    desc=$1; shift
    if "$@"; then ok "$desc"; else ko "$desc"; fi
}

# last value of a "<label> = <num> dB" report line
last_val() { # last_val <file> <label-regex>
    awk -v re="$2" '$0 ~ re { v = $0; sub(/^[^=]*=[ \t]*/, "", v); sub(/[ \t]+dB.*$/, "", v); r = v } END { print r }' "$1"
}
close_to() { # close_to <got> <expected> <tol>
    awk -v a="$1" -v b="$2" -v t="$3" 'BEGIN { d = a - b; if (d < 0) d = -d; exit !(d <= t) }'
}

# 1. CLI entry points -------------------------------------------------------
check "executable installed in bin/" test -x "$CASCADE"
check "--version prints 'cascade 1.4'" sh -c "\"$CASCADE\" --version | grep -q '^cascade 1.4\$'"
check "--help exits 0 and mentions usage" sh -c "\"$CASCADE\" --help | grep -q 'USAGE'"
"$CASCADE" /nonexistent/input.cas > "$work/err.out" 2>&1
rc=$?
check "missing input file exits 1" test $rc -eq 1
check "missing input file reports the error" grep -q 'not found or is not readable' "$work/err.out"
"$CASCADE" --bogus > /dev/null 2>&1
rc=$?
check "unknown option exits 1" test $rc -eq 1

# 2. upstream example: shipped ex1.cas must reproduce shipped ex1.out (stderr must stay empty:
#    an awk without the dropped gawk-only strftime used to print a parse error here)
EX=$PKG/share/examples/cascade
check "example input/output installed" test -r "$EX/ex1.cas" -a -r "$EX/ex1.out"
"$CASCADE" "$EX/ex1.cas" > "$work/ex1.mine" 2> "$work/ex1.err"
rc=$?
check "ex1.cas runs to completion (exit 0)" test $rc -eq 0
check "ex1.cas run prints nothing on stderr" test ! -s "$work/ex1.err"
# the banner echoes the input path, so compare without the 'Processing input file' line
grep -v '^Processing input file' "$work/ex1.mine" > "$work/a"
grep -v '^Processing input file' "$EX/ex1.out" > "$work/b"
check "ex1 report identical to upstream ex1.out" cmp -s "$work/a" "$work/b"

# 3. Friis cascade, two stages: LNA then lossless stage ------------------------
cat > "$work/lna.cas" <<'EOF'
source c=-40 cn=25 bw=1e6
lna g=10 nf=3
second g=0 nf=10
EOF
"$CASCADE" "$work/lna.cas" > "$work/lna.out"
check "two-stage cascade exits 0" test $? -eq 0
exp_nf=$(awk 'BEGIN { f1 = 10^(3/10); f2 = 10^(10/10); g1 = 10^(10/10);
                      printf "%.2f", 10*log(f1 + (f2 - 1)/g1)/log(10) }')
got_nf=$(last_val "$work/lna.out" 'Total Noise Figure')
check "total NF matches Friis ($got_nf vs $exp_nf dB)" close_to "$got_nf" "$exp_nf" 0.01
got_g=$(last_val "$work/lna.out" 'Total Power   Gain')
check "total gain is 10.00 dB (got $got_g)" close_to "$got_g" 10 0.01
got_c=$(last_val "$work/lna.out" 'Output Carrier Level')
check "output carrier is -30.00 dBm (got $got_c)" close_to "$got_c" -30 0.01
check "report lists both stages" sh -c "grep -q 'Stage #2  \"second\"' '$work/lna.out'"

# 4. Friis cascade with a lossy first stage (attenuator then amplifier) --------
cat > "$work/pad.cas" <<'EOF'
source c=-50 cn=30 bw=2e6
pad g=-6 nf=6
amp g=20 nf=2 iip3=-5
EOF
"$CASCADE" "$work/pad.cas" > "$work/pad.out"
check "pad+amp cascade exits 0" test $? -eq 0
exp_nf2=$(awk 'BEGIN { f1 = 10^(6/10); f2 = 10^(2/10); g1 = 10^(-6/10);
                       printf "%.2f", 10*log(f1 + (f2 - 1)/g1)/log(10) }')
got_nf2=$(last_val "$work/pad.out" 'Total Noise Figure')
check "pad+amp total NF matches Friis ($got_nf2 vs $exp_nf2 dB)" close_to "$got_nf2" "$exp_nf2" 0.01
got_g2=$(last_val "$work/pad.out" 'Total Power   Gain')
check "pad+amp total gain is 14.00 dB (got $got_g2)" close_to "$got_g2" 14 0.01
check "IIP3 summary printed for the amplifier" sh -c "grep -q 'IIP3 Contribution Summary' '$work/pad.out'"

# 5. input-file features: comment echo and 'defaults' keyword ------------------
cat > "$work/feat.cas" <<'EOF'
@ consumer annotation line
source c=-40 cn=25 bw=1e6
defaults rin=75 rout=75
stage_a g=6 nf=4
EOF
"$CASCADE" "$work/feat.cas" > "$work/feat.out"
check "'@' comment is echoed to the report" sh -c "grep -q '^@ consumer annotation line' '$work/feat.out'"
check "'defaults rin=75' applied to the stage" sh -c "grep -q 'Input Res. = 75 Ohms,  Output Res. = 75 Ohms' '$work/feat.out'"

# 6. man page source and doc/lisp payload ---------------------------------------
check "man1 page installed" test -s "$PKG/share/man/man1/cascade.1"
check "man1 page is roff source for cascade" grep -q '^\.TH' "$PKG/share/man/man1/cascade.1"
check "html documentation installed" test -s "$PKG/share/doc/cascade/index.html"
check "emacs mode installed" test -s "$PKG/share/emacs/site-lisp/cascade-mode.el"

echo "cascade consumer test: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
