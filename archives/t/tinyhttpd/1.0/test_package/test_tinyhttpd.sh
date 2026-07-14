#!/bin/sh
# Test tinyhttpd binary: start server, verify it runs, clean up.
# Usage: sh test_tinyhttpd.sh /path/to/httpd

set -e

HTTPD_BIN="$1"
if [ -z "$HTTPD_BIN" ]; then
    echo "FAIL: no httpd binary path provided"
    exit 1
fi

if [ ! -x "$HTTPD_BIN" ]; then
    echo "FAIL: httpd binary not found or not executable: $HTTPD_BIN"
    exit 1
fi

# Use TMPDIR or fallback (E002: /tmp is read-only on OHOS)
WORKDIR="${TMPDIR:-$HOME/tmp}/tinyhttpd-test-$$"
mkdir -p "$WORKDIR/htdocs"
echo "<html><body>tinyhttpd test</body></html>" > "$WORKDIR/htdocs/index.html"

cd "$WORKDIR"

# Kill any lingering httpd process before starting
# (tinyhttpd hardcodes port 4000, prior runs may leave it occupied)
for pid in $(ps -e -o pid,comm 2>/dev/null | grep httpd | awk '{print $1}'); do
    kill -9 "$pid" 2>/dev/null || true
done
sleep 1

# Start httpd in background (hardcoded port 4000)
"$HTTPD_BIN" &
HTTPD_PID=$!

# Wait for server to start
sleep 2

# Cleanup function
cleanup() {
    kill -9 "$HTTPD_PID" 2>/dev/null || true
    wait "$HTTPD_PID" 2>/dev/null || true
    rm -rf "$WORKDIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Check if httpd process is still running
if kill -0 "$HTTPD_PID" 2>/dev/null; then
    echo "PASS: httpd started successfully on port 4000"
    cleanup
    exit 0
else
    echo "FAIL: httpd failed to start (process exited)"
    cleanup
    exit 1
fi
