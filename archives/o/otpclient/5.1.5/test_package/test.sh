#!/bin/sh
# otpclient 5.1.5 消费者测试脚本
#
# 由 test_package/conanfile.py 调用：$1=包目录  $2=otpclient-cli 绝对路径
# 做的是「真实消费者行为」——实际执行被测程序并校验输出，而非静态断言。
#
# 安全模式说明：本脚本由 conan 以 `sh test.sh` 方式调用（shebang 不生效），
# 因此只用 POSIX 语义的 `set -eu`；`set -o pipefail` 非 POSIX，在 dash/mksh
# 上会直接报错中止，故不采用。
set -eu

PKG="$1"
CLI="$2"

fail() {
    echo "FAIL: $1"
    exit 1
}

# 1) CLI 版本输出（上游 src/cli/main.c:102-103 打印 "OTPClient version <PROJECT_VER>"）
if ! val=$("$CLI" --version 2>&1); then
    fail "otpclient-cli --version 执行失败：$val"
fi
echo "  otpclient-cli --version -> $val"
printf '%s' "$val" | grep -q '5\.1\.5' || fail "版本输出不含 5.1.5：$val"

# 2) --help 可用（GOption 解析路径走通，说明 glib/gio 运行时依赖链完整）
"$CLI" --help >/dev/null 2>&1 || fail "otpclient-cli --help 执行失败"

# 3) 包内数据编译产物（install 阶段宿主工具的成品）
[ -f "$PKG/share/glib-2.0/schemas/gschemas.compiled" ] \
    || fail "缺少 GSettings 编译产物：$PKG/share/glib-2.0/schemas/gschemas.compiled"

echo "otpclient consumer test passed"
