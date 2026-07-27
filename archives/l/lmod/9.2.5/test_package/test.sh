#!/data/service/hnp/bin/bash
# test_package/test.sh — 上游功能测试 for lmod
# 覆盖 module 命令的核心功能：version/help/avail/list/load/unload/purge
# 在 conanrun 环境下运行（PATH 包含已安装的 bin/）
set -euo pipefail

# Source lmod init to use the shell function wrapper for module command
# module() { eval "\$($LMOD_CMD bash "\$@")"; }
# Lmod 9.x make install puts init scripts at <prefix>/lmod/<version>/init/bash
if [ -n "${LMOD_PKG:-}" ] && [ -f "$LMOD_PKG/lmod/9.2.5/init/bash" ]; then
    source "$LMOD_PKG/lmod/9.2.5/init/bash"
elif [ -n "${LMOD_DIR:-}" ] && [ -f "$LMOD_DIR/init/bash" ]; then
    source "$LMOD_DIR/init/bash"
elif [ -n "${LMOD_PKG:-}" ] && [ -f "$LMOD_PKG/init/bash" ]; then
    source "$LMOD_PKG/init/bash"
fi

PASS=0
FAIL=0
TOTAL=0

check() {
    desc="$1"
    TOTAL=$((TOTAL + 1))
    shift
    # 捕获退出码：set +e 防止 eval 提前终止，$? 获取真实退出码
    set +e
    eval "$@" > /dev/null 2>&1
    rc=$?
    set -e
    if [ $rc -eq 0 ]; then
        echo "  ✅ PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  ❌ FAIL: $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "═══ lmod 上游功能测试 ═══"
echo ""

# ── 1. module --version ──
echo "[group] 1. 版本信息"
check "module --version 返回版本号" \
    'module --version 2>&1 | grep -i "modules.*based on lua\|Lmod\|9\." > /dev/null 2>&1'

# ── 2. module --help ──
echo "[group] 2. 帮助信息"
check "module --help 显示帮助" \
    'module --help 2>&1 | grep -i "usage\|help\|avail\|list\|load\|unload" > /dev/null 2>&1'

# ── 3. module avail ──
echo "[group] 3. 模块列表"
check "module avail 可列出模块" \
    'module avail 2>&1'
check "module avail 输出非空" \
    'test -n "$(module avail 2>&1 || true)"'

# ── 4. module list ──
echo "[group] 4. 已加载模块"
check "module list 不崩溃" \
    'module list 2>&1'

# ── 5. module 子命令完整性 ──
echo "[group] 5. 子命令可用性"
check "module help 子命令正常" \
    'module help 2>&1 | sed -n "1,5p"'
check "module spider 可用" \
    'module spider 2>&1'

# ── 6. module load/unload 循环 ──
echo "[group] 6. 模块加载/卸载"
# 创建测试用 modulefile
TEST_MODULE_DIR="$HOME/.lmod_test_modules"
TEST_MODULE="$TEST_MODULE_DIR/test_app/1.0.lua"
mkdir -p "$(dirname "$TEST_MODULE")"
cat > "$TEST_MODULE" << 'LUAEOF'
whatis("测试模块 - lmod 功能验证")
setenv("TEST_LMOD_VAR", "hello_lmod")
LUAEOF

check "module use 添加自定义路径" \
    'module use "$TEST_MODULE_DIR"'
check "module avail 能看到测试模块" \
    'module avail 2>&1 | grep "test_app/1.0" > /dev/null 2>&1'
check "module load 加载测试模块" \
    'module load test_app/1.0'
check "load 后环境变量生效" \
    'test "${TEST_LMOD_VAR:-}" = "hello_lmod"'
check "module list 显示已加载模块" \
    'module list 2>&1 | grep -i "test_app" > /dev/null 2>&1'
check "module unload 卸载测试模块" \
    'module unload test_app/1.0'
check "unload 后环境变量已清除" \
    'test -z "${TEST_LMOD_VAR:-}"'

# 清理
check "module unuse 移除测试路径" \
    'module unuse "$TEST_MODULE_DIR"'
rm -rf "$TEST_MODULE_DIR"

# ── 7. module purge ──
echo "[group] 7. module purge"
check "module purge 不崩溃" \
    'module purge 2>&1'

# ── 8. ml 别名（shorthand） ──
echo "[group] 8. ml shorthand"
if command -v ml >/dev/null 2>&1; then
    check "ml 别名可用" \
        'ml --version 2>&1 | grep -i "lmod\|9\." > /dev/null 2>&1'
else
    echo "  ⏭️  SKIP: ml 别名未安装（非阻塞）"
fi

# ── 9. 环境变量一致性 ──
echo "[group] 9. 环境变量"
check "LMOD_VERSION 已设置" \
    'test -n "${LMOD_VERSION:-}"'
check "LMOD_DIR 已设置" \
    'test -n "${LMOD_DIR:-}"'
check "LMOD_PKG 已设置" \
    'test -n "${LMOD_PKG:-}"'

# ── 总结 ──
echo ""
echo "═══ 测试总结 ═══"
echo "  总数: $TOTAL"
echo "  通过: $PASS"
echo "  失败: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "❌ 有 $FAIL 个测试失败"
    exit 1
else
    echo "✅ 全部通过 ($PASS/$TOTAL)"
    exit 0
fi
