#!/data/service/hnp/bin/bash
# test_package/test.sh — on-device verification for the meterec 0.9.3
# executables (conanrun env: PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binaries:
#   - `test`  : the upstream event-queue self-test shipped in the tarball
#   - `meterec`: version/usage banner + no-JACK-server failure path
#   - `meterec-init-conf`: session .mrec generator (graceful without jackd)
set -euo pipefail

DISCOVERED=0
PASSED=0
RUN_OUTPUT=""
RUN_STATUS=0
# 上游 test 自测（Test 1~2）单独计数：机器证据标记只允许上报本行对应的
# 真实用例数，不能把下面 5 项配方自检的结果混进上游口径。
UP_DISCOVERED=0
UP_PASSED=0

run_cmd() {
    set +e
    RUN_OUTPUT="$("$@" 2>&1)"
    RUN_STATUS=$?
    set -e
}

# Resolve the installed bin directory (via the meterec binary on PATH).
BINDIR="$(dirname "$(command -v meterec)")"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# ---------------------------------------------------------------- Test 1
# Upstream queue self-test runs and exits 0 (no JACK server needed).
DISCOVERED=$((DISCOVERED + 1))
UP_DISCOVERED=$((UP_DISCOVERED + 1))
run_cmd "$BINDIR/test"
if [ "$RUN_STATUS" -eq 0 ]; then
    echo "OK: upstream queue self-test (test) exits 0"
    PASSED=$((PASSED + 1))
    UP_PASSED=$((UP_PASSED + 1))
else
    echo "FAIL: test exited $RUN_STATUS: $RUN_OUTPUT"
fi

# ---------------------------------------------------------------- Test 2
# The self-test output is fully deterministic: 12 state-dump separators,
# 20 queue lines, deterministic first line.
DISCOVERED=$((DISCOVERED + 1))
UP_DISCOVERED=$((UP_DISCOVERED + 1))
# `|| true` 是必需的：grep -c 在“零匹配”时**输出 0 但退出码为 1**，而本脚本是
# set -euo pipefail —— 管道退出码会让赋值语句整体失败、脚本在此**无诊断地终止**，
# 后面的 Test 3~7 与结果标记（HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT）
# 统统不会执行，CI 只能看到一个没有任何线索的失败。这正是“Test 1 失败时最需要诊断”
# 的场景，因此必须容错。仓库同类先例：archives/m/mafft/7.525/test_package/test_mafft.sh
# （`INPUT_SEQ_COUNT=$(grep -c '^>' ... || true)`）。
SEP_COUNT="$(printf '%s\n' "$RUN_OUTPUT" | grep -c '^====' || true)"
Q_COUNT="$(printf '%s\n' "$RUN_OUTPUT" | grep -c '^queue [0-9]' || true)"
if [ "$SEP_COUNT" -eq 12 ] && [ "$Q_COUNT" -eq 20 ] && \
   printf '%s' "$RUN_OUTPUT" | grep -q "queue 1 - type 1 - old 1 - new 1 - buf 1"; then
    echo "OK: queue self-test dump is deterministic (12 separators, 20 queue lines)"
    PASSED=$((PASSED + 1))
    UP_PASSED=$((UP_PASSED + 1))
else
    echo "FAIL: unexpected self-test dump (separators=$SEP_COUNT queue_lines=$Q_COUNT)"
fi

# ---------------------------------------------------------------- Test 3
# meterec -h prints the version banner. Upstream usage() calls exit(1).
DISCOVERED=$((DISCOVERED + 1))
run_cmd meterec -h
if [ "$RUN_STATUS" -eq 1 ] && printf '%s' "$RUN_OUTPUT" | grep -q "version 0.9.3"; then
    echo "OK: meterec -h prints 'version 0.9.3' (exit 1, upstream usage semantics)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: meterec -h status=$RUN_STATUS, banner missing: $RUN_OUTPUT"
fi

