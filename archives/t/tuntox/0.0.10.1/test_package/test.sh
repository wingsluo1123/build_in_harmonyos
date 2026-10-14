#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for tuntox CLI
# Usage: test.sh <path-to-tuntox-binary>
#
# 运行真实的 tuntox 二进制并验证其功能：
#   - `tuntox -h` 触发 print_version()（内部调用 toxcore 的
#     tox_version_major/minor/patch —— 真实 toxcore API）与 help() 输出
#   - 能打印出 help 文本证明二进制可运行、toxcore/libsodium 正确链接
#   - 二进制 ELF 头校验 aarch64（armv8）体系，确认交叉编译目标正确
#
# 上游 tuntox 0.0.10.1 经审计无任何测试套件（详见 MANIFEST.yml
# upstream_test_audit），本脚本为消费者 test_package。
#
# 平台注意（OHOS 打包 ELF 调用方式）：打包后的 tuntox ELF 经 `sh`
# （mksh/toybox /bin/sh）无法直接运行——与 wwwoffle 先例一致
# （"wwwoffle: inaccessible or not found"）。按仓库已验证范式
# （templates/test_package-executable / keychain / wwwoffle），用 bash
# （CONFIG_SHELL，默认 /data/service/hnp/bin/bash）执行本测试，并以绝对路径
# 参数传入打包二进制。启动时先 cd 到可写 TMPDIR，避免 bash getcwd 失败。
set -u

# 先切到可写临时目录，规避 HMFS/HMDFS getcwd 失败。
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

TUNTOX="${1:?usage: test.sh <path-to-tuntox-binary>}"
FAILED=0
TOTAL=0

echo "[test] tuntox -h runs and prints usage"
TOTAL=$((TOTAL+1))
# 以绝对路径直接执行 ELF 二进制（bash exec）。
help_out=$("$TUNTOX" -h 2>&1)
printf '[debug] help_out=%s\n' "$help_out"
if printf '%s\n' "$help_out" | grep -q "tuntox - Forward ports over the Tox protocol"; then
  echo "PASS: help banner present"
else
  echo "FAIL: help banner missing"
  FAILED=$((FAILED+1))
fi

echo "[test] tuntox -h help lists Options"
TOTAL=$((TOTAL+1))
if printf '%s\n' "$help_out" | grep -q "Options:"; then
  echo "PASS: options listed"
else
  echo "FAIL: options missing"
  FAILED=$((FAILED+1))
fi

echo "[test] tuntox ELF is aarch64 (armv8)"
TOTAL=$((TOTAL+1))
# ELF64 little-endian: e_machine 字段在偏移 18，aarch64 = 0xb7（小端 b7 00）。
# 用 od -j18 -N2 直接读 e_machine 两字节。
emachine=$(od -An -tx1 -j 18 -N 2 "$TUNTOX" 2>/dev/null | tr -d ' \n')
if [ "$emachine" = "b700" ]; then
  echo "PASS: e_machine=aarch64 (0xb7)"
else
  echo "FAIL: e_machine=$emachine (expected b700 = aarch64)"
  FAILED=$((FAILED+1))
fi

# HMBS 证据标记（必须由真机测试命令结束后产生，discovered/passedCount 来自
# 本脚本真实断言计数：TOTAL 个用例，passed = TOTAL - FAILED）
discovered="$TOTAL"
passed="$((TOTAL - FAILED))"
if [ "$FAILED" -eq 0 ]; then
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test.sh <tuntox_binary>\",\"discovered\":$discovered,\"passedCount\":$passed}"
else
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh <tuntox_binary>\",\"discovered\":$discovered,\"passedCount\":$passed}"
fi

# 上游套件：tuntox 0.0.10.1 经审计无任何测试（MANIFEST.yml upstream_test_audit）
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"tuntox 0.0.10.1 upstream release tarball audited: Makefile has no check/test target, no tests/ directory, no test source files"}'

exit "$FAILED"
