#!/data/service/hnp/bin/bash
# test_pasystray.sh — pasystray 0.8.2 消费者测试：结构性/链接性断言（R34/R51）。
#
# 本脚本只做**不需要执行被测二进制**的断言，因此它必须始终真正通过，并在
# 产物被移走时真正失败（CI 的 L1e 破坏性反向验证即依赖这一点）：
#   1. 产物存在且可执行（bin/pasystray）。
#   2. 产物是合法 ELF。
#   3. DT_NEEDED 记录 libpulse.so.0 与 libpulse-mainloop-glib.so.0 —— 证明交付物
#      链接的确实是 pulseaudio 提供的 GLib 主循环库（平台任务 9324 的争点）。
#
# CLI 契约（--version / --notify=help / 无显示失败路径）需要**真正执行**二进制，
# 由 test_package/conanfile.py 的 test() 直接运行并与 OHOS 运行期限制容错
# （先例：已合入的 pavucontrol-qt/2.4.0），不在本脚本内重复。
#
# 退出码：全部通过 0，否则 1；末行打印机器可读汇总。
set -eu

BIN="${1:?usage: test_pasystray.sh <path-to-pasystray>}"

TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

ok()  { TOTAL=$((TOTAL + 1)); PASSED=$((PASSED + 1)); printf '  PASS  %s\n' "$1"; }
bad() { TOTAL=$((TOTAL + 1)); FAILED=$((FAILED + 1)); printf '  FAIL  %s\n' "$1"; }
skip(){ SKIPPED=$((SKIPPED + 1)); printf '  SKIP  %s\n' "$1"; }

echo "== pasystray 0.8.2 test_package (structural): $BIN"

# --- 1. 产物存在且可执行 -------------------------------------------------
if [ -f "$BIN" ]; then ok "binary exists"; else bad "binary missing: $BIN"; fi
if [ -x "$BIN" ]; then ok "binary is executable"; else bad "binary not executable"; fi

# --- 2. 合法 ELF ---------------------------------------------------------
if [ -f "$BIN" ]; then
  MAGIC=$(head -c 4 "$BIN" 2>/dev/null | od -An -tx1 2>/dev/null | tr -d ' \n' || true)
  if [ "$MAGIC" = "7f454c46" ]; then ok "binary is a valid ELF (magic 7f454c46)"; else bad "not a valid ELF (magic '$MAGIC')"; fi
else
  bad "cannot check ELF magic: binary missing"
fi

# --- 3. DT_NEEDED 记录 pulseaudio 主循环库 -------------------------------
READELF=""
for c in /data/service/hnp/bin/llvm-readelf /data/service/hnp/bin/readelf \
         /usr/bin/readelf /system/bin/readelf; do
  if [ -x "$c" ]; then READELF="$c"; break; fi
done
if [ -n "$READELF" ]; then
  NEEDED=$("$READELF" -d "$BIN" 2>/dev/null || true)
  case "$NEEDED" in
    *libpulse.so.0*) ok "DT_NEEDED links libpulse (=libpulse.so.0)" ;;
    *) bad "DT_NEEDED is missing libpulse.so.0" ;;
  esac
  case "$NEEDED" in
    *libpulse-mainloop-glib.so.0*) ok "DT_NEEDED links libpulse-mainloop-glib (=libpulse-mainloop-glib.so.0)" ;;
    *) bad "DT_NEEDED is missing libpulse-mainloop-glib.so.0" ;;
  esac
else
  skip "no readelf available; DT_NEEDED assertions not counted"
fi

printf 'HMBS_TEST_PACKAGE_STRUCTURAL={"total":%s,"passed":%s,"failed":%s,"skipped":%s}\n' \
  "$TOTAL" "$PASSED" "$FAILED" "$SKIPPED"
[ "$FAILED" -eq 0 ] || exit 1
exit 0
