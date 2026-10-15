#!/usr/bin/env bash
# test.sh — jakarta-jmeter 2.13 消费者验证
# 1) 结构校验：打包产物是可运行的 JMeter home（bin/ApacheJMeter.jar + lib/ + lib/ext/）
# 2) 真实运行打包出来的 JMeter 二进制入口：java -jar ApacheJMeter.jar --version → 必须报告 2.13
# 3) 编译并运行 Java 反射消费者程序（TestApacheJMeter.java，断言核心 API 与版本）
# 满足 R34 实质性验证要求

set -euo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"

# 解析 JAVA_HOME：优先环境变量，其次检测常见 JDK 安装路径
# （HNP 自带的 java 在部分环境无法启动，故优先 ~/bishengjdk17）
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    for candidate in \
        "$HOME/bishengjdk17" \
        /storage/Users/currentUser/bishengjdk17 \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
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

# /tmp 在 OHOS 沙箱只读（EROFS），mktemp 失败时回退 $HOME
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"
trap 'rm -rf "$TMP_DIR"' EXIT

JM_HOME="$PKG_DIR/libexec/jmeter"

echo "=== jakarta-jmeter 2.13 消费者验证 ==="

# 1) 结构校验：主 jar、模块 jar、运行时依赖 jar
JAR_MAIN="$JM_HOME/bin/ApacheJMeter.jar"
if [ ! -f "$JAR_MAIN" ]; then
    echo "ERROR: ApacheJMeter.jar not found at $JAR_MAIN"
    exit 1
fi
echo "OK: ApacheJMeter.jar found"

if [ ! -f "$JM_HOME/lib/ext/ApacheJMeter_core.jar" ]; then
    echo "ERROR: lib/ext/ApacheJMeter_core.jar not found"
    exit 1
fi
echo "OK: ApacheJMeter_core.jar found"

LIB_JAR_COUNT=0
for j in "$JM_HOME"/lib/*.jar; do
    [ -f "$j" ] && LIB_JAR_COUNT=$((LIB_JAR_COUNT + 1))
done
EXT_JAR_COUNT=0
for j in "$JM_HOME"/lib/ext/*.jar; do
    [ -f "$j" ] && EXT_JAR_COUNT=$((EXT_JAR_COUNT + 1))
done
echo "OK: lib/ jars = $LIB_JAR_COUNT, lib/ext/ jars = $EXT_JAR_COUNT"
if [ "$LIB_JAR_COUNT" -lt 30 ] || [ "$EXT_JAR_COUNT" -lt 8 ]; then
    echo "ERROR: runtime jar set looks incomplete (lib=$LIB_JAR_COUNT, ext=$EXT_JAR_COUNT)"
    exit 1
fi

if [ ! -f "$JM_HOME/lib/activation-1.1.1.jar" ]; then
    echo "ERROR: lib/activation-1.1.1.jar missing (javax.activation runtime jar)"
    exit 1
fi
echo "OK: activation-1.1.1.jar found"

# 2) 真实运行打包产物（NewDriver 以 jar 位置推断 jmeter.home，装载 ../lib 与 ../lib/ext）
VERSION_OUT="$(cd "$JM_HOME/bin" && java -jar ApacheJMeter.jar --version 2>&1)" || {
    echo "ERROR: java -jar ApacheJMeter.jar --version failed"
    echo "$VERSION_OUT"
    exit 1
}
echo "$VERSION_OUT"
if ! printf '%s\n' "$VERSION_OUT" | grep -q "Version 2.13"; then
    echo "ERROR: JMeter did not report Version 2.13"
    exit 1
fi
echo "OK: ApacheJMeter.jar --version reports 2.13"

# 3) 消费者反射断言（classpath = 主 jar + lib/*.jar + lib/ext/*.jar）
CP="$JAR_MAIN"
for j in "$JM_HOME"/lib/*.jar; do
    [ -f "$j" ] && CP="$CP:$j"
done
for j in "$JM_HOME"/lib/ext/*.jar; do
    [ -f "$j" ] && CP="$CP:$j"
done
TEST_SRC="$(dirname "$0")/TestApacheJMeter.java"

if ! javac -encoding UTF-8 -cp "$CP" "$TEST_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed"
    exit 1
fi
echo "OK: TestApacheJMeter.java compiled successfully"

output="$(java -cp "$CP:$TMP_DIR" TestApacheJMeter 2>&1)" || {
    echo "ERROR: Java consumer execution failed"
    echo "$output"
    exit 1
}

if printf '%s\n' "$output" | grep -q "^PASS:"; then
    printf '%s\n' "$output"
    echo "=== All tests passed ==="
    exit 0
else
    echo "ERROR: Test did not produce PASS output"
    printf '%s\n' "$output"
    exit 1
fi