# ---------------------------------------------------------------- Test 4
# The usage text lists the core options.
DISCOVERED=$((DISCOVERED + 1))
if printf '%s' "$RUN_OUTPUT" | grep -q -- "-f freqency" && \
   printf '%s' "$RUN_OUTPUT" | grep -q -- "-o output-format"; then
    echo "OK: usage text lists the -f/-o options"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: usage text does not list the -f/-o options: $RUN_OUTPUT"
fi

# ---------------------------------------------------------------- Test 5
# meterec with no args in a scratch dir: no jackd on device -> the JACK
# registration fails and meterec exits non-zero. On OHOS the exact jack
# error string differs from upstream (the client init is refused earlier),
# so assert the core semantic only: a non-zero exit == graceful no-server
# failure. The specific message is logged for diagnostics but is not gated.
DISCOVERED=$((DISCOVERED + 1))
set +e
( cd "$WORKDIR" && meterec >/dev/null 2>&1 )
RUN_STATUS=$?
set -e
ERR="$(cd "$WORKDIR" && meterec 2>&1 >/dev/null || true)"
if [ "$RUN_STATUS" -ne 0 ]; then
    echo "OK: without a JACK server meterec exits non-zero (exit $RUN_STATUS; jack-client init refused)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: meterec should exit non-zero without a JACK server, got status=$RUN_STATUS ($ERR)"
fi

# ---------------------------------------------------------------- Test 6
# meterec-init-conf without args: usage text, exit 1.
# Use the absolute path: the file lives next to `meterec` (resolved via
# BINDIR), and invoking it as `sh <name>` relies on toybox `sh` re-doing a
# PATH lookup that the conanrun bin dir does not reach inside the sh subshell.
DISCOVERED=$((DISCOVERED + 1))
run_cmd sh "$BINDIR/meterec-init-conf"
if [ "$RUN_STATUS" -eq 1 ] && printf '%s' "$RUN_OUTPUT" | grep -q "Usage: meterec-init-conf <session-name>"; then
    echo "OK: meterec-init-conf without args prints usage (exit 1)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: meterec-init-conf usage status=$RUN_STATUS: $RUN_OUTPUT"
fi

# ---------------------------------------------------------------- Test 7
# meterec-init-conf <session> creates <session>.mrec; without a jack
# server the port map degrades to an empty ports=( array + version=1.
DISCOVERED=$((DISCOVERED + 1))
# 与 Test 5 同样处理：本脚本是 set -e，裸子 shell 一旦非零退出就会让脚本
# 在此静默终止，FAIL 分支与两个 HMBS 标记都不会输出。先捕获退出码再判定。
set +e
( cd "$WORKDIR" && sh "$BINDIR/meterec-init-conf" testsess >/dev/null 2>&1 )
INIT_STATUS=$?
set -e
if [ "$INIT_STATUS" -ne 0 ]; then
    echo "FAIL: meterec-init-conf testsess exited $INIT_STATUS"
fi
if [ "$INIT_STATUS" -eq 0 ] && [ -f "$WORKDIR/testsess.mrec" ] && \
   grep -q "ports=(" "$WORKDIR/testsess.mrec" && \
   grep -q "version=1;" "$WORKDIR/testsess.mrec"; then
    echo "OK: meterec-init-conf creates testsess.mrec (ports=() + version=1)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: testsess.mrec missing or malformed: $(cat "$WORKDIR/testsess.mrec" 2>/dev/null || echo absent)"
fi

echo "test_package: ${PASSED}/${DISCOVERED} checks passed"

# HMBS machine evidence markers (real case counts produced above)
if [ "$PASSED" -eq "$DISCOVERED" ]; then
    HMBS_PASSED=true
else
    HMBS_PASSED=false
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
    "$HMBS_PASSED" "$DISCOVERED" "$PASSED"
# Upstream ships the `test` queue self-test (executed as tests 1-2 above);
# no automake check/test target or other test framework exists.
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"executed","command":"test","discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":0,"reason":"tarball ships a standalone event-queue self-test binary (test); no check/test target or test framework"}\n' \
    "$UP_DISCOVERED" "$UP_DISCOVERED" "$UP_PASSED" "$((UP_DISCOVERED - UP_PASSED))"

[ "$PASSED" -eq "$DISCOVERED" ] || exit 1
