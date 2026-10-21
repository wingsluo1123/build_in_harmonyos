#!/bin/sh
# KB-NO-OPENGL 复现脚本：同一份样例库跑两阶段——
#   阶段 OFF（关 SKILL）：直接 conan create → 必须复现 "use of undeclared identifier"
#   阶段 ON （开 SKILL）：detect.sh 命中 → fix.sh 加 QT_NO_OPENGL 门控 → conan create 通过
#
# 用法:
#   reproduce.sh [--sample <样例库目录>] [--profile <ohos-aarch64 profile>]
#                [--work <工作目录>] [--only off|on] [--keep] [--json]
#
# 说明:
#   * 默认样例库 = 本脚本同级 sample/；默认 profile = 本仓库 ci/conan/profiles/ohos-aarch64
#   * 全程不依赖本地缓存路径：Qt 前缀优先由 --qt-prefix 指定，否则自动探测
#   * 日志一律重定向到文件（脚本内不做 `cmd | head` 管道，避免 SIGPIPE 误杀）
#   * 退出码: 0=两阶段均符合预期 1=有阶段不符合预期 2=参数/环境错误
set -u

SAMPLE=""
PROFILE=""
WORK=""
QT_PREFIX=""
ONLY="both"
KEEP=0
JSON=0

usage() {
    sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --sample)     SAMPLE=${2:-}; shift 2 ;;
        --sample=*)   SAMPLE=${1#*=}; shift ;;
        --profile)    PROFILE=${2:-}; shift 2 ;;
        --profile=*)  PROFILE=${1#*=}; shift ;;
        --qt-prefix)  QT_PREFIX=${2:-}; shift 2 ;;
        --qt-prefix=*) QT_PREFIX=${1#*=}; shift ;;
        --work)       WORK=${2:-}; shift 2 ;;
        --work=*)     WORK=${1#*=}; shift ;;
        --only)       ONLY=${2:-}; shift 2 ;;
        --only=*)     ONLY=${1#*=}; shift ;;
        --keep)       KEEP=1; shift ;;
        --json)       JSON=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *) echo "reproduce.sh: 未知参数 $1" >&2; usage >&2; exit 2 ;;
    esac
done

case "$ONLY" in off|on|both) ;; *) echo "reproduce.sh: --only 只能是 off/on/both" >&2; exit 2 ;; esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -n "$SAMPLE" ] || SAMPLE="$SCRIPT_DIR/sample"
if [ ! -d "$SAMPLE" ]; then
    echo "reproduce.sh: 样例库目录不存在: $SAMPLE" >&2
    exit 2
fi
SAMPLE=$(CDPATH= cd -- "$SAMPLE" && pwd)

# ---- profile 定位（优先参数，其次本仓库约定路径） ----
if [ -z "$PROFILE" ]; then
    for cand in "$SCRIPT_DIR/../../../ci/conan/profiles/ohos-aarch64" \
                "$SCRIPT_DIR/../../ci/conan/profiles/ohos-aarch64" \
                "$PWD/ci/conan/profiles/ohos-aarch64"; do
        if [ -f "$cand" ]; then PROFILE=$cand; break; fi
    done
fi
if [ -z "$PROFILE" ] || [ ! -f "$PROFILE" ]; then
    echo "reproduce.sh: 未找到 OHOS conan profile，请用 --profile 指定" >&2
    exit 2
fi
PROFILE=$(CDPATH= cd -- "$(dirname -- "$PROFILE")" && pwd)/$(basename -- "$PROFILE")

