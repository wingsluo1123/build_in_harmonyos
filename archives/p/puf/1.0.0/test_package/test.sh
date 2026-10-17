#!/bin/sh
# test_package/test.sh — smoke + functional test for the puf executable.
# Usage: test.sh BINDIR PYTHON
#   BINDIR : absolute dir containing the installed `puf` binary
#            (resolved by test_package/conanfile.py from package_folder)
#   PYTHON : absolute python3 interpreter used to run the local HTTP
#            loopback server, or empty to skip the fetch test
# Verifies the packaged binary substantively: option parsing/usage
# (puf -h and bare `puf` argument-handling), plus puf's core function — a
# real HTTP download from a hermetic loopback server, checking that the
# fetched file content matches.
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs) and
# /bin/sh materializes $(...) command substitution in hardcoded /tmp
# (ignoring TMPDIR), so this script contains ZERO $(...) / backticks.
# Output capture uses plain redirections into $TMPDIR files; the HTTP
# server is synchronized by grepping its startup log (no IPC shell).
set -e

BINDIR="${1:-}"
PYTHON="${2:-}"

# Resolve a writable TMPDIR (parent conanfile.py already seeds it).
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export TEMPDIR="$TMPDIR"
if [ -z "${XDG_CACHE_HOME:-}" ]; then
    export XDG_CACHE_HOME="$TMPDIR"
fi

UPSTREAM_MARKER='HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"puf 1.0.0 ships no upstream test framework (no test directory, no make check test target, no gtest/ctest bindings; src/Makefile.am only defines bin_PROGRAMS = puf).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

fail_markers() {
    echo "$UPSTREAM_MARKER"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh <bindir>","discovered":3,"passedCount":0}'
    exit 1
}

if [ -z "$BINDIR" ] || [ ! -x "$BINDIR/puf" ]; then
    echo "[test] FAIL: puf binary not found/executable at '$BINDIR/puf'"
    if [ -n "$BINDIR" ]; then
        ls -la "$BINDIR" 2>&1 || true
    fi
    fail_markers
fi
PUF="$BINDIR/puf"
echo "[test] puf resolved: $PUF"

# Resolve PYTHON to an absolute path if a bare command name was given
# (conanfile.py normally passes HMBS_PYTHON3, an absolute path; this lets
# a bare `python3` arg work too). No $(...) used: `read` from a file.
if [ -n "$PYTHON" ] && [ ! -x "$PYTHON" ]; then
    command -v "$PYTHON" >"$TMPDIR/py_path.txt" 2>/dev/null || true
    if read -r PYP <"$TMPDIR/py_path.txt" 2>/dev/null && [ -n "$PYP" ]; then
        PYTHON="$PYP"
        echo "[test] python resolved via PATH: $PYTHON"
    else
        PYTHON=""
    fi
fi

PASS_COUNT=0
TOTAL=3

# ---- Assertion 1: puf -h prints the full help/usage (real option table
# ---- and getopts command path), exits 0.
echo "[test] assertion 1: puf -h usage output"
if "$PUF" -h >"$TMPDIR/puf_h.txt" 2>&1; then RC1=0; else RC1=$?; fi
echo "[test]   exit=$RC1"
grep -v '^  -' "$TMPDIR/puf_h.txt" 2>/dev/null || true
if [ "$RC1" -eq 0 ] && grep -q "Usage: puf" "$TMPDIR/puf_h.txt" 2>/dev/null \
    && grep -q "This help screen" "$TMPDIR/puf_h.txt" 2>/dev/null; then
    echo "[test]   PASS: puf -h prints usage"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test]   FAIL: puf -h did not print expected usage" >&2
fi

# ---- Assertion 2: bare `puf` (no URLs) prints the short usage and exits
# ---- with code 2 (argument-handling path). (Exit 2 is expected, so the
# ---- command runs inside an `if` condition, exempting it from `set -e`.)
echo "[test] assertion 2: puf with no args -> usage + exit 2"
if "$PUF" >"$TMPDIR/puf_na.txt" 2>&1; then RC2=0; else RC2=$?; fi
echo "[test]   exit=$RC2"
cat "$TMPDIR/puf_na.txt" 2>/dev/null || true
if [ "$RC2" -eq 2 ] && grep -q "Usage: puf" "$TMPDIR/puf_na.txt" 2>/dev/null \
    && grep -q "Try 'puf -h'" "$TMPDIR/puf_na.txt" 2>/dev/null; then
    echo "[test]   PASS: bare puf prints short usage and exits 2"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "[test]   FAIL: bare puf did not print usage/exit 2" >&2
