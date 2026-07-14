#!/bin/bash
# ============================================================================
# build_ohos.sh — CDO (Climate Data Operators) for OpenHarmony PC aarch64
#
# 功能:
#   1. 自动下载 CDO 官方源码
#   2. 适配 OpenHarmony PC aarch64 交叉编译
#   3. 打包为扁平结构 (bin/ lib/ share/ 在顶层)
#
# 用法:
#   bash build_ohos.sh [version] [prefix]
#
# 环境变量:
#   CONFIG_SHELL  — configure 解释器 (默认 /data/service/hnp/bin/bash)
#   CC / CXX      — C/C++ 编译器 (默认 clang / clang++)
#   AR / RANLIB   — 归档工具 (默认 llvm-ar / llvm-ranlib)
#   JOBS          — 并行编译任务数 (默认 1, OHOS 推荐 -j1)
#
# 依赖:
#   - Clang 15+ (aarch64-linux-ohos 目标)
#   - llvm-ar / llvm-ranlib
#   - curl / wget
#   - GNU patch
# ============================================================================

set -euo pipefail

# ---- 版本与路径 ------------------------------------------------------------
CDO_VERSION="${1:-2.4.0}"
PREFIX="${2:-$HOME/usr/local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$HOME/tmp/build-cdo-$$"
STAGING_DIR="$BUILD_DIR/staging"
PKG_DIR="$BUILD_DIR/pkg"
PATCH_DIR="$SCRIPT_DIR/patches"

# ---- 工具链 ----------------------------------------------------------------
CONFIG_SHELL="${CONFIG_SHELL:-/data/service/hnp/bin/bash}"
CC="${CC:-clang}"
CXX="${CXX:-clang++}"
AR="${AR:-llvm-ar}"
RANLIB="${RANLIB:-llvm-ranlib}"
JOBS="${JOBS:-1}"

OHOS_TARGET="aarch64-linux-ohos"
CFLAGS="-fPIC -O2 -target $OHOS_TARGET"
CXXFLAGS="-fPIC -O2 -target $OHOS_TARGET"
LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld"

# ---- 源码 URL --------------------------------------------------------------
# CDO 官方发布页: https://code.mpimet.mpg.de/projects/cdo/files
# 备用: https://github.com/ClimateDataOps/CDO/releases
CDO_URL="https://code.mpimet.mpg.de/attachments/download/29670/cdo-${CDO_VERSION}.tar.gz"
CDO_URL_FALLBACK="https://github.com/ClimateDataOps/CDO/releases/download/v${CDO_VERSION}/cdo-${CDO_VERSION}.tar.gz"

# ============================================================================
# 辅助函数
# ============================================================================

log()  { printf "\033[1;32m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*" >&2; exit 1; }

