#!/bin/sh
# pixelize 2.0.0-git20220108.d1f9da9 consumer test — real binary invocations.
#
# Usage: test.sh <pixelize-bin> <make_db-bin>
#
# Execution model (set by test_package/conanfile.py from the ELF header):
#   native   — the binaries match the test host (CI HarmonyOS PC worker):
#              exec them directly.
#   emulated — foreign-architecture host (x86_64 Linux dev box cross-building
#              for OHOS aarch64): PIXELIZE_RUNNER=qemu-aarch64, exec'd against
#              the OHOS guest sysroot (PIXELIZE_GUEST_ROOT) with the fortify/
#              compat shims (PIXELIZE_GUEST_PRELOAD, ':'-separated) preloaded
#              in the guest via -E.
#              Precedent: archives/v/vimpc/0.09.2, archives/m/musicpc/0.35,
#              archives/t/tasksh/1.2.0, archives/a/array-hash/0.7.2.
#
# 覆盖（两二进制 × 三条真实路径）：
#   1) pixelize --help → rc=0 且 usage 含 [image_file]（GOption 在 GTK
#      显示初始化前处理 --help，无头可跑）
#   2) make_db --help → rc=0 且 usage 含 [FILE...]
#   3) pixelize 未知选项 → GOption 拒绝 → main() else 分支
#      "Error: in parameters" + exit(1)
#   4) make_db 未知选项 → 同上
#   5) pixelize 无显示环境启动（broadway 后端，无 broadwayd）→
#      gtk_init_with_args 显示打开失败 → 同一 else 分支 exit(1)
#      （almanah/0.12.4 同款无头负向断言；同时证明 gtk/glib/gdk-pixbuf/
#      pango/cairo 动态链接链完整解析——加载器把全部共享库装进了进程）
#   6) make_db 无显示环境启动 → 同上
set -u

PIXELIZE="$1"
MAKEDB="$2"
pass=0
fail=0

ok() { pass=$((pass+1)); echo "ok - $1"; }
no() { fail=$((fail+1)); echo "NOT OK - $1"; }

# Command prefix for the emulated model. No quoting inside CMD_PREFIX on
# purpose: the paths are space-free by construction and the prefix is meant
# to word-split (POSIX sh has no arrays).
CMD_PREFIX=""
if [ -n "${PIXELIZE_RUNNER:-}" ]; then
    CMD_PREFIX="$PIXELIZE_RUNNER -L $PIXELIZE_GUEST_ROOT"
    if [ -n "${PIXELIZE_GUEST_PRELOAD:-}" ]; then
        CMD_PREFIX="$CMD_PREFIX -E LD_PRELOAD=$PIXELIZE_GUEST_PRELOAD"
    fi
fi

# run_bin <env-prefix> <binary> <args...> → 设置 out/rc（stdout+stderr 合并）
run_bin() {
    envpfx="$1"; bin="$2"; shift 2
    out=$(timeout 15 $envpfx $CMD_PREFIX "$bin" "$@" </dev/null 2>&1)
    rc=$?
}

# assert_rc_needle <expected-rc> <needle> <description> <env-prefix> <binary> <args...>
assert_rc_needle() {
    expected="$1"; needle="$2"; desc="$3"; envpfx="$4"; bin="$5"; shift 5
    run_bin "$envpfx" "$bin" "$@"
    if [ "$rc" -ne "$expected" ]; then
        no "$desc (expected rc=$expected, got rc=$rc)"
        echo "  output: $out"
    elif echo "$out" | grep -F -- "$needle" >/dev/null; then
        ok "$desc"
    else
        no "$desc (missing '$needle')"
        echo "  output: $out"
    fi
}

# 无显示环境前缀：清空 DISPLAY/BROADWAY_DISPLAY 等，保证 CI worker 与
# 交叉开发机行为一致（都走 broadway 显示打开失败路径）
NO_DISPLAY="env -u DISPLAY -u WAYLAND_DISPLAY -u BROADWAY_DISPLAY"

echo "# pixelize 2.0.0-git20220108.d1f9da9 consumer test"
echo "# pixelize: $PIXELIZE"
echo "# make_db:  $MAKEDB"
if [ -n "${PIXELIZE_RUNNER:-}" ]; then
    echo "# emulated via: $CMD_PREFIX"
fi

# --- 1/2. GOption --help（显示初始化前的解析路径）→ rc=0 + usage -------
assert_rc_needle 0 "image_file" "pixelize --help prints usage with [image_file] (rc=0)" "" "$PIXELIZE" --help
assert_rc_needle 0 "FILE" "make_db --help prints usage with [FILE...] (rc=0)" "" "$MAKEDB" --help

# --- 3/4. 负向：未知选项 → GOption 拒绝 → else 分支 exit(1) ---------------
assert_rc_needle 1 "Error: in parameters" "pixelize rejects unknown option (rc=1, diagnostic present)" "" "$PIXELIZE" --no-such-option
assert_rc_needle 1 "Error: in parameters" "make_db rejects unknown option (rc=1, diagnostic present)" "" "$MAKEDB" --no-such-option

# --- 5/6. 无显示环境：broadway 显示打开失败 → 同一 else 分支 exit(1) ------
assert_rc_needle 1 "Error: in parameters" "pixelize headless launch fails at display open (rc=1, diagnostic present)" "$NO_DISPLAY" "$PIXELIZE"
assert_rc_needle 1 "Error: in parameters" "make_db headless launch fails at display open (rc=1, diagnostic present)" "$NO_DISPLAY" "$MAKEDB"

echo "1..$((pass+fail))"
echo "# passed: $pass"
echo "# failed: $fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
