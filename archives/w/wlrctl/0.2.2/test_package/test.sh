#!/usr/bin/env bash
# test_package/test.sh — wlrctl consumer smoke test
# R34/L0d：真实执行被测包二进制并断言输出
set -uo pipefail

# 依赖 wayland-client/libxkbcommon（conan 包 lib，conanfile.py 已注入
# LD_LIBRARY_PATH 前缀；/system/lib64 系统库兜底，与 wlopm 同款保障）。
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}/system/lib64"

BIN="$1"
[ -n "$BIN" ] && [ -x "$BIN" ] || { echo "❌ wlrctl not found/executable: ${BIN:-<empty>}"; exit 1; }

passed=0; failed=0
check() { # name, expected-substring, command...
  local name="$1" want="$2"; shift 2
  local out rc=0
  out="$("$@" 2>&1)" || rc=$?
  # 上游行为（main.c/keyboard.c/pointer.c/toplevel.c/output.c）：
  # --version/-v/--help/-h 退出码 0；无参数 usage 打印后 EXIT_FAILURE；
  # 各参数校验失败路径 die()/usage 后 EXIT_FAILURE——rc 容忍非 0，
  # 只断言输出内容（全部路径在 wl_display_connect 之前终止，无需
  # Wayland 会话）。
  if echo "$out" | grep -q -- "$want"; then
    echo "ok: $name"; passed=$((passed+1))
  else
    echo "FAIL: $name (want '$want', got: $(echo "$out" | head -2))"
    failed=$((failed+1))
  fi
}

echo "[test] wlrctl consumer smoke"
check "wlrctl --version" "wlrctl v0.2.2" "$BIN" --version
check "wlrctl -v (short version)" "wlrctl v0.2.2" "$BIN" -v
check "wlrctl --help (usage)" "Usage: wlrctl" "$BIN" --help
check "wlrctl -h (short help)" "Usage: wlrctl" "$BIN" -h
check "wlrctl (no args, usage)" "Usage: wlrctl" "$BIN"
check "wlrctl bogus (unknown command)" "Unknown command: 'bogus'" "$BIN" bogus
check "wlrctl keyboard (missing action)" "Missing keyboard action" "$BIN" keyboard
check "wlrctl keyboard bogus (unknown action)" "Unknown keyboard action: 'bogus'" "$BIN" keyboard bogus
check "wlrctl keyboard type (missing text)" "Missing text to type" "$BIN" keyboard type
check "wlrctl pointer bogus (unknown action)" "Unknown pointer action: 'bogus'" "$BIN" pointer bogus
check "wlrctl pointer click bogus (unknown button)" "Unknown button: 'bogus'" "$BIN" pointer click bogus
check "wlrctl toplevel (missing action)" "Missing toplevel action" "$BIN" toplevel
check "wlrctl toplevel bogus (unknown action)" "Unknown toplevel action: 'bogus'" "$BIN" toplevel bogus
check "wlrctl output (missing action)" "Missing output action or identifier" "$BIN" output
check "wlrctl output DP-1 bogus (unknown config)" "Unknown output configurataion 'bogus'" "$BIN" output DP-1 bogus

echo "HMBS_TEST_PACKAGE_RESULT=$(python3 -c "import json;print(json.dumps({'framework':'shell','discovered':15,'executed':15,'passed':$passed,'failed':$failed,'skipped':0}))")"
[ "$failed" -eq 0 ] || exit 1
echo "✅ wlrctl smoke test PASSED"
