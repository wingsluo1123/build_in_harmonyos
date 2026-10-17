#!/bin/sh
# test_ohos — verhaal 025 HarmonyOS PC（真机 aarch64/OHOS）专项验证
#（自包含，可单独执行）
#
# 区别于 test_package 消费者用例：本套件在鸿蒙 PC 上针对**平台特有行为**
# 做独立检查，其中 T4 是本包唯一补丁（0001）的回归验证。
#
#   T1  aarch64 ELF 校验（ELF64 AArch64，可在 OHOS 执行）
#   T2  本包构建路径泄漏检查（/storage/Users、/home 等宿主绝对路径不得进产物；
#       依赖包自身烘焙的路径按依赖归属排除，见脚本内 EXCLUDE 说明）
#   T3  --version 输出核验（消费者可见的版本信息）
#   T4  ★ HMDFS 共享属主场景下打开真实 git 仓库（补丁 0001 回归）
#       本文件系统把属主归一为共享账号 uid，与进程 euid 不一致，
#       libgit2 >= 1.7 的属主校验对任何仓库恒失败 ——
#       校验 verhaal 仍能打开仓库并完成建库（未打补丁时为
#       "Error opening git repo ... is not owned by current user" 退出）
#   T5  ★ 端到端业务语义：仿真内核树（mainline 分支 + linux-6.0.y 稳定分支，
#       稳定分支提交带 "commit <sha> upstream." 与 "Fixes:" 尾行）建库后，
#       校验「某 mainline 提交被回填到哪个发行版」这一核心查询可复现
#   T6  CVEKERNELTREE 未设置时给出明确错误并以非 0 退出（不改上游契约）
#
# 用法：sh run_ohos_test.sh <已安装 verhaal 二进制路径>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）
#
# 注：有意不启用 `set -e` —— 本脚本用 chk() 累积失败后统一判定（全部用例都要跑完
#     才能给出完整体检报告）；`set -o pipefail` 仍然启用，保证管道内失败不被吞掉。
set -u
set -o pipefail
BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <verhaal-binary>"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
chk() { # $1=name $2=rc
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- verhaal HarmonyOS 专项验证 (binary=$BIN) ---"

# T1: aarch64 ELF
readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 本包构建路径泄漏。
# 判定口径（两条，均为本包可控范围）：
#   a) 构建机宿主绝对路径（/storage/Users、/home/<user>、tmp/builds）不得出现在产物中；
#      Conan 缓存内的路径（/.conan2/、/.cache/conan2/）为**依赖包自身**在被构建时
#      烘焙的常量（如 openssl 的 ssl/ 默认目录、libgit2 源码路径），属预编译依赖
#      固有属性，按依赖归属排除，仅作 info 输出。
#   b) 本包在 Conan 缓存中的目录标识（p/b/<hash>/ 或 p/<hash>/）不得出现 ——
#      本包源码/构建目录已由配方 extra_cflags 的 -ffile-prefix-map 重映射。
LEAKS="$(strings "$BIN" 2>/dev/null \
    | grep -E '/storage/Users/|/home/[a-z]|tmp/builds' \
    | grep -vE '/\.conan2/|/\.cache/conan2/')"
SELF_DIR="$(dirname "$(dirname "$BIN")")"
SELF_ID="$(echo "$SELF_DIR" | sed -n 's#.*/p/\(b/\)\{0,1\}\([^/]*\)/p$#\2#p')"
SELF_HIT=""
if [ -n "$SELF_ID" ]; then
    SELF_HIT="$(strings "$BIN" 2>/dev/null | grep -F "$SELF_ID" | head -3)"
fi
if [ -n "$LEAKS" ] || [ -n "$SELF_HIT" ]; then
    [ -n "$LEAKS" ] && echo "  host leak: $(echo "$LEAKS" | head -2 | tr '\n' ' ')"
    [ -n "$SELF_HIT" ] && echo "  self leak: $(echo "$SELF_HIT" | tr '\n' ' ')"
    chk "T2 无本包构建路径泄漏" 1
else
    chk "T2 无本包构建路径泄漏（本包标识 ${SELF_ID:-未识别} 未出现）" 0
    DEP_PATHS="$(strings "$BIN" 2>/dev/null | grep -cE '/\.conan2/|/\.cache/conan2/' || true)"
    echo "  (info: 依赖包烘焙路径 ${DEP_PATHS} 处，按依赖归属排除)"
fi

# T3: --version
VER="$("$BIN" --version 2>&1 | head -1)"
echo "$VER" | grep -q "verhaal version 025" && r=0 || r=1
chk "T3 --version (got: $VER)" "$r"

WORK="${TMPDIR:-/storage/Users/currentUser/tmp}/verhaal-ohos-$$"
rm -rf "$WORK"; mkdir -p "$WORK/kernel" "$WORK/run" || exit 2
trap 'rm -rf "$WORK"' EXIT

# 仿真内核 stable 树：
#   master      v6.0 → v6.0.1（mainline 提交，带 Fixes:）
#   linux-6.0.y v6.0.2（稳定分支上的回填提交，带 "commit <mainline> upstream."）
# 注：verhaal 用 git describe 取版本，tag 必须是附注标签（轻量标签会 describe 失败）
TREE="$WORK/kernel"
GIT="git -c user.email=ohos@test -c user.name=verhaal-ohos"
cd "$TREE" || exit 2
$GIT init -q -b master || exit 2
echo base > f && $GIT add f && $GIT commit -qm "initial" && $GIT tag -a v6.0 -m "Linux 6.0"
echo b >> f && $GIT commit -qam "fix a leak

Fixes: 1111111111111111111111111111111111111111" && $GIT tag -a v6.0.1 -m "Linux 6.0.1"
MAIN="$(git rev-parse HEAD)"
$GIT checkout -q -b linux-6.0.y
echo bb >> f && $GIT commit -qam "fix a leak

commit $MAIN upstream.
Fixes: 1111111111111111111111111111111111111111" && $GIT tag -a v6.0.2 -m "Linux 6.0.2"
STABLE="$(git rev-parse HEAD)"
echo "  仓库属主 uid=$(stat -c '%u' "$TREE" 2>/dev/null) 进程 euid=$(id -u)"
echo "  mainline=$MAIN stable=$STABLE"

# T4: 打开仓库 + 建库（补丁 0001 回归）
cd "$WORK/run" || exit 2
CVEKERNELTREE="$TREE" "$BIN" >"$WORK/out.log" 2>"$WORK/err.log"
rc=$?
if [ "$rc" != "0" ]; then
    echo "  rc=$rc stderr=$(head -2 "$WORK/err.log" | tr '\n' ' ')"
    chk "T4 HMDFS 共享属主下打开仓库并建库（补丁 0001）" 1
elif grep -q "not owned by current user" "$WORK/err.log"; then
    echo "  stderr=$(head -1 "$WORK/err.log")"
    chk "T4 HMDFS 共享属主下打开仓库并建库（补丁 0001）" 1
else
    chk "T4 HMDFS 共享属主下打开仓库并建库（补丁 0001）" 0
fi
grep -q "Saved commits to database" "$WORK/out.log" && r=0 || r=1
chk "T4b 建库流程走完（Saved commits to database）" "$r"

# T5: 回填查询语义（verhaal 的核心用途）
PY="$(command -v python3 || true)"
if [ -n "$PY" ] && [ -s "$WORK/run/verhaal.db" ]; then
    "$PY" - "$WORK/run/verhaal.db" "$MAIN" "$STABLE" <<'EOF'
import sqlite3, sys
db, main, stable = sys.argv[1], sys.argv[2], sys.argv[3]
con = sqlite3.connect(db)
sel = "SELECT id, release, mainline, mainline_id, fixes FROM commits"
rows = {r[0]: r for r in con.execute(sel)}
problems = []

# 稳定分支提交应记录它回填自哪个 mainline 提交
back = rows.get(stable)
if not back or back[3] != main:
    problems.append(f"stable {stable}: {back} (期望 mainline_id={main})")
elif back[1] != "6.0.2":
    problems.append(f"stable {stable} release={back[1]} (期望 6.0.2)")
elif back[4] != "1" * 40:
    problems.append(f"stable {stable} fixes={back[4]} (期望 Fixes 尾行)")

# 核心查询：该 mainline 提交被回填到了哪些发行版
releases = sorted(r[0] for r in con.execute(
    "SELECT DISTINCT release FROM commits WHERE mainline_id=?", (main,)))
if releases != ["6.0.2"]:
    problems.append(f"回填查询 mainline_id={main} -> {releases} (期望 ['6.0.2'])")

# mainline 提交自身记录
ml = rows.get(main)
if not ml or ml[1] != "6.0.1":
    problems.append(f"mainline {main}: {ml} (期望 release=6.0.1)")

if problems:
    for p in problems:
        print(f"  {p}")
sys.exit(1 if problems else 0)
EOF
    chk "T5 回填查询语义（mainline→被回填发行版 / 稳定分支 mainline_id / Fixes）" "$?"
else
    chk "T5 回填查询语义（缺 python3 或库未生成）" 1
fi

# T6: 未设置 CVEKERNELTREE 的契约
env -u CVEKERNELTREE "$BIN" >"$WORK/o6.log" 2>"$WORK/e6.log"
rc6=$?
if [ "$rc6" != "0" ] && grep -q "CVEKERNELTREE" "$WORK/e6.log"; then r=0; else r=1; echo "  rc=$rc6 stderr=$(head -1 "$WORK/e6.log")"; fi
chk "T6 未设置 CVEKERNELTREE 时报错并非 0 退出" "$r"

if [ "$fail" = "0" ]; then
    echo "ALL OHOS TESTS PASSED"
else
    echo "OHOS TESTS FAILED"
fi
exit "$fail"