fi

# ---- Assertion 3: real loopback HTTP fetch (puf's core function).
echo "[test] assertion 3: real local HTTP fetch"
if [ -n "$PYTHON" ] && [ -x "$PYTHON" ]; then
    WEBROOT="$TMPDIR/web"
    OUTDIR="$TMPDIR/out"
    mkdir -p "$WEBROOT" "$OUTDIR" 2>/dev/null || true
    echo "puf-http-fetch-ok-12345" > "$WEBROOT/payload.txt"
    # Port derived from shell PID via arithmetic (no command substitution).
    PORT=$(( 15000 + ($$ % 5000) ))
    HTTPDLOG="$TMPDIR/httpd.log"
    # Serve WEBROOT by running http.server from that cwd (--directory works
    # only on python>=3.7; cwd approach is maximally compatible). `-u`
    # forces unbuffered stderr so the "Serving HTTP" banner is flushed to
    # the log immediately (block-buffering would hide it and stall readiness).
    #
    # Detach the server from this script's stdio: redirect the *subshell*
    # fds (not just the inner command) and `exec` the interpreter so no
    # wrapper shell survives. Under mksh (OHOS /bin/sh) a `( ... ) &`
    # subshell keeps the inherited stdout pipe open for as long as it lives,
    # so the parent's `conan create | tee` capture never sees EOF and the CI
    # step hangs until the watchdog kill even though the build and test all
    # passed. With the redirects on the subshell plus `exec`, $! is the python
    # process itself, which holds no copy of the inherited stdout pipe.
    ( cd "$WEBROOT" && exec "$PYTHON" -u -m http.server "$PORT" --bind 127.0.0.1 ) \
        >"$HTTPDLOG" 2>&1 </dev/null &
    SRV_PID=$!
    # Wait up to ~25s for the server to report "Serving HTTP".
    i=0
    READY=0
    while [ "$i" -lt 25 ]; do
        if grep -q "Serving HTTP" "$HTTPDLOG" 2>/dev/null; then
            READY=1
            break
        fi
        sleep 1
        i=$((i+1))
    done
    if [ "$READY" -eq 1 ]; then
        if "$PUF" -P "$OUTDIR" "http://127.0.0.1:$PORT/payload.txt" \
            >"$TMPDIR/puf_fetch.txt" 2>&1; then RC3=0; else RC3=$?; fi
        echo "[test]   puf fetch exit=$RC3"
        cat "$TMPDIR/puf_fetch.txt" 2>/dev/null || true
        # Kill the hermetic server and reap it so nothing lingers.
        kill "$SRV_PID" 2>/dev/null || true
        wait "$SRV_PID" 2>/dev/null || true
        if [ "$RC3" -eq 0 ] \
            && grep -q "puf-http-fetch-ok-12345" "$OUTDIR/payload.txt" 2>/dev/null; then
            echo "[test]   PASS: puf downloaded payload with correct content"
            PASS_COUNT=$((PASS_COUNT+1))
        else
            echo "[test]   FAIL: puf fetch failed or content mismatch" >&2
        fi
    else
        echo "[test]   FAIL: local HTTP server did not become ready" >&2
        kill "$SRV_PID" 2>/dev/null || true
        wait "$SRV_PID" 2>/dev/null || true
    fi
else
    echo "[test]   SKIP: no python interpreter for local HTTP server"
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo "$UPSTREAM_MARKER"

echo "[test] passed=$PASS_COUNT total=$TOTAL"
if [ "$PASS_COUNT" -eq "$TOTAL" ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"/bin/sh test.sh <bindir>\",\"discovered\":${TOTAL},\"passedCount\":${PASS_COUNT}}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"/bin/sh test.sh <bindir>\",\"discovered\":${TOTAL},\"passedCount\":${PASS_COUNT}}"
    exit 1
fi
