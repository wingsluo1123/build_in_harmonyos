#!/bin/sh
# test_package consumer test for bdf2sfd.
#
# 消费者视角验证：按 README 的真实用法调用已安装的 bdf2sfd 二进制，
# 把自带的最小 BDF 语料（font.bdf，2 个 glyph）转换成 SFD，并逐项断言
# 产物结构。覆盖 -v / -h / -f / -p 四个命令行选项。
#
# 断言全部基于命令输出（命令替换捕获），不落临时文件 —— OHOS 设备 /tmp 只读。
echo "--- bdf2sfd consumer verification ---"

fail() { echo "FAIL: $1"; exit 1; }

# ---- 1. -v 版本与任务版本逐字一致 ----
out_v=$(bdf2sfd -v 2>&1) || fail "-v exited non-zero"
case "$out_v" in
  *"bdf2sfd 1.1.9"*) echo "PASS 1: -v -> $out_v" ;;
  *) fail "-v output mismatch [$out_v]" ;;
esac

# ---- 2. -h 用法输出 ----
out_h=$(bdf2sfd -h 2>&1) || fail "-h exited non-zero"
case "$out_h" in
  *"-f name"*"font.bdf"*) echo "PASS 2: -h usage rendered" ;;
  *) fail "-h usage missing expected text [$out_h]" ;;
esac

# ---- 3. 无参调用（等价上游 ctest #1: add_test(bdf2sfd bdf2sfd)）----
bdf2sfd >/dev/null 2>&1
rc=$?
[ "$rc" -lt 128 ] || fail "no-arg invocation crashed (rc=$rc)"
echo "PASS 3: no-arg invocation rc=$rc (no crash)"

# ---- 4. BDF -> SFD 转换：SFD 魔数 + -f/-p 生效 ----
#   stdout(SFD) 与 stderr(glyph 计数) 合并捕获，一次运行全取。
#   实测（cat -A 逐字节，2026-10-07）：-f/-p 的取值是原样输出、不加引号 ——
#   `FullName: HarmonyMinimal`、`FontName: Harmony-Minimal`。
out_conv=$(bdf2sfd -f HarmonyMinimal -p Harmony-Minimal font.bdf 2>&1) \
  || fail "conversion exited non-zero"
case "$out_conv" in
  *"SplineFontDB: 3.0"*) echo "PASS 4a: SFD magic SplineFontDB: 3.0" ;;
  *) fail "missing SFD magic" ;;
esac
case "$out_conv" in
  *"FullName: HarmonyMinimal"*) echo "PASS 4b: -f applied to FullName" ;;
  *) fail "-f not applied" ;;
esac
case "$out_conv" in
  *"FontName: Harmony-Minimal"*) echo "PASS 4c: -p applied to FontName" ;;
  *) fail "-p not applied" ;;
esac

# ---- 5. glyph 数与语料一致（font.bdf 声明 CHARS 2）----
n=$(printf '%s\n' "$out_conv" | grep -c '^StartChar:')
[ "$n" = "2" ] || fail "StartChar count=$n, expected 2"
case "$out_conv" in
  *"Processed 2 glyphs"*) echo "PASS 5: 2 glyphs converted" ;;
  *) fail "missing 'Processed 2 glyphs' progress line" ;;
esac

echo "test bdf2sfd 1.1.9: 5/5 checks PASS"
exit 0
