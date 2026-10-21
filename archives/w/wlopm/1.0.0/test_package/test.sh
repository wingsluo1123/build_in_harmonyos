#!/usr/bin/env bash
# test_package/test.sh — wlopm consumer smoke test
# R34/L0d：真实执行被测包二进制并断言输出
set -uo pipefail

# 依赖 wayland-client（conan 包 lib + /system/lib64 系统库），显式补
# loader 路径——与 kakoune-lsp/alacritty test.sh 同款保障。
LL="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}/system/lib64:$LL:$LL/aarch64-linux-ohos"

BIN="$1"
[ -n "$BIN" ] && [ -x "$BIN" ] || { echo "❌ wlopm not found/executable: ${BIN:-<empty>}"; exit 1; }

passed=0; failed=0
check() { # name, expected-substring, command...
  local name="$1" want="$2"; shift 2
  local out rc=0
  out="$("$@" 2>&1)" || rc=$?
  # --version 退出码为 0；--help 上游实现 exit(EXIT_FAILURE)（usage 打到
  # stderr 后 exit 1，wlopm.c:498 fputs(usage, stderr); return EXIT_FAILURE）
  # ——rc 容忍非 0，只断言输出内容。
  if echo "$out" | grep -q "$want"; then
    echo "ok: $name"; passed=$((passed+1))
  else
    echo "FAIL: $name (want '$want', got: $(echo "$out" | head -2))"
    failed=$((failed+1))
  fi
}

echo "[test] wlopm consumer smoke"
check "wlopm --version" "wlopm version 1.0.0" "$BIN" --version
check "wlopm -v (short version)" "wlopm version 1.0.0" "$BIN" -v
check "wlopm --help (usage)" "Usage: wlopm" "$BIN" --help
check "wlopm -h (short help)" "Usage: wlopm" "$BIN" -h
check "wlopm --help (json option listed)" "\-\-json" "$BIN" --help

echo "HMBS_TEST_PACKAGE_RESULT=$(python3 -c "import json;print(json.dumps({'framework':'shell','discovered':5,'executed':5,'passed':$passed,'failed':$failed,'skipped':0}))")"
[ "$failed" -eq 0 ] || exit 1
echo "✅ wlopm smoke test PASSED"
