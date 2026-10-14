#!/data/service/hnp/bin/bash
# test_package/test.sh — 消费者视角功能测试：真实调用 oed 安装出的 `ed` 可执行文件。
#
# 两组用例（R34：全部为真实调用，无空壳断言）：
#   A 组 上游功能等价 —— 行编辑 / 寻址 / 正则替换 / 读写 / 撤销 / 全局命令 / 错误恢复 / 长缓冲
#   B 组 鸿蒙特有 —— /tmp 为 erofs 只读挂载时 scratch 文件目录的回退链（本次适配的核心修复）
#
# 用法: bash test.sh [ed 可执行文件路径]
#
# 刻意不使用 `set -e`：本脚本是计数式测试，需要跑完全部用例后统一汇总
# PASS/FAIL 再决定退出码，不能在中途第一个失败处终止。
set -u
set -o pipefail

ED="${1:-ed}"
if ! command -v "$ED" >/dev/null 2>&1 && [ ! -x "$ED" ]; then
    echo "FAIL: 找不到 ed 可执行文件: $ED"
    exit 1
fi

PASS=0
FAIL=0
FAILED_CASES=""

pass() { PASS=$((PASS + 1)); printf '  PASS  %s\n' "$1"; }
fail() {
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}
    - $1"
    printf '  FAIL  %s\n' "$1"
}

# assert_eq <用例名> <期望> <实际>
assert_eq() {
    if [ "$2" = "$3" ]; then
        pass "$1"
    else
        fail "$1（期望=[$2] 实际=[$3]）"
    fi
}

# 选一个可写的 scratch 目录：$TMPDIR → $HOME/tmp → $HOME → 当前目录
pick_scratch() {
    for c in "${TMPDIR:-}" "$HOME/tmp" "$HOME" "$(pwd)"; do
        [ -n "$c" ] || continue
        [ -d "$c" ] || mkdir -p "$c" 2>/dev/null || continue
        if ( : > "$c/.oed-write-probe" ) 2>/dev/null; then
            rm -f "$c/.oed-write-probe"
            printf '%s' "$c"
            return 0
        fi
    done
    return 1
}

SCRATCH="$(pick_scratch)" || {
    echo "FAIL: 找不到可写的 scratch 目录"
    exit 1
}
D="$SCRATCH/oed-test-$$"
mkdir -p "$D" || exit 1
trap 'rm -rf "$D"' EXIT

echo "[A] 上游功能等价测试（真实调用 ed 完成编辑任务）"

# A1 新建文件并写入两行（a / w）
printf 'a\nhello\nworld\n.\nw %s/a1.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
assert_eq "A1 新建文件写入两行（a/w）" "hello
world" "$(cat "$D/a1.txt" 2>/dev/null)"

# A2 全范围寻址 1,$p
assert_eq "A2 全范围寻址 1,\$p" "hello
world" "$(printf '1,$p\nq\n' | "$ED" -s "$D/a1.txt" 2>/dev/null)"

# A3 单行寻址 2p
assert_eq "A3 单行寻址 2p" "world" "$(printf '2p\nq\n' | "$ED" -s "$D/a1.txt" 2>/dev/null)"

# A4 末行寻址 $p
assert_eq "A4 末行寻址 \$p" "world" "$(printf '$p\nq\n' | "$ED" -s "$D/a1.txt" 2>/dev/null)"

# A5 正则替换并写盘
printf 'a\none\ntwo\nthree\n.\nw %s/a5.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
printf '2s/two/TWO/\nw\nq\n' | "$ED" -s "$D/a5.txt" >/dev/null 2>&1
assert_eq "A5 正则替换 2s/two/TWO/ 并写盘" "one
TWO
three" "$(cat "$D/a5.txt" 2>/dev/null)"

