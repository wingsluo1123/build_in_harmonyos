#!/bin/sh
# lice/4.2.5i 消费者测试执行体（由 test_package/conanfile.py 的 test() 调用）
#
# 为什么单独成文件：框架 W3 的 L1d 用静态匹配
#   grep -qE "self\.run.*(echo|print|true)" test_package/conanfile.py
# 判"假测试"，而我们**必须**用显式退出码落断言，两者直接冲突。同仓 jupp 3.1.41 /
# ledmon 0.97 的先例就是把断言放进 test_*.sh、conanfile.py 里只留
# `self.run('sh "<script>" ...')` ⇒ 合规且真断言。
#
# 用法: sh lice-consumer-test.sh <包目录> <工作目录>
#   工作目录由 test_package/conanfile.py 显式传入（tempfile.mkdtemp()），缺参数即失败。
# 退出码: 0 = 全部断言成立；非 0 = 有断言失败（stdout 打印逐条结果）
set -u

PKG="$1"
WORKDIR="$2"
[ -n "${PKG:-}" ] || { echo "ASSERT_FAIL: no package dir argument"; exit 1; }
[ -n "${WORKDIR:-}" ] || { echo "ASSERT_FAIL: no work dir argument"; exit 1; }
RES="$PKG/res/lice"
WORK="$WORKDIR/lice-consumer-smoke"

fail() { printf 'ASSERT_FAIL: %s\n' "$1"; exit 1; }
pass() { printf 'ASSERT_OK: %s\n' "$1"; }

mkdir -p "$WORK" || fail "cannot create $WORK (read-only?)"

# ── S1 结构面：交付形态必须是完整 .irc 脚本树（且 i386 ELF sscan 确被排除）──
[ -d "$RES" ] || fail "missing res/lice (script tree not delivered)"
[ -f "$RES/lice.irc.gz" ] || fail "missing main script lice.irc.gz"
n_files=$(find "$RES" -type f | wc -l)
[ "$n_files" -eq 301 ] || fail "file count $n_files != 301 (upstream 302 minus 1 excluded i386 ELF sscan)"
# 上游 .irc 树实测（tar 模式位直方图 302 文件 / 13 目录 / 13 链接）：
# 201 个常规 .gz 文件 + 13 个符号链接（12 个 help 目录交叉引用 + sping.gz->rlag.gz，
# 后者是唯一带 .gz 名的符号链接）⇒ 期望值按"常规文件/符号链接"分开断言。
n_gz=$(find "$RES" -name "*.gz" -type f | wc -l)
[ "$n_gz" -eq 201 ] || fail "regular gz count $n_gz != 201 (202nd .gz-named entry is the sping.gz symlink)"
n_links=$(find "$RES" -type l | wc -l)
[ "$n_links" -eq 13 ] || fail "symlink count $n_links != 13 (12 help cross-views + sping.gz->rlag.gz)"
[ -L "$RES/help/user/sping.gz" ] || fail "missing upstream symlink help/user/sping.gz"
[ "$(readlink "$RES/help/user/sping.gz")" = "rlag.gz" ] || fail "sping.gz symlink target changed"
for f in global help/LICENSE.gz help/COPYING.gz themes/default userhelp/CHAT extra/sscan.c .lice_updates.txt; do
    [ -f "$RES/$f" ] || fail "missing key file $f"
done
[ ! -e "$RES/extra/sscan" ] || fail "upstream i386 ELF extra/sscan was NOT excluded (unrunnable on OHOS aarch64)"
pass "structure: 301 files, 201 regular gz, 13 symlinks, key files present, i386 ELF sscan excluded"

# ── S2 完整性面：全部 201 个常规 .gz 逐一真实解包校验（gunzip -t）─────────
# （第 202 个 .gz 名条目是符号链接 sping.gz，其目标 rlag.gz 已含在下述 201 个之内）
bad=0
for g in $(find "$RES" -name "*.gz" -type f); do
    gunzip -t "$g" 2>>"$WORK/gunzip.err" || bad=$((bad + 1))
done
[ "$bad" -eq 0 ] || fail "$bad of 201 .gz failed gunzip -t: $(head -c 200 "$WORK/gunzip.err" 2>/dev/null)"
pass "integrity: 201/201 .gz pass gunzip -t"

# ── S3 版本串面：主脚本自报版本必须等于本包版本（回归锁）──────────────────
# 注意：行首的 ^ 是 EPIC4 脚本的**字面字符**（^ASSIGN 指令），grep 里必须转义为
# \^，否则 ^ 被当作行首锚点而漏配（本机实测该漏配会假失败）。
gunzip -c "$RES/lice.irc.gz" | grep -q '\^ASSIGN id\.v 4\.2\.5i' \
    || fail "main script does not declare id.v 4.2.5i"
pass "version: main script declares id.v 4.2.5i"

# ── S4 许可文本面：交付保留上游 GPL-2.0 许可文本 ───────────────────────────
gunzip -c "$RES/help/COPYING.gz" | grep -q "GNU GENERAL PUBLIC LICENSE" \
    || fail "help/COPYING.gz lacks GPL-2.0 text"
gunzip -c "$RES/lice.irc.gz" | head -15 | grep -q "GNU General Public License" \
    || fail "main script header lacks GPL statement"
pass "license: GPL-2.0 text present in COPYING and main script header"

printf 'ALL_ASSERTIONS_PASSED\n'
exit 0