cleanup() {
    log "清理临时目录: $BUILD_DIR"
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

download() {
    local url="$1" dest="$2"
    if command -v curl &>/dev/null; then
        curl -fSL -o "$dest" "$url" || return 1
    elif command -v wget &>/dev/null; then
        wget -O "$dest" "$url" || return 1
    else
        err "需要 curl 或 wget"
    fi
}

apply_patches() {
    local src_dir="$1"
    if [ -d "$PATCH_DIR" ]; then
        for patch_file in "$PATCH_DIR"/*.patch; do
            [ -f "$patch_file" ] || continue
            log "应用补丁: $(basename "$patch_file")"
            patch -d "$src_dir" -p1 < "$patch_file" || warn "补丁 $(basename "$patch_file") 应用失败"
        done
    fi
}

# ============================================================================
# 主流程
# ============================================================================

log "=== CDO $CDO_VERSION  OpenHarmony aarch64 交叉编译 ==="
log "编译器: $CC / $CXX"
log "目标:   $OHOS_TARGET"
log "安装到: $PREFIX"

mkdir -p "$BUILD_DIR" "$STAGING_DIR" "$PKG_DIR"

# ---- Step 1: 下载源码 ------------------------------------------------------
log "Step 1/6: 下载 CDO $CDO_VERSION 源码..."
SOURCE_TAR="$BUILD_DIR/cdo-${CDO_VERSION}.tar.gz"

if ! download "$CDO_URL" "$SOURCE_TAR"; then
    warn "主 URL 下载失败，尝试备用 URL..."
    download "$CDO_URL_FALLBACK" "$SOURCE_TAR" || err "所有下载源均失败"
fi

# ---- Step 2: 解压 ----------------------------------------------------------
log "Step 2/6: 解压源码..."
tar xzf "$SOURCE_TAR" -C "$BUILD_DIR"
SOURCE_DIR="$BUILD_DIR/cdo-${CDO_VERSION}"

if [ ! -d "$SOURCE_DIR" ]; then
    # 尝试自动检测解压后的目录名
    SOURCE_DIR=$(find "$BUILD_DIR" -maxdepth 1 -type d -name "cdo*" | head -1)
    [ -n "$SOURCE_DIR" ] || err "无法找到解压后的源码目录"
fi

log "源码目录: $SOURCE_DIR"

# ---- Step 3: 打补丁 (config.guess/config.sub) ------------------------------
log "Step 3/6: 为 config.guess/config.sub 打 HarmonyOS 补丁..."

# 查找并修补所有 config.guess 和 config.sub
find "$SOURCE_DIR" -name "config.guess" -o -name "config.sub" | while read -r f; do
    log "  修补: $f"
    case "$(basename "$f")" in
        config.guess)
            # 插入 OHOS 检测
            if ! grep -q "__OHOS__" "$f" 2>/dev/null; then
                perl -i -pe '
                    if (!defined $ohos_inserted && /defined\(__ANDROID__\)/) {
                        print;
                        print "#elif defined(__OHOS__)\n    LIBC=ohos\n";
                        $ohos_inserted = 1;
                    } else { print; }
                ' "$f" 2>/dev/null || warn "    config.guess OHOS 检测补丁失败"
            fi
            if ! grep -q "HarmonyOS" "$f" 2>/dev/null; then
                # 在 NetBSD 之前插入 HarmonyOS case
                perl -i -pe '
                    if (!defined $harmony_inserted && /^\s+\*\:NetBSD\:\*\:\*\)/) {
                        print "    *:HarmonyOS:*:*)\n";
                        print "\tcase \$UNAME_MACHINE in\n";
                        print "\t    aarch64|arm64) MACHINE=aarch64 ;;\n";
                        print "\t    armv7*|armv8*) MACHINE=arm ;;\n";
                        print "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n";
                        print "\t    i?86)         MACHINE=i686 ;;\n";
                        print "\t    *)            MACHINE=\"\$UNAME_MACHINE\" ;;\n";
                        print "\tesac\n";
                        print "\tGUESS=\${MACHINE}-unknown-linux-ohos\n";
                        print "\t;;\n\n";
                        $harmony_inserted = 1;
                    }
                    print;
                ' "$f" 2>/dev/null || warn "    config.guess HarmonyOS case 补丁失败"
            fi
            ;;
        config.sub)
            # 插入 ohos-linux triplet
            if ! grep -q "ohos-linux" "$f" 2>/dev/null; then
                perl -i -pe '
                    if (!defined $triplet_inserted && /^\s+android-linux\)/) {
                        print;
                        $triplet_inserted = 1;
                    } elsif ($triplet_inserted && /^\s+basic_os=linux-android/) {
                        print;
                        print "\tohos-linux)\n";
                        print "\t\tbasic_machine=\$field1-unknown\n";
                        print "\t\tbasic_os=linux-ohos\n";
                        print "\t\t;;\n";
                        $triplet_inserted = 2;
                    } else { print; }
                ' "$f" 2>/dev/null || warn "    config.sub triplet 补丁失败"
            fi
            # 在 OS 列表中添加 ohos*
            if ! grep -q "ohos\*" "$f" 2>/dev/null; then
                perl -i -pe 's/(gnu\*\s*\|\s*android\*)/$1 | ohos*/' "$f" 2>/dev/null || warn "    config.sub OS list 补丁失败"
            fi
            # 在 kernel-OS 列表中添加 linux-ohos
            if ! grep -q "linux-ohos" "$f" 2>/dev/null; then
                perl -i -pe 's/(linux-uclibc\*[\s\/-]*\))/$1| linux-ohos*)/' "$f" 2>/dev/null || warn "    config.sub kernel list 补丁失败"
            fi
            ;;
    esac
done

# 应用自定义补丁（如果有）
apply_patches "$SOURCE_DIR"

# ---- Step 4: 配置 ----------------------------------------------------------
log "Step 4/6: 配置 CDO (autotools)..."

cd "$SOURCE_DIR"

# 确保 autotools 辅助脚本可执行
chmod +x configure config.guess config.sub 2>/dev/null || true

# OHOS 适配: 使用 CONFIG_SHELL 并设置交叉编译参数
CONFIG_SHELL="$CONFIG_SHELL" \
CC="$CC" \
CXX="$CXX" \
AR="$AR" \
RANLIB="$RANLIB" \
CFLAGS="$CFLAGS" \
CXXFLAGS="$CXXFLAGS" \
LDFLAGS="$LDFLAGS" \
"$CONFIG_SHELL" ./configure \
    --host="$OHOS_TARGET" \
    --prefix="$STAGING_DIR" \
    --enable-static \
    --disable-shared \
    --without-netcdf \
    --without-hdf5 \
    --without-szlib \
    --disable-dependency-tracking \
    --disable-doc \
    --disable-dependency-tracking \
    || err "configure 失败"

# ---- Step 5: 编译 ----------------------------------------------------------
log "Step 5/6: 编译 CDO (make -j$JOBS)..."

# R9: 推荐 -j1，但允许通过 JOBS 环境变量覆盖
make -j"$JOBS" || err "make 构建失败"

# ---- Step 6: 安装与打包 ----------------------------------------------------
log "Step 6/6: 安装并打包..."

make install || err "make install 失败"

# 确认二进制存在
if [ -f "$STAGING_DIR/bin/cdo" ]; then
    log "✅ CDO 编译成功: $STAGING_DIR/bin/cdo"
    file "$STAGING_DIR/bin/cdo"
else
    warn "未找到 cdo 二进制，检查安装路径..."
    find "$STAGING_DIR" -type f -name "cdo*" 2>/dev/null
fi

# 打包为扁平结构（bin/ lib/ share/ 在顶层）
PKG_NAME="cdo-${CDO_VERSION}-ohos-aarch64"
PKG_TAR="$PKG_DIR/${PKG_NAME}.tar.gz"

mkdir -p "$PKG_DIR/$PKG_NAME"
cp -r "$STAGING_DIR"/* "$PKG_DIR/$PKG_NAME/" 2>/dev/null || true

# 如果 staging 是扁平结构，直接打包
cd "$PKG_DIR"
tar czf "$PKG_TAR" "$PKG_NAME" 2>/dev/null || {
    # 如果 staging 是 /usr/local 风格，提取 bin/lib/share
    cd "$STAGING_DIR"
    tar czf "$PKG_TAR" bin/ lib/ share/ 2>/dev/null || warn "打包警告: 部分目录可能为空"
}

log "✅ 包已创建: $PKG_TAR"

# 安装到目标目录
log "安装到: $PREFIX"
mkdir -p "$PREFIX"
cp -r "$STAGING_DIR"/* "$PREFIX/" 2>/dev/null || true

# 设置权限
chmod +x "$PREFIX/bin/"* 2>/dev/null || true

# PATH 提示
if ! grep -q 'usr/local/bin' "$HOME/.zshrc" 2>/dev/null; then
    warn "建议将 $PREFIX/bin 加入 PATH:"
    warn "  echo 'export PATH=\"$PREFIX/bin:\$PATH\"' >> ~/.zshrc"
fi

# ---- 验证 ----------------------------------------------------------------
log "=== 验证 ==="
if [ -f "$PREFIX/bin/cdo" ]; then
    # 预触发安全弹窗
    "$PREFIX/bin/cdo" --version 2>/dev/null || true
    log "✅ CDO $CDO_VERSION 安装完成!"
    log "   运行: $PREFIX/bin/cdo --version"
else
    warn "⚠️  cdo 二进制未安装到 $PREFIX/bin"
    warn "   请检查编译日志"
fi

echo ""
echo "=============================="
echo " CDO $CDO_VERSION 构建完成"
echo " 目标:   $OHOS_TARGET"
echo " 安装到: $PREFIX"
echo " 包:     $PKG_TAR"
echo "=============================="