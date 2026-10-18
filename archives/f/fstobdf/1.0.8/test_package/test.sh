#!/bin/sh
# Consumer test for fstobdf 1.0.8 in a headless build / CI environment.
#
# fstobdf is a real X Font Server (FS protocol) client: its productive path
# needs a reachable font server (FONTSERVER or -server), which a CI runner
# does not provide.  Every path asserted below is therefore either completely
# independent of a server, or it is the documented no-server termination.
#
# All exit codes and message texts below were measured on the real binary
# before being written down here; fstobdf's usage() helper exits 0 by design
# (upstream behaviour), so the negative controls assert *stderr content and
# the absence of BDF output*, not a non-zero status.
set -u
passed=0
skipped=0
fail() { echo "FAIL: $1"; exit 1; }

OUT=./.fstobdf-stdout
ERR=./.fstobdf-stderr
rm -f "$OUT" "$ERR"

BIN=$(command -v fstobdf || true)
[ -n "$BIN" ] || fail "fstobdf not found on the conanrun PATH"
echo "PASS 1: binary resolved -> $BIN"
passed=$((passed + 1))

# --- 2. -version banner: PACKAGE_STRING on stdout, nothing on stderr -------
"$BIN" -version > "$OUT" 2> "$ERR"; rc=$?
[ "$rc" = "0" ] || fail "-version exit=$rc (expected 0)"
grep -qx "fstobdf 1.0.8" "$OUT" || fail "-version stdout is not exactly 'fstobdf 1.0.8': [$(cat "$OUT")]"
[ -s "$ERR" ] && fail "-version wrote to stderr: [$(cat "$ERR")]"
echo "PASS 2: -version -> 'fstobdf 1.0.8' on stdout, rc=0, stderr empty"
passed=$((passed + 1))

# --- 3. no arguments: usage error before any server contact ----------------
"$BIN" > "$OUT" 2> "$ERR"; rc=$?
[ "$rc" = "0" ] || fail "no-args exit=$rc (usage() exits 0 upstream)"
grep -q "No font name specified" "$ERR" || fail "no-args stderr lacks 'No font name specified': [$(cat "$ERR")]"
grep -q "Usage:" "$ERR" || fail "no-args stderr lacks 'Usage:' line"
[ -s "$OUT" ] && fail "no-args wrote to stdout: [$(cat "$OUT")]"
echo "PASS 3: no arguments -> 'No font name specified' + usage on stderr, rc=0, stdout empty"
passed=$((passed + 1))

# --- 4. -fn without a value -----------------------------------------------
"$BIN" -fn > "$OUT" 2> "$ERR"; rc=$?
[ "$rc" = "0" ] || fail "-fn exit=$rc (expected 0)"
grep -q -- "-fn requires an argument" "$ERR" || fail "-fn stderr lacks '-fn requires an argument': [$(cat "$ERR")]"
echo "PASS 4: '-fn' without value -> '-fn requires an argument', rc=0"
passed=$((passed + 1))

# --- 5. -server without a value ------------------------------------------
"$BIN" -server > "$OUT" 2> "$ERR"; rc=$?
[ "$rc" = "0" ] || fail "-server exit=$rc (expected 0)"
grep -q -- "-server requires an argument" "$ERR" || fail "-server stderr lacks '-server requires an argument': [$(cat "$ERR")]"
echo "PASS 5: '-server' without value -> '-server requires an argument', rc=0"
passed=$((passed + 1))

# --- 6. unknown option is rejected and named -----------------------------
"$BIN" -bogus > "$OUT" 2> "$ERR"; rc=$?
[ "$rc" = "0" ] || fail "-bogus exit=$rc (expected 0)"
grep -q -- "unrecognized option '-bogus'" "$ERR" || fail "-bogus stderr lacks \"unrecognized option '-bogus'\": [$(cat "$ERR")]"
echo "PASS 6: '-bogus' -> \"unrecognized option '-bogus'\", rc=0"
passed=$((passed + 1))

# --- 7. named font but no font server: documented stop, and crucially NO
#        BDF may be emitted (negative control for "it actually did work") ---
env -u FONTSERVER "$BIN" -fn fixed > "$OUT" 2> "$ERR"; rc=$?
[ "$rc" = "0" ] || fail "no-server exit=$rc (expected 0)"
grep -q "No font server specified." "$ERR" || fail "no-server stderr lacks 'No font server specified.': [$(cat "$ERR")]"
if grep -q "STARTFONT\|ENDFONT" "$OUT"; then
  fail "no-server run emitted BDF on stdout: [$(cat "$OUT")]"
fi
echo "PASS 7: '-fn fixed' with no font server -> 'No font server specified.', rc=0, no BDF emitted"
passed=$((passed + 1))

# --- 8. the packaged man page ships next to the binary -------------------
MAN="$(dirname "$BIN")/../share/man/man1/fstobdf.1"
if [ -s "$MAN" ]; then
  grep -q "fstobdf" "$MAN" || fail "man page $MAN does not mention fstobdf"
  echo "PASS 8: man page installed -> $MAN ($(wc -c < "$MAN") bytes)"
  passed=$((passed + 1))
else
  fail "man page not found at $MAN"
fi

# --- 9. ELF dependency closure (skipped, and reported as skipped, when no
#        readelf exists on the runner) ------------------------------------
READELF=$(command -v readelf || command -v llvm-readelf || true)
if [ -n "$READELF" ]; then
  needs=$("$READELF" -d "$BIN" 2>/dev/null | grep NEEDED | sed -e 's/.*\[\(.*\)\]/\1/' | tr "\n" " ")
  echo "NEEDED: $needs"
  for lib in libFS.so.6 libX11.so.6; do
    case " $needs " in
      *" $lib"*) : ;;
      *) fail "ELF NEEDED lacks $lib: [$needs]" ;;
    esac
  done
  echo "PASS 9: dependency closure complete -> $needs"
  passed=$((passed + 1))
else
  echo "SKIP 9: no readelf on this runner"
  skipped=$((skipped + 1))
fi

rm -f "$OUT" "$ERR"
echo "fstobdf 1.0.8 test_package: declared=9 passed=$passed skipped=$skipped failed=0"
[ $((passed + skipped)) -eq 9 ] || fail "assertion accounting mismatch: passed=$passed skipped=$skipped"
exit 0
