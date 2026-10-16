#!/usr/bin/env bash
# test_package/test.sh — wlogout consumer smoke test
# R34/L0d：真实执行被测包二进制并断言输出
set -uo pipefail

BIN="$1"
[ -n "$BIN" ] && [ -x "$BIN" ] || { echo "❌ wlogout not found/executable: ${BIN:-<empty>}"; exit 1; }

passed=0; failed=0
check() { # name, expected-substring, command...
  local name="$1" want="$2"; shift 2
  local out rc=0
  out="$("$@" 2>&1)" || rc=$?
  # EPERM/未签名类失败显式判死——错误消息含二进制路径名，路径名里
  # 的 "wlogout" 子串会被宽松断言误匹配（假通过）。
  if echo "$out" | grep -q "Operation not permitted\|Permission denied"; then
    echo "FAIL: $name (exec denied: $(echo "$out" | head -1))"
    failed=$((failed+1))
    return
  fi
  # --version 走 g_print 后 exit(0)；--help 上游 g_print 后 exit(0)
  # （getopt_long 'h' 分支），此处只断言输出内容与退出非崩溃。
  if echo "$out" | grep -q "$want"; then
    echo "ok: $name"; passed=$((passed+1))
  else
    echo "FAIL: $name (rc=$rc, want '$want', got: $(echo "$out" | head -2))"
    failed=$((failed+1))
  fi
}

echo "[test] wlogout consumer smoke"
echo "[debug] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
check "wlogout --version" "1.2.2" "$BIN" --version
check "wlogout -v (short version)" "1.2.2" "$BIN" -v
check "wlogout --help (usage)" "Show help message" "$BIN" --help
check "wlogout -h (short help)" "Show help message" "$BIN" -h

echo "HMBS_TEST_PACKAGE_RESULT=$(python3 -c "import json;print(json.dumps({'framework':'shell','discovered':4,'executed':4,'passed':$passed,'failed':$failed,'skipped':0}))")"
[ "$failed" -eq 0 ] || exit 1
echo "✅ wlogout smoke test PASSED"
