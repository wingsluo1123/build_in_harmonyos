#!/bin/sh
# Consumer test for fslsfonts 1.0.7 in a headless build / CI environment.
#
# fslsfonts is a real X Font Server (FS protocol) client: its main functional
# path (listing fonts) needs a reachable font server (FONTSERVER environment
# variable or -s servername), which a CI runner does not provide.  Only code
# paths that are stable without a server are asserted here:
#   1. the binary is resolvable through the consumer run environment
#   2. -version banner (PACKAGE_STRING, handled before any server contact)
#   3. -help usage text, exit 0 (also before any server contact)
#   4. no-server path: FONTSERVER unset must terminate on its own with the
#      documented "no font server defined" usage error (exit 1, no hang)
#   5. server-unreachable path: -s 127.0.0.1:1 exercises the real FS connect
#      code path and must terminate with the documented clean error (exit 0)
#   6. ELF NEEDED closure (readelf) - skipped, and reported as skipped, when
#      no readelf exists on the runner
set -u
passed=0
skipped=0
fail() { echo "FAIL: $1"; exit 1; }

BIN=$(command -v fslsfonts || true)
[ -n "$BIN" ] || fail "fslsfonts not found on the conanrun PATH"
LIBDIR=$(dirname "$BIN")
echo "PASS 1: binary resolved -> $BIN"
passed=$((passed + 1))

out=$(PATH="$LIBDIR:$PATH" timeout 30 "$BIN" -version 2>&1); rc=$?
[ "$rc" = "124" ] && fail "-version hung for 30s"
[ "$rc" = "0" ] || fail "-version exit=$rc output=[$out]"
case "$out" in
  *"fslsfonts 1.0.7"*) echo "PASS 2: -version -> $out" ;;
  *) fail "-version banner lacks 'fslsfonts 1.0.7': [$out]" ;;
esac
passed=$((passed + 1))

out=$(PATH="$LIBDIR:$PATH" timeout 30 "$BIN" -help 2>&1); rc=$?
[ "$rc" = "124" ] && fail "-help hung for 30s"
[ "$rc" = "0" ] || fail "-help exit=$rc output=[$out]"
case "$out" in
  *"print this message and exit"*)
    case "$out" in
      *"usage:"*) echo "PASS 3: -help usage text printed, rc=0" ;;
      *) fail "-help output lacks 'usage:' line: [$out]" ;;
    esac ;;
  *) fail "-help output lacks option help: [$out]" ;;
esac
passed=$((passed + 1))

out=$(env -u FONTSERVER PATH="$LIBDIR:$PATH" timeout 30 "$BIN" -l 2>&1); rc=$?
[ "$rc" = "124" ] && fail "no-server invocation hung for 30s"
[ "$rc" = "1" ] || fail "no-server path expected exit 1, got rc=$rc output=[$out]"
case "$out" in
  *"no font server defined"*)
    case "$out" in
      *"usage:"*) echo "PASS 4: no-server path -> 'no font server defined' + usage, rc=1" ;;
      *) fail "no-server output lacks usage line: [$out]" ;;
    esac ;;
  *) fail "no-server path lacks 'no font server defined': [$out]" ;;
esac
passed=$((passed + 1))

out=$(env -u FONTSERVER PATH="$LIBDIR:$PATH" timeout 30 "$BIN" -s 127.0.0.1:1 -l 2>&1); rc=$?
[ "$rc" = "124" ] && fail "-s 127.0.0.1:1 hung for 30s"
[ "$rc" = "0" ] || fail "unreachable-server path expected exit 0 (upstream), got rc=$rc output=[$out]"
case "$out" in
  *"unable to open server"*) echo "PASS 5: unreachable font server -> clean 'unable to open server', rc=0" ;;
  *) fail "unreachable-server path lacks clean error: [$out]" ;;
esac
passed=$((passed + 1))

READELF=$(command -v readelf || command -v llvm-readelf || true)
if [ -n "$READELF" ]; then
  needs=$("$READELF" -d "$BIN" 2>/dev/null | grep NEEDED | sed -e 's/.*\[\(.*\)\]/\1/' | tr "\n" " ")
  echo "NEEDED: $needs"
  case " $needs " in
    *" libFS.so.6"*) : ;;
    *) fail "ELF NEEDED lacks libFS.so.6: [$needs]" ;;
  esac
  echo "PASS 6: dependency closure complete -> $needs"
  passed=$((passed + 1))
else
  echo "SKIP 6: no readelf on this runner"
  skipped=$((skipped + 1))
fi

echo "fslsfonts 1.0.7 test_package: declared=6 passed=$passed skipped=$skipped failed=0"
exit 0
