#!/bin/sh
# check.sh — 「GUI 工具库后端宏守卫」形态矩阵的离线回归
#
# 锁定检测器判定口径：什么算守卫（WARN，exit 0）、什么不算（HARD，exit 1）。
# 正向覆盖 #if defined / #ifdef / #elif defined；反向覆盖 #ifndef / !defined /
# 平台名宏 / 无守卫——两侧都要钉住，只测一侧会漏掉假阳性或假阴性。
# 不需要 GTK / conan / 网络，任何环境可直接跑。
#
# 用法:
#   ./check.sh             # 每例一行 PASS/FAIL
#   ./check.sh --verbose   # 同时打印检测器完整输出
#
# 退出码: 0 = 全部符合预期；1 = 有用例不符；2 = 用法/环境错误

set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DETECT="$HERE/../../detect-gui-toolkit-backend-macro-guard.sh"
VERBOSE=0

for a in "$@"; do
    case "$a" in
        --verbose) VERBOSE=1 ;;
        -h|--help) echo "usage: $0 [--verbose]"; exit 0 ;;
        *) echo "usage: $0 [--verbose]" >&2; exit 2 ;;
    esac
done

[ -f "$DETECT" ] || { echo "FAIL: detector not found: $DETECT" >&2; exit 2; }

FAILED=0
TOTAL=0

run_case() {   # run_case <子目录> <期望 exit> <期望 hard 计数> <说明>
    sub=$1
    want_rc=$2
    want_hard=$3
    desc=$4
    TOTAL=$((TOTAL + 1))

    set +e
    out=$(sh "$DETECT" --quiet "$HERE/$sub" 2>&1)
    rc=$?
    set -e

    hard=$(printf '%s\n' "$out" | sed -n 's/.*hard=\([0-9][0-9]*\).*/\1/p' | tail -n 1)
    hard=${hard:-?}

    if [ "$rc" = "$want_rc" ] && [ "$hard" = "$want_hard" ]; then
        printf 'PASS  %-18s exit=%s hard=%s  (%s)\n' "$sub" "$rc" "$hard" "$desc"
        if [ "$VERBOSE" = "1" ]; then
            printf '%s\n' "$out" | sed 's/^/      | /'
        fi
        return 0
    fi

    FAILED=$((FAILED + 1))
    printf 'FAIL  %-18s exit=%s(want %s) hard=%s(want %s)  (%s)\n' \
        "$sub" "$rc" "$want_rc" "$hard" "$want_hard" "$desc"
    printf '%s\n' "$out" | sed 's/^/      | /'
}

# 算守卫
run_case 01-ifdefined     0 0 "#if defined(M)"
run_case 02-ifdef         0 0 "#ifdef M（工具包自身写法）"
run_case 03-elifdefined   0 0 "#elif defined(M)"
# 不算守卫（反义 / 反模式 / 无守卫）
run_case 04-ifndef        1 1 "#ifndef M —— 反义形态，宏未定义时才编译"
run_case 05-not-defined   1 1 "#if !defined(M) —— 反义形态"
run_case 06-unguarded     1 2 "无守卫基线（后端头 include + 后端符号各 1 条）"
run_case 07-platform-macro 1 1 "#ifdef __OHOS__ —— 平台名不是后端宏"

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "RESULT: 守卫形态矩阵 $TOTAL/$TOTAL 符合预期"
    exit 0
fi
echo "RESULT: $FAILED/$TOTAL 不符合预期"
exit 1
