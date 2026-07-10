#!/usr/bin/zsh
# ci/conan/setup.sh — Conan environment initialization
#
# Contract: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_ci/blob/main/docs/CI_SCRIPT_SPEC.md
# Exit code: 0=success, non-0=failure (blocks subsequent steps)
# Timeout: 20 minutes
#
# Must complete:
#   - Detect/install Conan (pip install conan)
#   - Verify conan remote (预部署, 不做注册/认证)
#   - Ensure ohos-aarch64 profile exists
#   - Set conan configuration

set -euo pipefail

# ── Path resolution ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CI_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

echo "[step] Conan environment setup..."

# ── 0. Check Python sqlite3 module (CI environment dependency) ──
# HNP Python environment may have broken sqlite3 (missing libsqlite3.so.0)
# This will cause conan to fail at startup. Detect and try to fix.
if ! python3 -c "import sqlite3" 2>/dev/null; then
    echo "[warn] Python sqlite3 module broken (missing libsqlite3.so.0)"
    echo "[step] Attempting to fix sqlite3 dependency..."
    
    # Find libsqlite3.so.0 in system and add to LD_LIBRARY_PATH
    SQLITE3_LIB=""
    for lib_path in \
        "/usr/lib/libsqlite3.so.0" \
        "/usr/lib64/libsqlite3.so.0" \
        "/lib/libsqlite3.so.0" \
        "/lib64/libsqlite3.so.0" \
        "/data/service/hnp/lib/libsqlite3.so.0" \
        "/system/lib/libsqlite3.so.0" \
        "/system/lib64/libsqlite3.so.0"; do
        if [ -f "$lib_path" ]; then
            SQLITE3_LIB="$lib_path"
            lib_dir=$(dirname "$lib_path")
            echo "[step] Found libsqlite3.so.0 at: $lib_path"
            export LD_LIBRARY_PATH="$lib_dir:$LD_LIBRARY_PATH"
            break
        fi
    done
    
    # If still not found, try installing via package manager
    if [ -z "$SQLITE3_LIB" ]; then
        echo "[step] libsqlite3.so.0 not found, trying package manager..."
        if command -v apt-get &>/dev/null; then
            apt-get update -qq && apt-get install -y -qq libsqlite3-0 || true
        elif command -v yum &>/dev/null; then
            yum install -y -q sqlite-libs || true
        elif command -v dnf &>/dev/null; then
            dnf install -y -q sqlite-libs || true
        elif command -v opkg &>/dev/null; then
            opkg update && opkg install sqlite3 || true
        elif command -v pkg &>/dev/null; then
            pkg install -y sqlite3 || true
        fi
    fi
    
    # Re-check after attempting fix
    if ! python3 -c "import sqlite3" 2>/dev/null; then
        echo "[error] Failed to fix sqlite3 module - environment issue"
        echo "[error] Please contact CI maintainers to fix HNP Python environment"
        echo "[hint] Missing: libsqlite3.so.0"
        exit 1
    fi
    echo "[step] sqlite3 dependency fixed ✅"
fi

# ── 1. Detect/install Conan ──
# Check both that conan exists AND is functional (conan --version succeeds)
# If conan binary exists but is broken, force-reinstall to fix
if ! command -v conan &>/dev/null || ! conan --version &>/dev/null; then
    echo "[step] Conan not found or broken, (re)installing..."
    # 安装 OHOS 适配版 conan（私有 PyPI 提供，基线 2.29.1，已适配 OHOS 平台）
    # 不要钉死官方旧版本号，应从配置的 PyPI 源安装最新适配版
    # Use python3 -m pip to bypass potentially broken pip3 shebang
    # (HNP pip3/conan binaries may have shebangs pointing to non-existent
    #  build-machine paths with ^M line endings)
    python3 -m pip install --user --force-reinstall conan || {
        echo "[error] Failed to install conan"
        exit 1
    }
    # Ensure user-installed binaries are found before any broken HNP version
    export PATH="$HOME/.local/bin:$PATH"
fi

CONAN_VERSION=$(conan --version 2>/dev/null || echo "unknown")
echo "[step] Conan version: $CONAN_VERSION"

# ── 1b. Refresh stale settings.yml ──
# conan caches settings.yml on first run; if conan was upgraded (e.g. OHOS
# support added to default_settings.py), the cached file is stale and
# conan will reject os=OHOS. Delete it to force regeneration.
CONAN_HOME="${CONAN_HOME:-$HOME/.conan2}"
SETTINGS_FILE="$CONAN_HOME/settings.yml"
if [ -f "$SETTINGS_FILE" ]; then
    if ! grep -q "OHOS" "$SETTINGS_FILE" 2>/dev/null; then
        echo "[step] Refreshing stale settings.yml (missing OHOS enum)"
        rm -f "$SETTINGS_FILE" "$SETTINGS_FILE.orig"
    fi
fi

# ── 2. Verify conan remote (预部署校验) ──
# Conan 配置 (remotes.json, profiles, settings.yml) 由 worker app 文件预部署到 ~/.conan2/
# setup.sh 不做 remote 注册/认证, 仅校验 remote 已就绪
CONAN_REMOTE_NAME="${CONAN_REMOTE_NAME:-ohpcd}"

# Disable conancenter — these are private CI builds, no external deps needed
if conan remote list 2>/dev/null | grep -q "^conancenter:"; then
    echo "[step] Disabling conancenter (private CI, not needed)"
    conan remote disable conancenter 2>/dev/null || true
fi

if ! conan remote list 2>/dev/null | grep -q "^${CONAN_REMOTE_NAME}:"; then
    echo "[error] remote '${CONAN_REMOTE_NAME}' 不存在, 请检查 worker app 预部署"
    exit 1
fi
echo "[step] remote 已就绪: ${CONAN_REMOTE_NAME}"

# ── 3. Ensure ohos-aarch64 profile exists ──
PROFILE_NAME="${CONAN_PROFILE:-ohos-aarch64}"
PROFILE_DIR="$REPO_ROOT/ci/conan/profiles"
PROFILE_FILE="$PROFILE_DIR/$PROFILE_NAME"

if conan profile list 2>/dev/null | grep -q "^${PROFILE_NAME}$"; then
    echo "[step] Profile ${PROFILE_NAME} already exists"
else
    if [ -f "$PROFILE_FILE" ]; then
        echo "[step] Importing profile from ${PROFILE_FILE}"
        conan profile import "$PROFILE_FILE" 2>/dev/null || true
    else
        echo "[step] Creating default ${PROFILE_NAME} profile..."
        conan profile detect --name "${PROFILE_NAME}" 2>/dev/null || true
    fi
fi

# If profile file exists in repo, use it directly via -pr flag
if [ -f "$PROFILE_FILE" ]; then
    echo "[step] Profile file available at: ${PROFILE_FILE}"
fi

# ── 4. Set conan configuration ──
# Enable revisions (Conan 2.x default, but be explicit)
conan config set general.revisions_enabled=1 2>/dev/null || true

echo "[step] Conan environment ready ✅"
echo "[step]   remote: ${CONAN_REMOTE_NAME}"
echo "[step]   profile: ${PROFILE_NAME}"
echo "[step]   conan: ${CONAN_VERSION}"
