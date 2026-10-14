#!/usr/bin/env bash
# test.sh — zt-exec API 调用测试
# 编译并运行 Java 消费者程序：经 ProcessExecutor 真实 spawn 子 JVM，
# 验证输出重定向/exitValues/异步 start+Future/超时销毁 API（R34 实质性验证）。

set -euo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"

# 解析 JAVA_HOME：优先环境变量，其次检测常见 JDK 安装路径（真机 bishengjdk17 优先）
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    for candidate in \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
        /storage/Users/currentUser/bishengjdk17 \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -d "$candidate" ]; then
            JAVA_HOME="$candidate"
            break
        fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    echo "ERROR: JAVA_HOME not set and no JDK found in common locations." >&2
    echo "Set JAVA_HOME to a JDK 17+ installation path." >&2
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

MAIN_JAR="$PKG_DIR/libexec/zt-exec-1.12.jar"
SLF4J_JAR="$PKG_DIR/libexec/slf4j-api-1.7.2.jar"
TEST_SRC="$(dirname "$0")/TestZtExec.java"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== zt-exec API 调用测试 ==="

# 检查 JAR 文件存在
if [ ! -f "$MAIN_JAR" ]; then
    echo "ERROR: zt-exec JAR not found at $MAIN_JAR"
    exit 1
fi
echo "OK: main JAR found at $MAIN_JAR"

# 检查强制运行时依赖 slf4j-api 打包到位
if [ ! -f "$SLF4J_JAR" ]; then
    echo "ERROR: slf4j-api JAR not found at $SLF4J_JAR (mandatory runtime dependency)"
    exit 1
fi
echo "OK: slf4j-api JAR found"

# 编译测试程序
if ! javac -cp "$MAIN_JAR" "$TEST_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed"
    exit 1
fi
echo "OK: TestZtExec.java compiled successfully"

# 运行测试程序
CP="$MAIN_JAR:$SLF4J_JAR:$TMP_DIR"
output=$(java -cp "$CP" TestZtExec "$TMP_DIR" 2>&1) || {
    echo "ERROR: Java test execution failed"
    echo "$output"
    exit 1
}

# 验证测试输出包含 PASS
if echo "$output" | grep -q "PASS"; then
    echo "$output"
    echo "=== All tests passed ==="
    exit 0
else
    echo "ERROR: Test did not produce PASS output"
    echo "$output"
    exit 1
fi
