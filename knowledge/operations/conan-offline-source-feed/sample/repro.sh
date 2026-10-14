#!/bin/sh
# repro.sh — conan 离线源喂包共性问题复现脚本（样例库: japa 0.9.4）
#
# 用法:
#   bash repro.sh <japa配方目录> <源码包tarball> <工作目录> <ohos profile 路径>
#
# 阶段 A（不启用方案）: download_urls 用 file:// —— conan create 在 source() 失败，
#   复现 "No connection adapters were found" / "not found in remote backup" 报错。
# 阶段 B（启用方案）: 本地 http.server 喂 <sha256> + <sha256>.json 成对文件，
#   conan create 全流程通过。
#
# 规约:
#   - 所有日志重定向到文件（规避 SIGPIPE，不用管道 head）
#   - 不写死本地绝对路径：全部路径来自参数
#   - sha256 由 tarball 内容实算，不假设文件名

set -u

RECIPE_DIR="$1"
TARBALL="$2"
WORK_DIR="$3"
PROFILE="$4"

[ -d "$RECIPE_DIR" ] || { echo "recipe dir missing" >&2; exit 2; }
[ -f "$TARBALL" ]    || { echo "tarball missing" >&2; exit 2; }
[ -f "$PROFILE" ]    || { echo "profile missing" >&2; exit 2; }

CONF="${OHC_CONAN_GLOBAL_CONF:-$HOME/.conan2/global.conf}"
PORT=18732
BACKUP_DIR="$WORK_DIR/backup-src"
mkdir -p "$BACKUP_DIR"

SHA=$(sha256sum "$TARBALL" | awk '{print $1}')
cp "$TARBALL" "$BACKUP_DIR/$SHA"

run_create() {
    # run_create <log-file>
    conan create "$RECIPE_DIR" \
        -pr:h="$PROFILE" -pr:b="$PROFILE" \
        --build=japa --build=missing > "$1" 2>&1
    echo $?
}

# ---- 阶段 A: file:// scheme（复现原始报错） --------------------------------
cp "$CONF" "$WORK_DIR/global.conf.bak"
{
    echo "core.sources:download_cache=$WORK_DIR/dl-cache"
    echo "core.sources:download_urls=[\"file://$BACKUP_DIR\"]"
} > "$CONF"
mkdir -p "$WORK_DIR/dl-cache"

RC_A=$(run_create "$WORK_DIR/repro-A-file-scheme.log")
grep -m1 -E "No connection adapters|not found in remote backup|No scheme supplied" \
    "$WORK_DIR/repro-A-file-scheme.log" > "$WORK_DIR/repro-A-signature.txt" || true

# ---- 阶段 B: HTTP 喂源 + 成对 json（方案生效） -----------------------------
printf '{"references": {"japa/0.9.4": ["https://kokkinizita.linuxaudio.org/linuxaudio/downloads/japa-0.9.4.tar.bz2"]}, "timestamp": %s}' \
    "$(date +%s)" > "$BACKUP_DIR/$SHA.json"

# 起本地源服务（后台），退出时清理
(cd "$BACKUP_DIR" && python3 -m http.server "$PORT" --bind 127.0.0.1 > "$WORK_DIR/http-server.log" 2>&1) &
SRV_PID=$!
trap 'kill "$SRV_PID" 2>/dev/null; cp "$WORK_DIR/global.conf.bak" "$CONF"' EXIT INT TERM

# 等服务就绪（最多 10s）
i=0
while [ "$i" -lt 20 ]; do
    if wget -q -O /dev/null "http://127.0.0.1:$PORT/$SHA" 2>/dev/null; then
        break
    fi
    i=$((i + 1))
    sleep 0.5
done

echo "core.sources:download_cache=$WORK_DIR/dl-cache" > "$CONF"
echo "core.sources:download_urls=[\"http://127.0.0.1:$PORT/\"]" >> "$CONF"

RC_B=$(run_create "$WORK_DIR/repro-B-http-feed.log")

kill "$SRV_PID" 2>/dev/null
cp "$WORK_DIR/global.conf.bak" "$CONF"
trap - EXIT INT TERM

# ---- 判决 -------------------------------------------------------------------
echo "=== REPRO RESULT ==="
echo "A_without_skill: rc=$RC_A signature=$(cat "$WORK_DIR/repro-A-signature.txt" 2>/dev/null || echo none)"
echo "B_with_skill:    rc=$RC_B"
if [ "$RC_A" -ne 0 ] && [ "$RC_B" -eq 0 ]; then
    echo "VERDICT: PASS (不启用方案报错复现, 启用方案编译通过)"
    exit 0
elif [ "$RC_B" -eq 0 ]; then
    echo "VERDICT: PARTIAL (阶段A未复现报错——可能上游URL本机可达, 见README边界)"
    exit 0
else
    echo "VERDICT: FAIL"
    exit 1
fi
