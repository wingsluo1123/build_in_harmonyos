#!/bin/sh
# detect-conan-offline-source.sh — Conan 离线源喂包共性问题检测
#
# 检测三类 blocker（详见同目录 README.md）：
#   1. global.conf 的 core.sources:download_urls 使用 conan 不支持的 scheme
#      （file:// 无 connection adapter、裸路径 No scheme supplied）
#   2. backup 源 sha256 包缺少成对的 <sha256>.json 元数据
#      （conan caching_file_downloader 要求 sha256 与 json 成对下载）
#   3. conan 日志命中离线源失效的 error_signature
#
# 用法:
#   bash detect-conan-offline-source.sh [--conf <global.conf>] [--log <conan日志>...] [--json] [--quiet]
#
# 退出码: 0=无 blocker（warn 不阻断） 2=用法错误 10=存在 blocker
#
# 平台: OHOS aarch64（toybox ash 兼容：不用 mapfile/关联数组/管道 head）
# 无本地绝对路径写死：conf 路径默认取 $HOME 下标准位置，全部可参数覆盖。

set -u

CONF="${OHC_CONAN_GLOBAL_CONF:-$HOME/.conan2/global.conf}"
JSON=0
QUIET=0
# blocker 判定走落盘文件计数：emit 可能发生在管道子 shell（toybox 无进程替换，
# 子 shell 计数无法带回主 shell），主 shell 结束时统一数 [blocker] 行。
WORK="${TMPDIR:-$HOME/tmp}/detect-conan-offline-source.$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT INT TERM

while [ $# -gt 0 ]; do
    case "$1" in
        --conf)  CONF="$2"; shift 2 ;;
        --json)  JSON=1; shift ;;
        --quiet) QUIET=1; shift ;;
        --log)   LOGS="${LOGS:-} $2"; shift 2 ;;
        -h|--help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *)
            echo "unknown option: $1" >&2
            exit 2
            ;;
    esac
done

emit() {
    # emit <level> <code> <message>
    if [ "$JSON" -eq 1 ]; then
        printf '{"level":"%s","code":"%s","message":"%s"}\n' "$1" "$2" "$3"
    elif [ "$QUIET" -eq 0 ]; then
        printf '[%s] %s: %s\n' "$1" "$2" "$3"
    fi
    printf '%s\n' "$2" >> "$WORK/codes"
}

# ---- 1. 配置扫描：download_urls scheme 合法性 -----------------------------
if [ ! -f "$CONF" ]; then
    emit info "CONF_ABSENT" "no global.conf at $CONF — conan 走默认源，本条不适用"
else
    # 取未被注释的 download_urls / download_cache 行
    URLS_LINE=$(grep -E '^core\.sources:download_urls=' "$CONF" | tail -n 1 || true)
    CACHE_LINE=$(grep -E '^core\.sources:download_cache=' "$CONF" | tail -n 1 || true)

    if [ -n "$URLS_LINE" ]; then
        # 逐个提取引号内的 URL（toybox 无 grep -P，用 sed 逐条剥离）
        echo "$URLS_LINE" | tr ',' '\n' | grep -o '"[^"]*"' | tr -d '"' | while IFS= read -r u; do
            [ -z "$u" ] && continue
            case "$u" in
                http://*|https://*)
                    # TEMP 残留标记检测（上一次任务的临时配置忘还原）
                    if grep -q "^# TEMP" "$CONF" 2>/dev/null; then
                        emit warn "TEMP_RESIDUE" "global.conf 含 TEMP 临时源配置残留: $u（用后应还原，防污染下一个任务）"
                    fi
                    ;;
                file://*)
                    emit blocker "FILE_SCHEME" "download_urls 含 file:// — 本机 conan 的 requests 无 file adapter（No connection adapters were found），改用本地 http.server"
                    ;;
                http*)
                    ;;
                *)
                    emit blocker "NO_SCHEME" "download_urls 条目缺 scheme: $u（裸路径报 No scheme supplied，需 http:// 前缀）"
                    ;;
            esac
        done
    fi
