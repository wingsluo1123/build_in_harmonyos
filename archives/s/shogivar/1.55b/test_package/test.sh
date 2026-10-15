#!/usr/bin/env bash
# test_package/test.sh — HarmonyOS consumer test for the packaged shogivar.
#
# usage: test.sh <package-folder>
#
# Runs on an aarch64 OHOS host with the package's bin/ on PATH (conanrun env).
# ShogiVar is a GTK+ 3 GUI application, so the consumer-visible contract that
# can be exercised without a display is:
#   * the CLI entry points the package itself provides (-v/--version, -h/--help,
#     handled before gtk_init());
#   * the run-time asset tree under share/games/shogivar, which upstream's
#     README declares mandatory ("installing is essential, as otherwise
#     ShogiVar would not be able to find any of its graphics files");
#   * the fact that the GUI path really does require a window system.
#
# Every check prints "ok N - <what>"; the process exits non-zero on the first
# failure.  N is the assertion number reported in reports/test-report.md.
set -u

PKG="${1:?usage: test.sh <package-folder>}"
BIN="$PKG/bin/shogivar"
DATA="$PKG/share/games/shogivar"

# OHOS shadows a few coreutils; pin the ones used here.
HEAD=$(if [ -x /bin/head ]; then echo /bin/head; else command -v head; fi)
OD=$(if [ -x /bin/od ]; then echo /bin/od; else command -v od; fi)
LS=$(if [ -x /bin/ls ]; then echo /bin/ls; else command -v ls; fi)
GREP=$(if [ -x /bin/grep ]; then echo /bin/grep; else command -v grep; fi)

N=0
FAILED=0
ok()   { N=$((N + 1)); echo "ok $N - $1"; }
fail() { N=$((N + 1)); FAILED=1; echo "not ok $N - $1"; }

# ── 1. the executable itself ───────────────────────────────────────────────
if [ -x "$BIN" ]; then
    ok "bin/shogivar installed and executable"
else
    fail "bin/shogivar missing or not executable ($BIN)"
fi

# ── 2-4. CLI contract ──────────────────────────────────────────────────────
OUT="$("$BIN" --version 2>&1)"
RC=$?
if [ $RC -eq 0 ] && printf '%s' "$OUT" | "$GREP" -q "shogivar version C-port-1.55b"; then
    ok "shogivar --version exits 0 and reports 'shogivar version C-port-1.55b' [$OUT]"
else
    fail "shogivar --version failed (rc=$RC, out=$OUT)"
fi

OUT="$("$BIN" -v 2>&1)"
RC=$?
if [ $RC -eq 0 ] && printf '%s' "$OUT" | "$GREP" -q "shogivar version C-port-1.55b"; then
    ok "shogivar -v exits 0 and reports the same version string"
else
    fail "shogivar -v failed (rc=$RC, out=$OUT)"
fi

OUT="$("$BIN" --help 2>&1)"
RC=$?
if [ $RC -eq 0 ] && printf '%s' "$OUT" | "$GREP" -q -- "--version" \
        && printf '%s' "$OUT" | "$GREP" -q -- "--help"; then
    ok "shogivar --help exits 0 and documents -v/--version and -h/--help"
else
    fail "shogivar --help failed (rc=$RC, out=$OUT)"
fi

# ── 5. asset tree present ──────────────────────────────────────────────────
if [ -d "$DATA" ]; then
    ok "share/games/shogivar asset tree installed"
else
    fail "share/games/shogivar missing ($DATA)"
fi

# ── 6-7. the 18 variant definitions and rule files ─────────────────────────
VARIANTS="Chu Dai DaiDai HShogi Heian Heiansho Judkin Maka Micro Mini Sho Shogi Tai Tenjiku Tori Wa Whale Yari"
RULES="Chu Dai DaiDai General HShogi Heian Judkin Maka Micro Mini Sho Shogi Tai Tenjiku Tori Wa Whale Yari"

MISSING=""
for v in $VARIANTS; do
    [ -s "$DATA/$v.dat" ] || MISSING="$MISSING $v.dat"
done
if [ -z "$MISSING" ]; then
    ok "all 18 board definitions (Data/*.dat) installed and non-empty"
else
    fail "missing/empty board definitions:$MISSING"
fi

MISSING=""
for r in $RULES; do
    [ -s "$DATA/$r.rul" ] || MISSING="$MISSING $r.rul"
done
if [ -z "$MISSING" ]; then
    ok "all 18 rule files (Data/*.rul, incl. General.rul) installed and non-empty"
