#!/bin/sh
# detect-session-bus-deps.sh — 检出「依赖桌面会话」的源码（D-Bus 会话总线 / KDED 装载）
#
# 背景：HarmonyOS PC（OHOS aarch64）没有 KDE 桌面会话 —— 既没有会话 D-Bus 总线
# （DBUS_SESSION_BUS_ADDRESS 未设置、无 dbus-daemon --session），也没有 KDED 守护
# 进程。凡把「桌面会话」当作硬依赖的库，在 OHOS 上要么配置阶段就失败，要么编出
# 永远加载不了 / 永远没有输出的产物。
#
# 命中语义（与本知识库其它检测脚本一致）：**目标平台未声明支持、但源码里当真在用**。
#   - HARD：配置期/链接期硬依赖（find_package(KF6DBusAddons REQUIRED)、KF6::DBusAddons、
#           KDEDModule 插件装载），构建或运行必然失败 → 必须按 strategy.md 处理；
#   - SOFT：运行期可选依赖（QDBusConnection::sessionBus()、KNotification），应降级
#           为无输出/无通知，构建可通过 → 记录并确认有回退路径。
#
# 用法:
#   detect-session-bus-deps.sh [--json] [--quiet] <源码目录>
# 退出码:
#   0 = 未命中（无需处理）
#   1 = 命中 HARD（需按 knowledge/operations/no-desktop-session-dbus-kded/strategy.md 处理）
#   2 = 用法错误
#
# 说明：纯 POSIX sh + find/grep，不依赖 GNU 扩展，可在 OHOS 自带 busybox 上直接跑；
#       不接受写死的绝对路径，源码目录由参数给出。

# 安全模式（code-style 规则 7）：-e 生效处已对“预期非零”的命令（grep -c 无命中、find 权限报错、
# grep 无匹配）逐个显式兜底——检测脚本必须覆盖全部文件，不能因单点非零提前收场。
set -eu -o pipefail

JSON=0
QUIET=0
SRC=""

while [ $# -gt 0 ]; do
    case "$1" in
        --json) JSON=1 ;;
        --quiet) QUIET=1 ;;
        -h|--help)
            echo "usage: $0 [--json] [--quiet] <source-dir>" >&2
            exit 2
            ;;
        *)
            if [ -n "$SRC" ]; then
                echo "usage: $0 [--json] [--quiet] <source-dir>" >&2
                exit 2
            fi
            SRC="$1"
            ;;
    esac
    shift
done

if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
    echo "FAIL: source directory not found: '${SRC}'" >&2
    echo "usage: $0 [--json] [--quiet] <source-dir>" >&2
    exit 2
fi

TMP_BASE="${TMPDIR:-.}"
HITS="$TMP_BASE/.detect-session-bus-$$.tsv"
trap 'rm -f "$HITS"' EXIT INT TERM
: > "$HITS"    # 先建空文件：无命中时也让 grep -c / wc -l 有对象可读（set -e 下不留非零）

