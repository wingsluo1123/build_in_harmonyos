#!/bin/sh
# Consumer test for the packaged kwrited 6.7.2 executable (OHOS aarch64).
#
# The deliverable is a daemon with no command line options and no stdout
# output, so the meaningful consumer check is real execution (R34):
#
#   1. start the packaged bin/kwrited under the offscreen QPA platform -- this
#      loads the whole Qt6/KF6 link closure and makes KPtyDevice open the pty;
#   2. require the process to be alive after the grace period (an immediate
#      exit means a missing library, a failed pty open or a QGuiApplication
#      start-up failure);
#   3. require its stdin to be a pty slave: the BUILD_AS_EXECUTABLE branch
#      dup2()s pty->slaveFd() to fd 0, so /proc/<pid>/fd/0 must resolve to
#      /dev/pts/N. This is a HARD assertion: when readlink is unavailable the
#      script falls back to parsing `ls -l`, and when neither works the test
#      FAILS -- a packaged build that does not attach the pty is a regression,
#      not something to skip silently;
#   4. stop it with SIGTERM and let the signal handler run the graceful path
#      (~KWrited calls pty->logout()). This step is best-effort: if the process
#      is still alive after 10s it is force-killed with a WARN, so it does not
#      count as an assertion (see MANIFEST.yml -> assertion_count).
#
# usage: test_app.sh <path-to-kwrited> [grace-seconds]
# exit:  0 = pass, 1 = fail, 2 = usage error
#
# Safety mode per code-style rule 7. The few places where a non-zero status is
# EXPECTED are handled explicitly (see the inline comments): `wait` on a child
# that was killed by SIGTERM, and the best-effort SIGTERM observation.
set -eu -o pipefail

APP_BIN="${1:-}"
GRACE="${2:-5}"

if [ -z "$APP_BIN" ] || [ ! -x "$APP_BIN" ]; then
    echo "FAIL: usage: $0 <path-to-kwrited> [grace-seconds]" >&2
    exit 2
fi

TMP_DIR="${CONSUMER_TEST_TMP:-.}"
mkdir -p "$TMP_DIR" 2>/dev/null || true
LOG="$TMP_DIR/kwrited-consumer.log"

echo "kwrited consumer test: $APP_BIN (grace ${GRACE}s)"

QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" \
    "$APP_BIN" >"$LOG" 2>&1 &
PID=$!

i=0
while [ "$i" -lt "$GRACE" ]; do
    if ! kill -0 "$PID" 2>/dev/null; then
        break
    fi
    sleep 1
    i=$((i + 1))
done

if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID" 2>/dev/null && RC=0 || RC=$?   # child already gone: keep its real code without tripping -e
    echo "FAIL: kwrited exited within ${GRACE}s (rc=$RC); output:" >&2
    sed -n '1,20p' "$LOG" >&2
    exit 1
fi
echo "OK: kwrited alive after ${GRACE}s (pid=$PID)"

# Executable branch: pty->slaveFd() is dup2()'d onto fd 0.
FD0=""
if [ -L "/proc/$PID/fd/0" ]; then
    FD0="$(readlink "/proc/$PID/fd/0" 2>/dev/null || true)"
fi
if [ -n "$FD0" ]; then
    case "$FD0" in
        /dev/pts/*)
            echo "OK: kwrited holds a pty on stdin -> $FD0"
            ;;
        *)
            echo "FAIL: kwrited stdin is not a pty slave: $FD0" >&2
            kill -TERM "$PID" 2>/dev/null
            exit 1
            ;;
    esac
else
    # 备用探针：readlink 不可用时退回 ls -l 抓 fd 目标；两条路都不行就判失败（pty 归属是硬断言）
    FD0="$(ls -l "/proc/$PID/fd/0" 2>/dev/null | grep -o '/dev/pts/[0-9]*' || true)"
    case "$FD0" in
        /dev/pts/*)
            echo "OK: kwrited holds a pty on stdin -> $FD0"
            ;;
        *)
            echo "FAIL: cannot assert pty ownership: /proc/$PID/fd/0 unreadable ('$FD0')" >&2
            kill -TERM "$PID" 2>/dev/null
            exit 1
            ;;
    esac
fi

kill -TERM "$PID" 2>/dev/null || true   # a just-exited child makes kill fail; that is fine here
i=0
while [ "$i" -lt 10 ]; do
    if ! kill -0 "$PID" 2>/dev/null; then
        break
    fi
    sleep 1
    i=$((i + 1))
done
if kill -0 "$PID" 2>/dev/null; then
    echo "WARN: kwrited did not exit on SIGTERM within 10s; forcing" >&2
    kill -KILL "$PID" 2>/dev/null || true   # may have exited between the check and the kill
fi
wait "$PID" 2>/dev/null || true   # SIGTERM'd child returns 143; this step is a best-effort observation

echo "OK: kwrited consumer test passed"
exit 0
