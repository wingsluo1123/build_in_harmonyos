#!/usr/bin/env bash
# test.sh — keycloak-config-cli 消费者视角真机验证
# 真实执行 fat jar CLI（java -jar --help）+ fat jar 结构断言（R34 实质性验证）

set -euo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"

# 解析 JAVA_HOME：优先环境变量，其次检测常见 JDK 安装路径（真机候选列表）
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    for candidate in \
        /storage/Users/currentUser/bishengjdk17 \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
        "$HOME/bishengjdk17" \
        "$HOME/usr/local/bishengjdk17" \
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

JAR_PATH="$PKG_DIR/libexec/keycloak-config-cli.jar"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== keycloak-config-cli 消费者视角真机验证 ==="

# A1: JAR 存在
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: keycloak-config-cli JAR not found at $JAR_PATH"
    exit 1
fi
echo "OK A1: JAR found at $JAR_PATH"

# A2: fat jar 体积（spring-boot 打包后 > 10MB）
SIZE=$(wc -c < "$JAR_PATH")
if [ "$SIZE" -lt 10485760 ]; then
    echo "ERROR: JAR too small ($SIZE bytes) — not a fat jar?"
    exit 1
fi
echo "OK A2: fat jar size ${SIZE} bytes"

# A3: unzip -l 清单一次性落盘（禁 unzip|grep 管道：keycloak-metrics SIGPIPE 竞态教训）
if ! unzip -l "$JAR_PATH" > "$TMP_DIR/jar-listing.txt" 2>/dev/null; then
    echo "ERROR: unzip -l failed on $JAR_PATH"
    exit 1
fi
echo "OK A3: jar listing extracted ($(wc -l < "$TMP_DIR/jar-listing.txt") lines)"

# A4: 主类存在（KeycloakConfigApplication）
if ! grep -q "BOOT-INF/classes/de/adorsys/keycloak/config/KeycloakConfigApplication.class" "$TMP_DIR/jar-listing.txt"; then
    echo "ERROR: KeycloakConfigApplication.class missing from fat jar"
    exit 1
fi
echo "OK A4: BOOT-INF/classes/de/adorsys/keycloak/config/KeycloakConfigApplication.class present"

# A5: keycloak-admin-client 打包核验
if ! grep -q "BOOT-INF/lib/keycloak-admin-client-26.0.4.jar" "$TMP_DIR/jar-listing.txt"; then
    echo "ERROR: keycloak-admin-client-26.0.4.jar missing from fat jar"
    exit 1
fi
echo "OK A5: BOOT-INF/lib/keycloak-admin-client-26.0.4.jar present"

# A6: spring-boot 运行时打包核验
if ! grep -q "BOOT-INF/lib/spring-boot-3.2.9.jar" "$TMP_DIR/jar-listing.txt"; then
    echo "ERROR: spring-boot-3.2.9.jar missing from fat jar"
    exit 1
fi
echo "OK A6: BOOT-INF/lib/spring-boot-3.2.9.jar present"

# A7: javers-core 打包核验
if ! grep -q "BOOT-INF/lib/javers-core-7.6.3.jar" "$TMP_DIR/jar-listing.txt"; then
    echo "ERROR: javers-core-7.6.3.jar missing from fat jar"
    exit 1
fi
echo "OK A7: BOOT-INF/lib/javers-core-7.6.3.jar present"

# A8: Spring Boot loader Main-Class（ZIP layout → PropertiesLauncher）+ Start-Class
unzip -p "$JAR_PATH" META-INF/MANIFEST.MF > "$TMP_DIR/manifest.txt" 2>/dev/null
if ! grep -q "^Main-Class: org.springframework.boot.loader.launch.PropertiesLauncher" "$TMP_DIR/manifest.txt" \
   || ! grep -q "^Start-Class: de.adorsys.keycloak.config.KeycloakConfigApplication" "$TMP_DIR/manifest.txt"; then
    echo "ERROR: MANIFEST Main-Class/Start-Class mismatch"
    cat "$TMP_DIR/manifest.txt"
    exit 1
fi
echo "OK A8: Main-Class = PropertiesLauncher (ZIP layout), Start-Class = KeycloakConfigApplication"

# A9: 真实执行 CLI（无配置）：Spring 启动 + 配置绑定引擎生效，
#     预期确定性失败签名 import.files.locations must not be null（rc=1）
NOCONF_RC=0
NOCONF_OUTPUT=$(timeout 180 java -jar "$JAR_PATH" 2>&1) || NOCONF_RC=$?
if [ "$NOCONF_RC" -eq 0 ]; then
    echo "ERROR: unexpected success without required configuration"
    exit 1
fi
if ! echo "$NOCONF_OUTPUT" | grep -q "import.files.locations" \
   || ! echo "$NOCONF_OUTPUT" | grep -q "must not be null"; then
    echo "ERROR: expected config-binding failure signature missing:"
    echo "$NOCONF_OUTPUT"
    exit 1
fi
echo "OK A9: real execution boots Spring and enforces import.files.locations (rc=$NOCONF_RC)"

# A10: README 6.4.0 规范用法真实执行（M7 实测签名）：
#      --key=value 配置 + 上游示例 realm 配置（contrib/example-config/moped.json）
#      预期：Spring 启动 → import 阶段真实发起 Keycloak REST 连接
#      （127.0.0.1:59999 封闭端口 → Connection refused，rc=1）
#      注意：include-hidden-files 使 fixture 在隐藏目录（如 .atomcode）下也可解析
CFG_JSON="$(dirname "$0")/moped.json"
RUN_RC=0
RUN_OUTPUT=$(timeout 240 java -jar "$JAR_PATH" \
    --keycloak.url=http://127.0.0.1:59999 \
    --keycloak.ssl-verify=true \
    --keycloak.user=admin \
    --keycloak.password=admin \
    --import.files.include-hidden-files=true \
    --import.files.locations="$CFG_JSON" 2>&1) || RUN_RC=$?
if ! echo "$RUN_OUTPUT" | grep -q "Starting KeycloakConfigApplication v6.4.0"; then
    echo "ERROR: application did not start (version banner missing):"
    echo "$RUN_OUTPUT"
    exit 1
fi
if ! echo "$RUN_OUTPUT" | grep -q "Error during Keycloak import" \
   || ! echo "$RUN_OUTPUT" | grep -q "Connect to 127.0.0.1:59999" \
   || ! echo "$RUN_OUTPUT" | grep -q "Connection refused"; then
    echo "ERROR: expected Keycloak connection attempt signature missing:"
    echo "$RUN_OUTPUT"
    exit 1
fi
echo "OK A10: real execution reaches Keycloak import stage, REST connection attempted (rc=$RUN_RC)"
echo "PASS"
echo "=== All tests passed ==="
