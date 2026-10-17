#!/bin/sh
# test_package — verhaal 025 消费者端到端用例（R34：实质消费被测包的公开 CLI）
#
# 用已安装的 verhaal 走完整业务链路：
#   T1  --version 可执行并报告 025
#   T2  从仿真内核 stable 树建库：master(v6.0→v6.0.1) + linux-6.0.y(v6.0.2)
#       均为附注 tag，稳定分支提交带 "commit <sha> upstream." 与 "Fixes:" 尾行
#       → verhaal.db 生成且流程走完
#   T3  回填查询语义：即 verhaal 的用途 "what commit id was backported where" ——
#       按 mainline 提交反查被回填到的发行版，并校验 mainline_id / Fixes 映射
#
# 用法：sh test.sh          （verhaal 由 conanrun 环境的 PATH 提供）
# 退出码：0=全部通过；非 0=失败
#
# 注：有意不启用 `set -e` —— 本脚本用 chk() 累积失败后统一判定（全部用例都要跑完
#     才能给出完整消费者报告）；`set -o pipefail` 仍然启用。
set -u
set -o pipefail

BIN="${VERHAAL_BIN:-$(command -v verhaal || true)}"
[ -n "$BIN" ] || { echo "FAIL: verhaal not found in PATH"; exit 2; }
[ -x "$BIN" ] || { echo "FAIL: verhaal not executable: $BIN"; exit 2; }

fail=0
chk() { # $1=name $2=rc
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- verhaal consumer test (binary=$BIN) ---"

# T1: 版本输出
VER="$("$BIN" --version 2>&1 | head -1)"
echo "$VER" | grep -q "verhaal version 025" && r=0 || r=1
chk "T1 --version (got: $VER)" "$r"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
TREE="$WORK/kernel"
mkdir -p "$TREE"
cd "$TREE" || exit 2

GIT="git -c user.email=test@example.com -c user.name=verhaal-test"
$GIT init -q -b master || exit 2
echo base > f && $GIT add f && $GIT commit -qm "initial" && $GIT tag -a v6.0 -m "Linux 6.0"
echo b >> f && $GIT commit -qam "fix a leak

Fixes: 1111111111111111111111111111111111111111" && $GIT tag -a v6.0.1 -m "Linux 6.0.1"
MAIN="$($GIT rev-parse HEAD)"
$GIT checkout -q -b linux-6.0.y
echo bb >> f && $GIT commit -qam "fix a leak

commit $MAIN upstream.
Fixes: 1111111111111111111111111111111111111111" && $GIT tag -a v6.0.2 -m "Linux 6.0.2"
STABLE="$($GIT rev-parse HEAD)"

# T2: 建库
mkdir -p "$WORK/run"
cd "$WORK/run" || exit 2
CVEKERNELTREE="$TREE" "$BIN" >"$WORK/out.log" 2>"$WORK/err.log"
[ -s verhaal.db ] && r=0 || r=1
chk "T2 建库生成 verhaal.db ($(wc -c < verhaal.db 2>/dev/null || echo 0) bytes)" "$r"
grep -q "Saved commits to database" "$WORK/out.log" && r=0 || r=1
chk "T2b 建库流程完成（Saved commits to database）" "$r"

# T3: 回填查询语义
PY="$(command -v python3 || true)"
if [ -n "$PY" ] && [ -s "$WORK/run/verhaal.db" ]; then
    "$PY" - "$WORK/run/verhaal.db" "$MAIN" "$STABLE" <<'EOF'
import sqlite3, sys
db, main, stable = sys.argv[1], sys.argv[2], sys.argv[3]
con = sqlite3.connect(db)
rows = {r[0]: r for r in con.execute(
    "SELECT id, release, mainline, mainline_id, fixes FROM commits")}
problems = []

back = rows.get(stable)
if not back:
    problems.append(f"稳定分支提交 {stable} 未入库")
else:
    if back[3] != main:
        problems.append(f"{stable} mainline_id={back[3]} (期望 {main})")
    if back[1] != "6.0.2":
        problems.append(f"{stable} release={back[1]} (期望 6.0.2)")
    if back[4] != "1" * 40:
        problems.append(f"{stable} fixes={back[4]} (期望 Fixes 尾行)")

releases = sorted(r[0] for r in con.execute(
    "SELECT DISTINCT release FROM commits WHERE mainline_id=?", (main,)))
if releases != ["6.0.2"]:
    problems.append(f"回填查询 {main} -> {releases} (期望 ['6.0.2'])")

ml = rows.get(main)
if not ml or ml[1] != "6.0.1":
    problems.append(f"mainline {main}: {ml} (期望 release=6.0.1)")

if problems:
    for p in problems:
        print(f"  {p}")
sys.exit(1 if problems else 0)
EOF
    chk "T3 回填查询语义（mainline→被回填发行版 / mainline_id / Fixes）" "$?"
else
    # 无 python3 时退化为 SQLite 魔数校验，保证仍真实消费产物
    head -c 16 verhaal.db | grep -q "SQLite format 3" && r=0 || r=1
    chk "T3 verhaal.db 为 SQLite 库（无 python3，降级校验）" "$r"
fi

if [ "$fail" = "0" ]; then echo "ALL CONSUMER TESTS PASSED"; else echo "CONSUMER TESTS FAILED"; fi
exit "$fail"