# ---- Qt6 前缀探测（qtbase 包内 include/QtGui + lib/cmake） ----
if [ -z "$QT_PREFIX" ]; then
    for d in "${CONAN_HOME:-$HOME/.conan2}"/p/*/p; do
        if [ -f "$d/include/QtGui/qtgui-config.h" ] && [ -d "$d/lib/cmake" ]; then
            QT_PREFIX=$d; break
        fi
    done
fi

# ---- 工作目录（/tmp 可能只读，回退 $HOME/tmp） ----
if [ -z "$WORK" ]; then
    BASE="${TMPDIR:-}"
    { [ -n "$BASE" ] && [ -w "$BASE" ]; } 2>/dev/null || BASE="${HOME:-.}/tmp"
    WORK="$BASE/kb-no-opengl-repro.$$"
fi
mkdir -p "$WORK" || { echo "reproduce.sh: 工作目录不可写: $WORK" >&2; exit 2; }
WORK=$(CDPATH= cd -- "$WORK" && pwd)

log() { echo "$*" >&2; }

log "== KB-NO-OPENGL reproduce =="
log "sample : $SAMPLE"
log "profile: $PROFILE"
log "qt pfx : ${QT_PREFIX:-<detect.sh 自动探测>}"
log "work   : $WORK"

# 干净构建：显式关闭 ccache，避免本地缓存影响结论
CCACHE_DISABLE=1
export CCACHE_DISABLE

run_create() {
    # $1=源码目录 $2=日志文件；返回 conan create 退出码
    ( cd "$1" && conan create . -pr:h="$PROFILE" -pr:b="$PROFILE" ) > "$2" 2>&1
    return $?
}

PHASE_OFF_RC="skip"
PHASE_OFF_HIT=0
PHASE_ON_DETECT_RC="skip"
PHASE_ON_FIX_RC="skip"
PHASE_ON_RC="skip"
PHASE_ON_TEST_HIT=0
OFF_SIG=""

# ================= 阶段 OFF：关 SKILL =================
if [ "$ONLY" = "both" ] || [ "$ONLY" = "off" ]; then
    log ""
    log "-- 阶段 OFF（关 SKILL）：直接 conan create，期望复现原报错 --"
    rm -rf "$WORK/off"
    cp -r "$SAMPLE" "$WORK/off" || exit 2
    run_create "$WORK/off" "$WORK/off.log"
    PHASE_OFF_RC=$?
    # 只看日志文件，不经管道（避免 SIGPIPE）
    if grep -q "use of undeclared identifier" "$WORK/off.log" 2>/dev/null; then
        PHASE_OFF_HIT=1
    fi
    OFF_SIG=$(grep -m1 -o "use of undeclared identifier '[A-Za-z0-9_]*'" "$WORK/off.log" 2>/dev/null)
    log "   conan create rc=$PHASE_OFF_RC  原报错命中=$PHASE_OFF_HIT  ${OFF_SIG:-<无>}"
    log "   日志: $WORK/off.log"
fi

# ================= 阶段 ON：开 SKILL =================
if [ "$ONLY" = "both" ] || [ "$ONLY" = "on" ]; then
    log ""
    log "-- 阶段 ON（开 SKILL）：detect.sh → fix.sh → conan create --"
    rm -rf "$WORK/on"
    cp -r "$SAMPLE" "$WORK/on" || exit 2

    if [ -n "$QT_PREFIX" ]; then
        sh "$SCRIPT_DIR/detect.sh" --src "$WORK/on" --qt-prefix "$QT_PREFIX" \
            --log "$WORK/off.log" > "$WORK/detect.out" 2>&1
    else
        sh "$SCRIPT_DIR/detect.sh" --src "$WORK/on" \
            --log "$WORK/off.log" > "$WORK/detect.out" 2>&1
    fi
    PHASE_ON_DETECT_RC=$?
    if [ "$JSON" -eq 1 ] && [ -f "$WORK/detect.out" ]; then
        :
    fi
    log "   detect.sh rc=$PHASE_ON_DETECT_RC（1=源码使用 GL API；日志: $WORK/detect.out）"

    sh "$SCRIPT_DIR/fix.sh" --src "$WORK/on" --emit-patch "$WORK/kb-no-opengl.patch" \
        > "$WORK/fix.out" 2>&1
    PHASE_ON_FIX_RC=$?
    log "   fix.sh rc=$PHASE_ON_FIX_RC（补丁: $WORK/kb-no-opengl.patch）"

    run_create "$WORK/on" "$WORK/on.log"
    PHASE_ON_RC=$?
    if grep -q "no-GL build keeps the default scaling strategy" "$WORK/on.log" 2>/dev/null; then
        PHASE_ON_TEST_HIT=1
    fi
    log "   conan create rc=$PHASE_ON_RC  测试用例输出命中=$PHASE_ON_TEST_HIT"
    log "   日志: $WORK/on.log"
fi

# ================= 判定 =================
VERDICT=FAIL
REASON=""
if [ "$ONLY" = "off" ]; then
    if [ "$PHASE_OFF_RC" != "0" ] && [ "$PHASE_OFF_HIT" -eq 1 ]; then
        VERDICT=PASS
        REASON="阶段 OFF 复现原报错（${OFF_SIG}）"
    else
        REASON="阶段 OFF 未复现原报错（rc=$PHASE_OFF_RC hit=$PHASE_OFF_HIT）"
    fi
elif [ "$ONLY" = "on" ]; then
    if [ "$PHASE_ON_RC" = "0" ] && [ "$PHASE_ON_TEST_HIT" -eq 1 ]; then
        VERDICT=PASS
        REASON="阶段 ON 开 SKILL 后 conan create 通过且测试用例运行成功"
    else
        REASON="阶段 ON 未通过（create rc=$PHASE_ON_RC test_hit=$PHASE_ON_TEST_HIT）"
    fi
else
    if [ "$PHASE_OFF_RC" != "0" ] && [ "$PHASE_OFF_HIT" -eq 1 ] \
       && [ "$PHASE_ON_RC" = "0" ] && [ "$PHASE_ON_TEST_HIT" -eq 1 ]; then
        VERDICT=PASS
        REASON="阶段 OFF 复现原报错 → 阶段 ON 加门控后通过（SKILL 生效）"
    else
        REASON="两阶段未同时符合预期（off rc=$PHASE_OFF_RC hit=$PHASE_OFF_HIT / on rc=$PHASE_ON_RC test_hit=$PHASE_ON_TEST_HIT）"
    fi
fi

log ""
log "== 结论: $VERDICT — $REASON =="

if [ "$JSON" -eq 1 ]; then
    printf '{"tool":"kb-no-opengl/reproduce","verdict":"%s","reason":"%s",' "$VERDICT" "$REASON"
    printf '"phase_off_rc":"%s","phase_off_signature_hit":%s,"off_signature":"%s",' \
        "$PHASE_OFF_RC" "$PHASE_OFF_HIT" "$OFF_SIG"
    printf '"phase_on_detect_rc":"%s","phase_on_fix_rc":"%s","phase_on_create_rc":"%s","phase_on_test_hit":%s,' \
        "$PHASE_ON_DETECT_RC" "$PHASE_ON_FIX_RC" "$PHASE_ON_RC" "$PHASE_ON_TEST_HIT"
    printf '"work":"%s","sample":"%s"}\n' "$WORK" "$SAMPLE"
fi

if [ "$KEEP" -eq 0 ] && [ "$ONLY" != "off" ]; then
    rm -rf "$WORK"
elif [ "$KEEP" -eq 0 ]; then
    rm -rf "$WORK/on" 2>/dev/null
fi

if [ "$VERDICT" = "PASS" ]; then
    exit 0
fi
exit 1
