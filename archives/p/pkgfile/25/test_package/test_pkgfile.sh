#!/bin/sh
# pkgfile 25 消费者测试 —— 实际执行被测二进制并断言真实输出（R34，非空壳测试）
#
# 用法: sh test_pkgfile.sh <bin_dir> <testdata_dir>
#
# 覆盖范围:
#   1. --version          版本号与 config.hh 注入正确（PACKAGE_NAME/PACKAGE_VERSION）
#   2. --help             真实 CLI 已链接（Operations 段落完整）
#   3. 空缓存目录           db.cc 的 Database version file 校验路径
#   4. 离线端到端闭环        alpm .files --(libcurl file://)--> pkgfile -u
#                          --> 本地 pkgfile 缓存 --> -s / -l / -v 搜索与列举
#     完全不依赖网络：仓库以 file:// URL 由 libcurl 直接读取
#     （update.cc:344 只在 `result != CURLE_OK || resp >= 400` 时判失败，
#      file:// 传输 resp=0，走正常成功分支）。
set -eu

BIN_DIR="${1:?usage: test_pkgfile.sh <bin_dir> <testdata_dir>}"
TESTDATA_DIR="${2:?usage: test_pkgfile.sh <bin_dir> <testdata_dir>}"

PKG="$BIN_DIR/pkgfile"
if [ ! -x "$PKG" ]; then
  echo "FAIL: 未找到可执行文件 $PKG" >&2
  exit 1
fi

# ── 工作目录 ────────────────────────────────────────────────────────────────
# OHOS 沙箱的 /tmp 只读（共性问题指南 §13），而 `mktemp -d`（无模板）在
# GNU/Toybox 实现下**不使用** $TMPDIR、固定落 /tmp → 必失败
# （真机实测：can't create temporary file /tmp/xxx.tmp: Read-only file system）。
# 因此显式挑一个可写基目录并用 mkdir 建工作区，不依赖 mktemp。
WORK_BASE=""
for cand in "$TMPDIR" "$HOME/tmp" "$PWD"; do
  if [ -n "$cand" ] && [ -d "$cand" ] && [ -w "$cand" ]; then
    WORK_BASE="$cand"
    break
  fi
done
if [ -z "$WORK_BASE" ]; then
  echo "FAIL: TMPDIR/HOME/PWD 均不可写，找不到工作目录" >&2
  exit 1
fi
WORK="$WORK_BASE/pkgfile-consumer-$$"
rm -rf "$WORK"
mkdir -p "$WORK" || { echo "FAIL: 无法创建工作目录 $WORK" >&2; exit 1; }
trap 'rm -rf "$WORK"' EXIT

# update.cc:OpenTmpfile 读 TMPDIR（下载中转文件），zsh 另读 TMPPREFIX
TMPDIR="$WORK/tmp"
TMPPREFIX="$TMPDIR/zsh"
export TMPDIR TMPPREFIX
mkdir -p "$TMPDIR"

FAILURES=0

fail() {
  echo "FAIL: $*" >&2
  FAILURES=$((FAILURES + 1))
}

# ── 1. --version ────────────────────────────────────────────────────────────
VERSION_OUT="$("$PKG" --version)"
echo "version: $VERSION_OUT"
if [ "$VERSION_OUT" != "pkgfile v25" ]; then
  fail "--version 期望 'pkgfile v25'，实际 '$VERSION_OUT'"
fi

# ── 2. --help：确认链接的是真实 CLI ─────────────────────────────────────────
HELP_OUT="$("$PKG" --help)"
echo "$HELP_OUT" | grep -q -- '--search' || fail "--help 未列出 --search"
echo "$HELP_OUT" | grep -q -- '--update' || fail "--help 未列出 --update"
echo "$HELP_OUT" | grep -q -- '--cachedir' || fail "--help 未列出 --cachedir"

# ── 3. 空缓存目录：db.cc 的版本文件缺失路径 ─────────────────────────────────
mkdir -p "$WORK/empty-cache"
if "$PKG" --cachedir="$WORK/empty-cache" --list demo \
     >"$WORK/empty.out" 2>"$WORK/empty.err"; then
  fail "空缓存目录下 --list 本应非 0 退出"
fi
grep -q 'Database version file not found' "$WORK/empty.err" \
  || fail "空缓存目录未报 'Database version file not found'（stderr: $(cat "$WORK/empty.err")）"

# ── 4. 离线端到端：.files -> -u -> 本地缓存 -> -s / -l ──────────────────────
# pacman.conf 的 Server 模板：pkgfile 先替换 $arch/$repo，再追加 "/<repo>.files"
# （update.cc:PrepareUrl），故文件路径必须是 <root>/<arch>/<repo>/<repo>.files。
mkdir -p "$WORK/repo/x86_64/demo" "$WORK/cache"