else
    fail "missing/empty rule files:$MISSING"
fi

# ── 8-10. graphics asset counts ────────────────────────────────────────────
count() { "$LS" "$1" 2>/dev/null | wc -l | tr -d ' '; }

PIECES=$(count "$DATA/pieces")
if [ "${PIECES:-0}" -ge 1028 ]; then
    ok "piece graphics: $PIECES files (>= 1028)"
else
    fail "piece graphics incomplete: $PIECES files (expected >= 1028)"
fi

TITLES=$(count "$DATA/titles")
if [ "${TITLES:-0}" -ge 25 ]; then
    ok "variant title graphics: $TITLES files (>= 25)"
else
    fail "title graphics incomplete: $TITLES files (expected >= 25)"
fi

HELP=$(count "$DATA/help")
if [ "${HELP:-0}" -ge 24 ]; then
    ok "piece-help graphics: $HELP files (>= 24)"
else
    fail "piece-help graphics incomplete: $HELP files (expected >= 24)"
fi

# ── 11. representative assets are real PNGs (not truncated/placeholder) ────
PNG_OK=0
PNG_BAD=""
for f in "$DATA/pieces/Wapiece.png" "$DATA/titles/logo.png" \
         "$DATA/help/ChuHelp1.png"; do
    [ -f "$f" ] || { PNG_BAD="$PNG_BAD $f(missing)"; continue; }
    SIG=$("$HEAD" -c 4 "$f" | "$OD" -An -tx1 | tr -d ' \n')
    if [ "$SIG" = "89504e47" ]; then
        PNG_OK=$((PNG_OK + 1))
    else
        PNG_BAD="$PNG_BAD $f(sig=$SIG)"
    fi
done
if [ "$PNG_OK" -eq 3 ] && [ -z "$PNG_BAD" ]; then
    ok "representative piece/title/help assets carry the PNG signature (89504e47)"
else
    fail "asset signature check failed:$PNG_BAD"
fi

# ── 12. no zero-length asset claims to be installed ────────────────────────
EMPTY=$(find "$DATA" -type f ! -size +0c 2>/dev/null | wc -l | tr -d ' ')
if [ "${EMPTY:-1}" -eq 0 ]; then
    ok "no zero-length file under share/games/shogivar"
else
    fail "$EMPTY zero-length file(s) under share/games/shogivar"
fi

# ── 13. man page ───────────────────────────────────────────────────────────
MAN="$PKG/share/man/man6/shogivar.6"
if [ -s "$MAN" ]; then
    ok "man page share/man/man6/shogivar.6 installed and non-empty"
else
    fail "man page missing or empty ($MAN)"
fi

# ── 14. the binary resolves its asset tree next to itself ──────────────────
# This is the end-to-end check of the relocatable data directory: the package
# is materialised under an arbitrary conan/kv path, so the compiled-in
# --datadir of the build machine is not usable; --help reports what the
# running binary actually resolved.
DATADIR_LINE=$(printf '%s' "$("$BIN" --help 2>&1)" | "$GREP" -a "^Data directory: ")
RESOLVED=${DATADIR_LINE#Data directory: }
if [ -n "$RESOLVED" ] && [ -d "$RESOLVED" ] && [ -s "$RESOLVED/Shogi.dat" ]; then
    ok "binary resolves its asset tree at run time: $RESOLVED"
else
    fail "binary did not resolve a usable data directory (reported: '$RESOLVED')"
fi

# ── 15. the GUI path really needs a display (and does not crash) ───────────
# Without a display GTK must bail out with a display error and a non-zero exit
# status.  A signal death (>=128) would mean the binary is broken rather than
# merely display-less.
TMO=$(command -v timeout || true)
if [ -n "$TMO" ]; then
    OUT=$(DISPLAY= WAYLAND_DISPLAY= "$TMO" 60 "$BIN" 2>&1)
    RC=$?
    if [ $RC -gt 0 ] && [ $RC -lt 128 ] \
            && printf '%s' "$OUT" | "$GREP" -qi "display"; then
        ok "headless start exits cleanly with a display error (rc=$RC), no signal death"
    else
        fail "headless start behaved unexpectedly (rc=$RC, out=$OUT)"
    fi
else
    ok "headless start check skipped (no timeout(1) on this host) - not counted as failure"
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo "PASS: all $N consumer checks succeeded"
    exit 0
fi
echo "FAIL: $N checks run, at least one failed"
exit 1