# A6 全局正则替换
printf 'a\nx1\ny2\nz3\n.\nw %s/a6.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
printf '1,$s/[0-9]/#/g\nw\nq\n' | "$ED" -s "$D/a6.txt" >/dev/null 2>&1
assert_eq "A6 全局正则替换 1,\$s/[0-9]/#/g" "x#
y#
z#" "$(cat "$D/a6.txt" 2>/dev/null)"

# A7 删除行
printf 'a\nalpha\nbeta\ngamma\n.\nw %s/a7.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
printf '2d\nw\nq\n' | "$ED" -s "$D/a7.txt" >/dev/null 2>&1
assert_eq "A7 删除行 2d 并写盘" "alpha
gamma" "$(cat "$D/a7.txt" 2>/dev/null)"

# A8 撤销
printf 'a\nalpha\nbeta\ngamma\n.\nw %s/a8.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
printf '2d\nu\nw\nq\n' | "$ED" -s "$D/a8.txt" >/dev/null 2>&1
assert_eq "A8 撤销 2d/u 恢复被删行" "alpha
beta
gamma" "$(cat "$D/a8.txt" 2>/dev/null)"

# A9 全局命令 g/re/d
printf 'a\naa\nbb\nac\nbd\n.\nw %s/a9.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
printf 'g/^b/d\nw\nq\n' | "$ED" -s "$D/a9.txt" >/dev/null 2>&1
assert_eq "A9 全局命令 g/^b/d 删除匹配行" "aa
ac" "$(cat "$D/a9.txt" 2>/dev/null)"

# A10 r 命令读入外部文件并拼接
printf 'tail1\ntail2' > "$D/a10r.txt"
printf 'a\nhead\n.\nw %s/a10.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
printf 'r %s/a10r.txt\nw\nq\n' "$D" | "$ED" -s "$D/a10.txt" >/dev/null 2>&1
assert_eq "A10 r 读入外部文件并拼接" "head
tail1
tail2" "$(cat "$D/a10.txt" 2>/dev/null)"

# A11 就地编辑既有文件（命令来自 stdin 重定向，脚本化典型用法）
printf 'a\nkeep\nremove\n.\nw %s/a11.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
printf 'g/^remove/d\nw\nq\n' > "$D/a11.cmds"
"$ED" -s "$D/a11.txt" < "$D/a11.cmds" >/dev/null 2>&1
rc=$?
assert_eq "A11 就地编辑既有文件（stdin 重定向）内容正确" "keep" "$(cat "$D/a11.txt" 2>/dev/null)"
assert_eq "A11 就地编辑退出码为 0" "0" "$rc"

# A12 非法命令的脚本安全契约：给出 ? 诊断、非交互输入下以非零码退出且不落盘
#     （main.c:275-282 —— 命令分发 default 分支：fputs("?\n") 后 !interactive 即 quit(2)）
printf 'a\nx\n.\nw %s/a12.txt\nq\n' "$D" | "$ED" -s >/dev/null 2>&1
out="$(printf 'bogus-command\n1s/x/y/\nw\nq\n' | "$ED" -s "$D/a12.txt" 2>&1)"
rc12=$?
case "$out" in
    *'?'*) pass "A12 非法命令给出 ? 诊断" ;;
    *) fail "A12 非法命令给出 ? 诊断（实际=[$out]）" ;;
esac
[ "$rc12" -ne 0 ] && pass "A12 非交互输入下非法命令以非零码退出（rc=$rc12）" \
    || fail "A12 非交互输入下非法命令应以非零码退出（实际 rc=$rc12）"
assert_eq "A12 非法命令中断后未落盘，文件保持不变" "x" "$(cat "$D/a12.txt" 2>/dev/null)"

# A13 500 行长缓冲（所有行经 scratch 文件落盘）
python3 - "$D/a13in.txt" <<'PYEOF'
import sys
with open(sys.argv[1], "w") as f:
    for i in range(1, 501):
        f.write("line%03d\n" % i)