# alpm `.files` 数据库就是一个普通（未压缩）tar，成员为
# `<pkgname>-<pkgver>-<pkgrel>/files`，内容为 "%FILES%" + 每行一个不带前导斜杠
# 的路径（见 archive_converter.cc:WriteCpioEntry）。
# 这里在测试运行时用 tar 现场组装；testdata 下全部是**纯文本**成员，不放二进制
# 归档 —— GitCode 的 pull/<n>.diff 对二进制只渲染 "Binary files ... differ"、
# 不带 GIT binary patch 数据，CI 的 checkout-pr 用 `git apply pr.diff` 应用时会
# 直接失败（CI #91143 实测：error: missing binary patch data for ...）。
# 纯文本可保证 PR diff 永远可应用。
ALPM_DIR="$TESTDATA_DIR/alpm"
if [ ! -d "$ALPM_DIR" ]; then
  echo "FAIL: 缺少测试数据目录 $ALPM_DIR" >&2
  exit 1
fi
if ! command -v tar >/dev/null 2>&1; then
  echo "FAIL: 需要 tar 现场组装 alpm .files 测试归档，但 PATH 中找不到 tar" >&2
  exit 1
fi
tar cf "$WORK/repo/x86_64/demo/demo.files" -C "$ALPM_DIR" demo-1.2.3-1 helper-2.0-1 \
  || { echo "FAIL: 组装 demo.files 失败" >&2; exit 1; }

# 不用 here-doc：OHOS 的 /bin/sh 是 mksh，here-doc 会落一个临时文件到
# **shell 启动时缓存的** TMPDIR（脚本内部再 export 已经太晚，实测必落只读的
# /tmp 并报 "can't create temporary file /tmp/shXXXX.tmp: Read-only file
# system"）。printf 直接写文件，不依赖任何临时文件。
printf '[options]\nArchitecture = x86_64\n\n[demo]\nServer = file://%s/repo/$arch/$repo\n' \
  "$WORK" >"$WORK/pacman.conf"
cat "$WORK/pacman.conf"
"$PKG" --config="$WORK/pacman.conf" --cachedir="$WORK/cache" --update
[ -f "$WORK/cache/.db_version" ] || fail "-u 未写出 .db_version"
[ -f "$WORK/cache/demo.files.000" ] || fail "-u 未写出 demo.files.000"

# 4a. 按文件名反查所属包（非 verbose 输出 repo/pkgname）
SEARCH_OUT="$("$PKG" --config="$WORK/pacman.conf" --cachedir="$WORK/cache" \
  --search demo-tool)"
echo "search demo-tool -> $SEARCH_OUT"
[ "$SEARCH_OUT" = "demo/demo" ] \
  || fail "搜索 demo-tool 期望 'demo/demo'，实际 '$SEARCH_OUT'"

# 4b. 按绝对路径查找（跨包）
SEARCH2_OUT="$("$PKG" --config="$WORK/pacman.conf" --cachedir="$WORK/cache" \
  --search /usr/bin/helper-ctl)"
echo "search /usr/bin/helper-ctl -> $SEARCH2_OUT"
[ "$SEARCH2_OUT" = "demo/helper" ] \
  || fail "期望 'demo/helper'，实际 '$SEARCH2_OUT'"

# 4c. 未命中必须非 0 退出
if "$PKG" --config="$WORK/pacman.conf" --cachedir="$WORK/cache" \
     --search no-such-file-xyz >/dev/null 2>&1; then
  fail "搜索未命中时本应非 0 退出"
fi

# 4d. 列出包内文件（tab 分隔的 repo/pkg <TAB> path）
LIST_OUT="$("$PKG" --config="$WORK/pacman.conf" --cachedir="$WORK/cache" \
  --list demo)"
echo "list demo:"
echo "$LIST_OUT"
echo "$LIST_OUT" | grep -q '/usr/bin/demo-tool' \
  || fail "--list demo 未包含 /usr/bin/demo-tool"
echo "$LIST_OUT" | grep -q '/usr/share/demo/hello.txt' \
  || fail "--list demo 未包含 /usr/share/demo/hello.txt"
if echo "$LIST_OUT" | grep -q 'helper'; then
  fail "--list demo 不应包含 helper 包的内容"
fi

# 4e. 列出不存在的包必须非 0 退出
if "$PKG" --config="$WORK/pacman.conf" --cachedir="$WORK/cache" \
     --list packagedoesntexist >/dev/null 2>&1; then
  fail "--list 不存在的包本应非 0 退出"
fi

# 4f. verbose 搜索带版本号
VERBOSE_OUT="$("$PKG" --config="$WORK/pacman.conf" --cachedir="$WORK/cache" \
  --search --verbose /usr/bin/demo-tool)"
echo "search -v -> $VERBOSE_OUT"
echo "$VERBOSE_OUT" | grep -q 'demo/demo 1.2.3-1' \
  || fail "verbose 输出缺少 'demo/demo 1.2.3-1'"

if [ "$FAILURES" -ne 0 ]; then
  echo "FAILED: $FAILURES 项断言未通过" >&2
  exit 1
fi

echo "PASS: pkgfile 25 消费者测试全部通过"
