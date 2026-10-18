#!/usr/bin/env bash
# test_package/test.sh — kakoune-lsp (kak-lsp) consumer smoke test
# R34/L0d：真实执行被测包二进制并断言输出
set -uo pipefail

# 打包二进制为 OHOS rust 目标（clang 15 编译，libc++_shared std）；显式
# 补 /system/lib64——与 alacritty/0.17.0 test.sh 同款 loader 路径保障。
LL="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}/system/lib64:$LL:$LL/aarch64-linux-ohos"

BIN="$(command -v kak-lsp || true)"
if [ -z "$BIN" ] && [ -n "${1:-}" ]; then BIN="$1"; fi
[ -n "$BIN" ] && [ -x "$BIN" ] || { echo "❌ kak-lsp not found/executable: ${BIN:-<empty>}"; exit 1; }

passed=0; failed=0
check() { # name, expected-substring, command...
  local name="$1" want="$2"; shift 2
  local out
  out="$("$@" 2>&1)"
  if [ "$?" -eq 0 ] && echo "$out" | grep -q "$want"; then
    echo "ok: $name"; passed=$((passed+1))
  else
    echo "FAIL: $name (want '$want', got: $(echo "$out" | head -2))"
    failed=$((failed+1))
  fi
}

echo "[test] kak-lsp consumer smoke"
check "kak-lsp --version" "21.0.2" "$BIN" --version
check "kak-lsp --help (usage)" "Usage" "$BIN" --help
check "kak-lsp -h (short help)" "Usage" "$BIN" -h
check "kak-lsp --kakoune (kakoune rc emitted)" "kakoune" "$BIN" --kakoune
echo "HMBS_TEST_PACKAGE_RESULT=$(python3 -c "import json;print(json.dumps({'framework':'shell','discovered':4,'executed':4,'passed':$passed,'failed':$failed,'skipped':0}))")"
[ "$failed" -eq 0 ] || exit 1
echo "✅ kak-lsp smoke test PASSED"