PYEOF
printf 'w %s/a13out.txt\nq\n' "$D" | "$ED" -s "$D/a13in.txt" >/dev/null 2>&1
assert_eq "A13 500 行长缓冲写入行数" "500" "$(wc -l < "$D/a13out.txt" 2>/dev/null | tr -d ' ')"
assert_eq "A13 长缓冲首行" "line001" "$(head -1 "$D/a13out.txt" 2>/dev/null)"
assert_eq "A13 长缓冲末行" "line500" "$(tail -1 "$D/a13out.txt" 2>/dev/null)"

echo "[B] 鸿蒙特有测试（/tmp 只读挂载下 scratch 文件目录回退链）"

# B1 TMPDIR 指向可写目录：正常工作，且 scratch 文件用后即删（close_sbuf/quit unlink）
B1DIR="$D/scratch-b1"
mkdir -p "$B1DIR"
printf 'a\ntmpdir-ok\n.\nw %s/b1.txt\nq\n' "$D" | TMPDIR="$B1DIR" "$ED" -s >/dev/null 2>&1
assert_eq "B1 TMPDIR 为可写目录时编辑成功" "tmpdir-ok" "$(cat "$D/b1.txt" 2>/dev/null)"
assert_eq "B1 退出后 TMPDIR 中无 ed.* scratch 残留" "0" \
    "$(ls -1 "$B1DIR" 2>/dev/null | grep -c '^ed\.' || true)"

# B2 TMPDIR 未设置：鸿蒙上 /tmp 不可写，必须经 $HOME 回退后仍能工作
printf 'a\nno-tmpdir\n.\nw %s/b2.txt\nq\n' "$D" | env -u TMPDIR "$ED" -s >/dev/null 2>&1
assert_eq "B2 TMPDIR 未设置时编辑仍成功（鸿蒙经 \$HOME 回退）" "no-tmpdir" \
    "$(cat "$D/b2.txt" 2>/dev/null)"

# B3 TMPDIR 指向一个普通文件：对任何 uid（含 root）都不可用，必须经回退链继续工作
printf 'not-a-directory\n' > "$D/tmpdir-is-a-file"
printf 'a\nro-tmpdir\n.\nw %s/b3.txt\nq\n' "$D" \
    | TMPDIR="$D/tmpdir-is-a-file" "$ED" -s >/dev/null 2>&1
assert_eq "B3 TMPDIR 不可用（普通文件）时经回退链仍编辑成功" "ro-tmpdir" \
    "$(cat "$D/b3.txt" 2>/dev/null)"

# B4 TMPDIR 指向不存在的目录：必须经回退链继续工作
printf 'a\nmissing-tmpdir\n.\nw %s/b4.txt\nq\n' "$D" \
    | TMPDIR="$D/no-such-dir" "$ED" -s >/dev/null 2>&1
assert_eq "B4 TMPDIR 目录不存在时经回退链仍编辑成功" "missing-tmpdir" \
    "$(cat "$D/b4.txt" 2>/dev/null)"

# B5 非 tty 管道输入（鸿蒙终端下的脚本化用法）+ 回退路径不留残留
home_ed_before="$(ls -1 "$HOME" 2>/dev/null | grep -c '^ed\.' || true)"
printf 'a\npipe-mode\n.\nw %s/b5.txt\nq\n' "$D" | env -u TMPDIR "$ED" -s >/dev/null 2>&1
assert_eq "B5 非 tty 管道输入可正常编辑" "pipe-mode" "$(cat "$D/b5.txt" 2>/dev/null)"
assert_eq "B5 回退路径 \$HOME 中无 ed.* scratch 残留" "$home_ed_before" \
    "$(ls -1 "$HOME" 2>/dev/null | grep -c '^ed\.' || true)"

echo ""
echo "===== 结果: PASS=$PASS FAIL=$FAIL ====="
if [ "$FAIL" -ne 0 ]; then
    echo "失败用例:${FAILED_CASES}"
    exit 1
fi
echo "全部 $PASS 项断言通过"
exit 0
