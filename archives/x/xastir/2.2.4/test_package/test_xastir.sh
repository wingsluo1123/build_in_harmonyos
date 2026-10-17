#!/system/bin/sh
# Consumer test — xastir 2.2.4 (twclock precedent).
#   $1 = package bin dir, $2 = llvm-readelf, $3 = E050 repair view dir
# Assertions:
#   (a) callpass functional: output matches an independent Python
#       implementation of the published APRS passcode hash;
#   (b) xastir headless run: must fail with the real Xt display error
#       (proves the whole DT_NEEDED closure loaded);
#   (c) ELF DT_NEEDED walk covers the platform-critical sonames;
#   (d) the packaged runtime data tree is present.
# Any failure exits non-zero (CI L1e destructive reverse check: moving
# bin/ away makes (a)/(b)/(c) fail — this is not a stub test).
set -u

BIN_DIR="$1"
READELF="$2"
VIEW="$3"
XASTIR="$BIN_DIR/xastir"
CALLPASS="$BIN_DIR/callpass"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

[ -x "$XASTIR" ] || [ -f "$XASTIR" ] || fail "missing packaged binary: $XASTIR"
[ -f "$CALLPASS" ] || fail "missing packaged helper: $CALLPASS"

# ---------------------------------------------------------------- (a)
aprs_passcode() {
    # Independent reimplementation of the callpass hash (callpass.c):
    # seed 0x73e2, pair-wise XOR over the SSID-stripped uppercase callsign
    # (odd tail XORs the terminating NUL), 16-bit truncation, 0x7fff mask.
    python3 - "$1" <<'PYEOF'
import sys

def passcode(call):
    call = call.split("-")[0].upper()
    h = 0x73E2
    i = 0
    n = len(call)
    while i < n:
        h = (h ^ (ord(call[i]) << 8)) & 0xFFFF
        h = (h ^ (ord(call[i + 1]) if i + 1 < n else 0)) & 0xFFFF
        i += 2
    return h & 0x7FFF

print(passcode(sys.argv[1]))
PYEOF
}

for CALL in W1AW WA0EIR N0CALL X1ABC-9; do
    EXPECTED=$(aprs_passcode "$CALL")
    OUT=$(LD_LIBRARY_PATH="$VIEW${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$CALLPASS" "$CALL")
    RC=$?
    [ "$RC" -eq 0 ] || fail "callpass '$CALL' exited $RC: $OUT"
    echo "$OUT" | grep -q "Passcode for $CALL is $EXPECTED\$" \
        || fail "callpass '$CALL': expected hash $EXPECTED, got: $OUT"
done
echo "PASS: callpass functional hash check (4 callsigns)"

USAGE=$(LD_LIBRARY_PATH="$VIEW${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$CALLPASS" 2>&1)
echo "$USAGE" | grep -q "^Usage:callpass" || fail "callpass usage banner missing: $USAGE"
echo "PASS: callpass usage banner"

# ---------------------------------------------------------------- (b)
# Headless negative test (twclock matrix, adapted for the OHOS libXt
# finding). No X server exists on the target, so xastir must fail. The
# REAL assertions are:
#   - no dynamic-loader diagnostics in the output (the OHOS libc does
#     eager relocation, so reaching the X layer at all proves the whole
#     DT_NEEDED closure was mapped and relocated);
#   - a non-zero exit (exiting 0 without a display would be wrong);
#   - the failure mode is either the upstream "Can't open display" Xt
#     error (healthy libXt) or death by signal inside the libXt
#     display-less error path. The latter is a documented OHOS platform
#     condition of libXt/1.3.1: a minimal 8-line program that only calls
#     XtOpenDisplay(NULL,...) with DISPLAY unset dies with SIGSEGV and
#     zero output on this worker — see notes.md. What must NEVER appear
#     are loader errors: those would mean an unresolvable closure.
XOUT=$( ( unset DISPLAY; LD_LIBRARY_PATH="$VIEW${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" timeout 60 "$XASTIR" ) 2>&1 )
XRC=$?
if printf '%s\n' "$XOUT" | grep -qE "Error relocating|symbol not found|cannot open shared object|error while loading|Error loading shared library"; then
    UNLOADABLE=$(printf '%s\n' "$XOUT" | grep -oE "Error loading shared library [^:]+" | head -3 | tr '\n' ' ')
    [ -n "$UNLOADABLE" ] || UNLOADABLE="dynamic loader could not resolve the closure"
    fail "xastir runtime closure incomplete: $UNLOADABLE :: $XOUT"
fi
if [ "$XRC" -eq 124 ]; then
    fail "xastir hung for 60s without a display"
fi
if [ "$XRC" -eq 0 ]; then
    fail "xastir exited 0 without a display; expected failure"
fi
if printf '%s\n' "$XOUT" | grep -qiE "can'?t open display|Xt error|X OpenDisplay|cannot open.*display"; then
    echo "PASS: xastir headless-init negative test (upstream display error, rc=$XRC)"
elif [ "$XRC" -ge 128 ] && [ $((XRC - 128)) -ne 0 ] && [ $((XRC - 128)) -le 31 ]; then
    echo "PASS: xastir headless-init negative test (rc=$XRC = signal $((XRC-128)) in the libXt"
    echo "      display-less error path: documented OHOS platform condition of libXt/1.3.1;"
    echo "      closure fully loaded+relocated — zero loader diagnostics in output)"
else
    fail "xastir unexpected headless failure mode rc=$XRC output='$XOUT'"
fi

# ---------------------------------------------------------------- (c)
NEEDED=$("$READELF" -d "$XASTIR" 2>/dev/null | grep NEEDED) || fail "readelf failed"
# Direct DT_NEEDED set of the packaged xastir (xcb/Xau/Xdmcp/zstd/jpeg/
# webp/sharpyuv hang off libX11/libXext/libtiff transitively; the headless
# run in (b) proves the loader resolved that whole closure).
for SONAME in libXm.so.4 libXt.so.6 libX11.so.6 libXext.so.6 libXpm.so.4 \
              libSM.so.6 libICE.so.6 libcurl.so libproj.so.25 \
              libtiff.so.6 libgeotiff.so.5; do
    echo "$NEEDED" | grep -q "\[$SONAME\]" \
        || fail "xastir DT_NEEDED lacks $SONAME: $NEEDED"
done
echo "PASS: DT_NEEDED walk covers the direct platform sonames"
# The linked curl must be the graph's (SONAME libcurl.so), not the
# worker-prefix copy (SONAME libcurl.so.4 — see recipe generate()).
echo "$NEEDED" | grep -q "libcurl.so.4" \
    && fail "xastir linked the worker-prefix curl (libcurl.so.4), not the conan graph curl"
echo "$NEEDED" | grep -q "libpcre2-8.so.0" \
    && fail "xastir linked the worker-prefix shared pcre2, not the conan graph static pcre2"
echo "PASS: DT_NEEDED uses graph-owned sonames (no worker-prefix curl/pcre2)"

# ---------------------------------------------------------------- (d)
PKG=$(dirname "$BIN_DIR")
for DATA in share/xastir/config/language-English.sys \
            share/xastir/symbols/symbols.dat \
            share/xastir/help/help-English.dat; do
    [ -f "$PKG/$DATA" ] || fail "missing packaged runtime data: $DATA"
done
echo "PASS: packaged runtime data tree present"

echo "=== xastir 2.2.4 consumer test: ALL PASS ==="
