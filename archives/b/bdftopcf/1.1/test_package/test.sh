#!/bin/bash
# test_package consumer test for bdftopcf 1.1.
#
# 消费者视角验证：按 README/man 的真实用法调用已安装的 bdftopcf 二进制，
# 把自带的最小 BDF 语料（font.bdf，2 个 glyph）编译成 PCF 并逐项断言。
#
# 断言全部基于命令输出与退出码，**不落任何临时文件**（OHOS 设备 /tmp 只读，
# 且 §12.71② 直编产物会被目录级 git add 扫进提交）：
#   * 输出文件路径一律用 `-o /dev/null`（照样走开/写路径），
#   * 数据面用 stdout 管道取前 4 字节比对 PCF magic。
set -u

pass=0
fail=0
ok()   { echo "PASS $1: $2"; pass=$((pass + 1)); }
bad()  { echo "FAIL $1: $2"; fail=$((fail + 1)); }

echo "--- bdftopcf 1.1 consumer verification ---"

# 1. 文档主用法 `-o <pcf 文件> <bdf 文件>`：退出码 0
bdftopcf -o /dev/null font.bdf > /dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  ok 1 "-o <out> <in> exit 0"
else
  bad 1 "-o conversion rc=$rc"
fi

# 2. stdout 模式产出的流带 PCF magic：首字节 0x01（byte order = LSBFirst），
#    其后 3 字节 ASCII 'f','p','c' —— 即 PCF_FILE_VERSION 小端字节序。
magic=$(bdftopcf font.bdf 2> /dev/null | head -c 4)
if [ "$magic" = "$(printf '\001fcp')" ]; then
  ok 2 "PCF magic = 01 66 63 70 (LSBFirst 'fcp')"
else
  bad 2 "magic len=${#magic} hex=$(printf '%s' "$magic" | od -An -tx1 | tr -d ' \n')"
fi

# 3. 产物非空（转换确实吐出了 PCF 数据，而不是空壳退出 0）
size=$(bdftopcf font.bdf 2> /dev/null | wc -c)
if [ "$size" -gt 100 ]; then
  ok 3 "stdout PCF stream = ${size} bytes"
else
  bad 3 "stdout PCF stream = ${size} bytes (expected > 100)"
fi

# 4. 流式（stdin → stdout）路径：man 页的 `[bdf file]` 缺省即从 stdin 读
bdftopcf < font.bdf > /dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  ok 4 "stdin -> stdout conversion exit 0"
else
  bad 4 "stdin conversion rc=$rc"
fi

# 5. 位图格式选项 `-p8`（1/2/4/8 之一）被接受且成功
bdftopcf -p8 -o /dev/null font.bdf > /dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  ok 5 "-p8 accepted, exit 0"
else
  bad 5 "-p8 rc=$rc"
fi

# 6. 损坏输入：非零退出 + stderr 报 corrupt（不静默吞错）
err=$(printf 'this is not a bdf font\n' | bdftopcf 2>&1 > /dev/null)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$err" | grep -q "corrupt"; then
  ok 6 "corrupt input -> rc=$rc + 'corrupt' diagnostic"
else
  bad 6 "corrupt input rc=$rc err=[$err]"
fi

# 7. 文件不存在：非零退出 + stderr 报 can't open
err=$(bdftopcf -o /dev/null __bdftopcf_missing_input__.bdf 2>&1 > /dev/null)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$err" | grep -q "can't open bdf source file"; then
  ok 7 "missing input -> rc=$rc + 'can't open bdf source file'"
else
  bad 7 "missing input rc=$rc err=[$err]"
fi

echo "test bdftopcf 1.1: $pass/$((pass + fail)) checks PASS"
[ "$fail" -eq 0 ] || exit 1
exit 0
