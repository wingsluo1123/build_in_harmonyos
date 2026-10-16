#!/data/service/hnp/bin/bash
# test_package/test.sh — pqiv 消费者测试
#
# 在 conanrun 环境中运行安装后的 pqiv 可执行文件并断言真实输出（R34）。
# 断言对象是安装产物 bin/pqiv 本身：从 PATH 解析（VirtualRunEnv 将包 bin/
# 前置进 PATH），因此 L1e 反向验证（移走 bin/ 后 conan test 必须失败）成立。
set -eu

echo "[test] locating installed pqiv"
BIN="$(command -v pqiv)"
echo "[test] pqiv path: ${BIN}"
[ -x "${BIN}" ] || { echo "FAIL: pqiv not executable"; exit 1; }

echo "[test] assertion 1: pqiv --version prints exact upstream version"
VERSION_OUT="$("${BIN}" --version 2>&1)"
echo "${VERSION_OUT}"
printf '%s\n' "${VERSION_OUT}" | grep -q '^pqiv 2\.13\.3$' \
    || { echo "FAIL: unexpected --version output"; exit 1; }
echo "[test] assertion 1 OK"

echo "[test] assertion 2: pqiv --help exposes the real option surface"
HELP_OUT="$("${BIN}" --help 2>&1)"
printf '%s\n' "${HELP_OUT}" | grep -q 'Powerful quick image viewer' \
    || { echo "FAIL: --help summary missing"; exit 1; }
printf '%s\n' "${HELP_OUT}" | grep -q -- '--version' \
    || { echo "FAIL: --help does not list --version"; exit 1; }
echo "[test] assertion 2 OK"

echo "[test] assertion 3: pqiv rejects an invalid option with a non-zero exit"
if "${BIN}" --definitely-not-a-pqiv-option >/dev/null 2>&1; then
    echo "FAIL: pqiv accepted an invalid option"
    exit 1
fi
echo "[test] assertion 3 OK"

echo "[test] all pqiv consumer assertions passed"