fi

# ---- 2. backup 源 sha256 成对完整性 ----------------------------------------
# 对 http 型 backup base，尝试解析出本地对应目录（本机目录或 HTTP 目录列举），
# 校验 <sha256> 与 <sha256>.json 成对。
if [ -f "$CONF" ] && [ -n "${URLS_LINE:-}" ]; then
    echo "$URLS_LINE" | tr ',' '\n' | grep -o '"[^"]*"' | tr -d '"' | while IFS= read -r u; do
        case "$u" in
            http://127.0.0.1:*|http://localhost:*)
                # 本机 HTTP 喂源：从端口推断无法直接拿目录，跳过成对校验，
                # 由 --log 的签名匹配兜底（NotFound in remote backup 即缺文件或缺 json）。
                ;;
            file://*|http://*|https://*)
                ;;
        esac
    done
    # download_cache 目录的成对校验（本地目录可直接列举）
    if [ -n "${CACHE_LINE:-}" ]; then
        CACHE_DIR=$(printf '%s' "$CACHE_LINE" | sed -e 's/^core.sources:download_cache=//' -e 's/^"//' -e 's/"$//')
        if [ -d "$CACHE_DIR" ]; then
            for f in "$CACHE_DIR"/*; do
                [ -f "$f" ] || continue
                case "$f" in
                    *.json|*.lock) continue ;;
                esac
                if [ ! -f "$f.json" ]; then
                    emit blocker "CACHE_JSON_MISSING" "download_cache 条目缺元数据: $(basename "$f") 无配套 .json（conan 缓存命中分支同样校验元数据）"
                fi
            done
        fi
    fi
fi

# ---- 3. 日志 error_signature 匹配 ------------------------------------------
for log in ${LOGS:-}; do
    [ -f "$log" ] || continue
    if grep -q "not found in remote backup" "$log" 2>/dev/null; then
        emit blocker "BACKUP_NOT_FOUND" "$log: backup 源取不到 sha256 包或缺成对 .json（README §4 策略1/2）"
    fi
    if grep -q "No connection adapters were found" "$log" 2>/dev/null; then
        emit blocker "NO_ADAPTER" "$log: file:// scheme 不被 conan 的 requests 支持（README §4 策略1）"
    fi
    if grep -q "No scheme supplied" "$log" 2>/dev/null; then
        emit blocker "NO_SCHEME_LOG" "$log: download_urls 裸路径缺 scheme（README §4 策略1）"
    fi
    if grep -q "Error downloading file" "$log" 2>/dev/null && grep -qE "127\.0\.0\.1|localhost" "$log" 2>/dev/null; then
        emit warn "LOCAL_DL_FAIL" "$log: 本地喂源下载失败——检查 http.server 是否存活/端口是否与 download_urls 一致"
    fi
done

if [ "$JSON" -eq 0 ] && [ "$QUIET" -eq 0 ]; then
    echo ""
    echo "策略（README §4）："
    echo "  1. HTTP 喂源: 目录内成对放 <内容sha256> 与 <内容sha256>.json，download_urls 指向 http://127.0.0.1:<port>/"
    echo "  2. download_cache 预置: 同样成对放进 cache 目录，conan 命中本地缓存跳过远端"
    echo "  3. 配置卫生: TEMP 配置用后还原 global.conf"
fi

# 主 shell 统一数 blocker（覆盖管道子 shell 里的 emit）
CODES_FILE="$WORK/codes"
if [ -f "$CODES_FILE" ] && grep -qE '^(FILE_SCHEME|NO_SCHEME|CACHE_JSON_MISSING|BACKUP_NOT_FOUND|NO_ADAPTER|NO_SCHEME_LOG)$' "$CODES_FILE"; then
    exit 10
fi
exit 0