# 只看构建描述与源码，跳过 VCS/构建产物目录
list_files() {
    find "$1" -type f \
        \( -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.cxx' \
           -o -name '*.h' -o -name '*.hh' -o -name '*.hpp' -o -name '*.hxx' \
           -o -name '*.cmake' -o -name '*.txt' -o -name '*.in' -o -name '*.json' \
           -o -name '*.desktop' -o -name '*.sh' -o -name '*.build' -o -name '*.py' \) \
        -not -path '*/.git/*' -not -path '*/build/*' -not -path '*/.build/*' \
        -not -path '*/_build/*' 2>/dev/null || true   # 权限受限子树会让 find 非零，不让 -e 因此中断扫描
}

# scan_case <HARD|SOFT> <标签> <扩展正则>
scan_case() {
    kind="$1"; label="$2"; pattern="$3"
    list_files "$SRC" | while IFS= read -r f; do
        # grep 无命中即退出码 1：必须 '|| true' 兜住，否则 -e 会在首个未命中的文件处中断整轮扫描
        grep -n -E "$pattern" "$f" 2>/dev/null | while IFS=: read -r lineno text; do
            printf '%s\t%s\t%s\t%s\t%s\n' \
                "$kind" "$f" "$lineno" "$label" "$(printf '%s' "$text" | tr -s ' \t' ' ' | cut -c1-120)" >> "$HITS"
        done || true
    done
}

# ---- HARD: 配置期/链接期/装载期硬依赖 -------------------------------------
scan_case HARD "cmake:KF6DBusAddons"      'find_package[[:space:]]*\([[:space:]]*KF6DBusAddons'
scan_case HARD "cmake:KF6_COMPONENTS_DBus" 'COMPONENTS[^)]*DBusAddons'
scan_case HARD "cmake:DBusAddons_target"  'KF6::DBusAddons|DBusAddons::DBusAddons'
scan_case HARD "cmake:kded_plugin"        'kcoreaddons_add_plugin|kded_load_plugin|KDEDModule'
scan_case HARD "code:KDEDModule"          'class[[:space:]]+[A-Za-z_]+[[:space:]]*:[[:space:]]*public[[:space:]]+KDEDModule|KDEDModule[[:space:]]*\('
scan_case HARD "code:KPluginFactory_kded" 'K_PLUGIN_FACTORY_WITH_JSON|K_PLUGIN_FACTORY[[:space:]]*\('
scan_case HARD "cmake:plugin_install_dir" 'plugins/kf6/kded|KDE_INSTALL_PLUGINDIR'

# ---- SOFT: 运行期可选依赖（应降级） ---------------------------------------
scan_case SOFT "code:session_bus"         'QDBusConnection::sessionBus|QDBusConnection::[[:space:]]*sessionBus'
scan_case SOFT "code:dbus_call"           'QDBusInterface|QDBusMessage|QDBusReply|QDBusPendingCall'
scan_case SOFT "code:notifications"       'KNotification|KNotifyConfig'
scan_case SOFT "code:kdedsrv"             'org\.kde\.kded|KDBusService'
scan_case SOFT "env:session_bus_addr"     'DBUS_SESSION_BUS_ADDRESS|dbus-launch'

# grep -c 无命中时会打印 0 但退出码为 1：不能再接 `|| echo 0`（会捕获两行，污染 JSON 与数值比较），
# 用 `|| true` 只取它已打印的 0，同时满足 set -e。
HARD_N=$(grep -c '^HARD' "$HITS" 2>/dev/null || true); HARD_N=${HARD_N:-0}
SOFT_N=$(grep -c '^SOFT' "$HITS" 2>/dev/null || true); SOFT_N=${SOFT_N:-0}

# 判定词只算一次，供 --json 与文本两种输出共用（避免两处口径漂移）
if [ "$HARD_N" -gt 0 ]; then VERDICT=needs_strategy; else VERDICT=ok; fi

if [ "$JSON" -eq 1 ]; then
    # JSON 整体交给 awk：逐字符转义（不依赖 sub/gsub 替换操作数的历史语义差异），
    # 值经 ENVIRON 传入（-v 会解释值里的转义序列，路径含反斜杠时会走样）。
    SRC="$SRC" HARD_N="$HARD_N" SOFT_N="$SOFT_N" VERDICT="$VERDICT" LC_ALL=C \
    awk -F'\t' '
    function esc(s,   i, c, out) {
        out = ""
        for (i = 1; i <= length(s); i++) {
            c = substr(s, i, 1)
            if (c == "\\")      out = out "\\\\"
            else if (c == "\"") out = out "\\\""
            else if (c < " ")   out = out " "
            else                out = out c
        }
        return out
    }
    BEGIN {
        printf "{\n  \"source_dir\": \"%s\",\n  \"hard_hits\": %s,\n  \"soft_hits\": %s,\n", esc(ENVIRON["SRC"]), ENVIRON["HARD_N"], ENVIRON["SOFT_N"]
        printf "  \"verdict\": \"%s\",\n", esc(ENVIRON["VERDICT"])
        printf "  \"strategy_doc\": \"knowledge/operations/no-desktop-session-dbus-kded/strategy.md\",\n"
        printf "  \"hits\": [\n"
    }
    {
        if (NR > 1) printf ",\n"
        printf "    {\"kind\": \"%s\", \"file\": \"%s\", \"line\": %s, \"rule\": \"%s\", \"text\": \"%s\"}", esc($1), esc($2), $3, esc($4), esc($5)
    }
    END { printf "\n  ]\n}\n" }
    ' "$HITS"
else
    if [ "$QUIET" -eq 0 ]; then
        echo "# detect-session-bus-deps: $SRC"
        if [ -s "$HITS" ]; then
            awk -F'\t' '{printf "%-4s %-22s %s:%s\t%s\n", $1, $4, $2, $3, $5}' "$HITS"
        else
            echo "（无命中）"
        fi
    fi
    echo "HARD=$HARD_N SOFT=$SOFT_N"
    if [ "$HARD_N" -gt 0 ]; then
        echo "VERDICT: needs_strategy — 存在桌面会话硬依赖，见 knowledge/operations/no-desktop-session-dbus-kded/strategy.md"
    else
        echo "VERDICT: ok — 无桌面会话硬依赖（SOFT 命中请确认已有降级路径）"
    fi
fi

if [ "$HARD_N" -gt 0 ]; then
    exit 1
fi
exit 0
