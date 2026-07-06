#!/usr/bin/zsh
# ci/conan/setup.sh — Conan environment initialization
#
# Contract: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_ci/blob/main/docs/CI_SCRIPT_SPEC.md
# Exit code: 0=success, non-0=failure (blocks subsequent steps)
# Timeout: 20 minutes
#
# Must complete:
#   - Detect/install Conan (pip install conan)
#   - Detect/install Rust toolchain (cargo/rustc for Cargo-based packages)
#   - Verify conan remote (预部署, 不做注册/认证)
#   - Ensure ohos-aarch64 profile exists
#   - Set conan configuration

set -euo pipefail

# ── Path resolution ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CI_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

echo "[step] Conan environment setup..."

# ── 1. Detect/install Conan ──
if ! command -v conan &>/dev/null; then
    echo "[step] Conan not found, installing..."
    # 安装 OHOS 适配版 conan（私有 PyPI 提供，基线 2.29.1，已适配 OHOS 平台）
    # 不要钉死官方旧版本号，应从配置的 PyPI 源安装最新适配版
    pip3 install conan || {
        echo "[error] Failed to install conan"
        exit 1
    }
fi

CONAN_VERSION=$(conan --version 2>/dev/null || echo "unknown")
echo "[step] Conan version: $CONAN_VERSION"

# ── 1b. Detect/install Rust toolchain (for Cargo-based packages) ──
# CI 环境可能没有预装 cargo/rustc，需要自动安装。
# 检测顺序: PATH → ~/.harmonybrew/bin → ~/.cargo/bin → rustup 安装
if command -v cargo &>/dev/null; then
    echo "[step] Cargo already in PATH"
else
    echo "[step] Cargo not found, checking alternative locations..."
    _cargo_found=false

    # Check harmonybrew installation
    if [ -x "$HOME/.harmonybrew/bin/cargo" ]; then
        echo "[step] Found cargo via harmonybrew: $HOME/.harmonybrew/bin"
        export PATH="$HOME/.harmonybrew/bin:$PATH"
        _cargo_found=true
    fi

    # Check existing rustup installation (installed but not sourced)
    if [ "$_cargo_found" = false ] && [ -x "$HOME/.cargo/bin/cargo" ]; then
        echo "[step] Found cargo in ~/.cargo/bin (not sourced)"
        source "$HOME/.cargo/env" 2>/dev/null || export PATH="$HOME/.cargo/bin:$PATH"
        _cargo_found=true
    fi

    # Install via rustup if still not found
    if [ "$_cargo_found" = false ]; then
        echo "[step] Installing Rust via rustup..."
        # SSL cert workaround for OHOS (curl/SSL needs explicit cert path)
        _cert_pem="$HOME/usr/local/ssl/cert.pem"
        if [ -f "$_cert_pem" ]; then
            export SSL_CERT_FILE="$_cert_pem"
            export REQUESTS_CA_BUNDLE="$_cert_pem"
        fi

        # Download and run rustup-init with sh (not zsh — rustup expects sh)
        # -y: accept defaults, --default-toolchain stable: install stable Rust
        _rustup_url="https://sh.rustup.rs"
        if command -v curl &>/dev/null; then
            curl --proto '=https' --tlsv1.2 -sSf "$_rustup_url" | sh -s -- -y --default-toolchain stable
        elif command -v wget &>/dev/null; then
            wget -qO- "$_rustup_url" | sh -s -- -y --default-toolchain stable
        else
            # Fallback: use Python to download
            python3 -c "
import urllib.request, ssl
ctx = ssl.create_default_context()
ctx.load_verify_locations('$_cert_pem') if __import__('os').path.exists('$_cert_pem') else None
urllib.request.urlretrieve('$_rustup_url', '/tmp/rustup-init.sh')
" && sh /tmp/rustup-init.sh -y --default-toolchain stable && rm -f /tmp/rustup-init.sh
        fi

        # Source the installed environment
        source "$HOME/.cargo/env" 2>/dev/null || export PATH="$HOME/.cargo/bin:$PATH"

        if ! command -v cargo &>/dev/null; then
            echo "[error] Rust installation failed — cargo still not found"
            exit 1
        fi
        echo "[step] Rust installed via rustup ✅"
    fi
fi

CARGO_VERSION=$(cargo --version 2>/dev/null || echo "not available")
RUSTC_VERSION=$(rustc --version 2>/dev/null || echo "not available")
echo "[step] Cargo: $CARGO_VERSION"
echo "[step] Rustc: $RUSTC_VERSION"

# ── 1c. Refresh stale settings.yml ──
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
echo "[step]   cargo: ${CARGO_VERSION}"
