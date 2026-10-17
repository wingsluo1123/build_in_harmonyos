#!/data/service/hnp/bin/bash
# test_package/test.sh — wayland-utils 1.2.0 层 2 消费者 CLI 测试。
#
# 执行安装出的 bin/wayland-info（经 conanrun PATH 解析；RUNPATH 已嵌入
# 二进制指向 wayland 包 libdir），断言真实退出码与诊断文本（上游
# wayland-info.c parse_cmdline 源码实证：--help/-h 走 stderr 且
# EXIT_SUCCESS；未知选项/缺参 EXIT_FAILURE；无合成器时
# wl_display_connect 失败返回 -1）。附 readelf 级 ELF 属性断言。
#
# 20 项断言，任一失败退出码 1。
pass=0
fail=0

ok()   { printf '        [ok]   %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '        [fail] %s\n' "$1"; fail=$((fail + 1)); }

check_eq() {
    if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2', want '$3')"; fi
}

check_contains() {
    case "$2" in
        *"$3"*) ok "$1" ;;
        *)      bad "$1 (missing: $3)" ;;
    esac
}

WAYLAND_LIBDIR="${1:-}"

echo "[test] wayland-info binary: $(command -v wayland-info)"

# ── 1. --help 退出码 0（EXIT_SUCCESS），usage 走 stderr ────────────────
OUT="$(wayland-info --help 2>&1)"; RC=$?
check_eq "--help exits 0" "$RC" "0"
check_contains "--help prints usage banner" "$OUT" "Usage: "
check_contains "--help documents -h|--help" "$OUT" "-h|--help"
check_contains "--help documents -i|--interface" "$OUT" "-i|--interface"

# ── 2. -h 短选项同款 ───────────────────────────────────────────────────
OUT="$(wayland-info -h 2>&1)"; RC=$?
check_eq "-h exits 0" "$RC" "0"
check_contains "-h prints usage banner" "$OUT" "Usage: "

# ── 3. 未知选项被拒绝（EXIT_FAILURE + "Unknown option"） ───────────────
OUT="$(wayland-info --no-such-option 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "unknown option exits non-zero ($RC)" \
                || bad "unknown option should fail but exited 0"
check_contains "unknown option reports 'Unknown option'" "$OUT" "Unknown option"

# ── 4. -i 缺参被拒绝（"Missing interface name"） ───────────────────────
OUT="$(wayland-info --interface 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "--interface without value exits non-zero ($RC)" \
                || bad "--interface without value should fail but exited 0"
check_contains "missing interface name reported" "$OUT" "Missing interface name"

# ── 5. 无参运行：无合成器环境，wl_display_connect 失败 ─────────────────
#    （优雅失败契约：stderr 打印 "failed to create display" 并返回 255；
#     沙箱/CI 无 Wayland 合成器，这正是此环境的预期行为）
OUT="$(wayland-info 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "no-compositor run exits non-zero ($RC)" \
                || bad "no-compositor run should fail but exited 0"
check_contains "no-compositor reports 'failed to create display'" "$OUT" "failed to create display"

# ── 6. ELF 属性（readelf 级） ───────────────────────────────────────────
BIN="$(command -v wayland-info)"
EH="$(readelf -h "$BIN" 2>/dev/null)"
check_contains "ELF machine is AArch64" "$EH" "AArch64"
check_contains "ELF type is PIE/DYN" "$EH" "DYN"
PH="$(readelf -lW "$BIN" 2>/dev/null)"
check_contains "NX stack (GNU_STACK RW, no E)" "$(printf '%s' "$PH" | grep GNU_STACK)" "RW "
check_contains "RELRO segment present" "$PH" "GNU_RELRO"
DY="$(readelf -d "$BIN" 2>/dev/null)"
check_contains "NEEDED libwayland-client.so.0" "$DY" "libwayland-client.so.0"
check_contains "NEEDED libc.so" "$DY" "libc.so"

# ── 7. RUNPATH 指向 wayland 包 libdir（裸跑冒烟的关键） ────────────────
if [ -n "$WAYLAND_LIBDIR" ]; then
    check_contains "RUNPATH points at wayland package libdir" "$DY" "$WAYLAND_LIBDIR"
else
    ok "RUNPATH check skipped (no libdir argument)"
fi

# ── 8. 裸跑冒烟（无 conanrun env，等价 CI L2 场景） ────────────────────
env -i "$BIN" --help >/dev/null 2>&1
check_eq "bare-run --help (no conanrun env) exits 0" "$?" "0"

echo "[test] test_package layer-2 assertions: $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
