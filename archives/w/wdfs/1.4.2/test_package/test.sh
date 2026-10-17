#!/usr/bin/env bash
# wdfs 1.4.2 消费者测试（上游零测试用例，本文件为补充的自研测试）。
#
# 覆盖三条真实执行路径 + 一条端到端用例：
#   1) --version            -> KEY_VERSION 分支 exit(0)，banner 含版本号
#   2) --help               -> print_help + fuse "-ho"（FUSE 库与参数构造闭合）
#   3) 无参数               -> "missing webdav uri" 校验分支 exit(1)
#   4) 端到端：本地最小 WebDAV server + 真实 neon HTTP 会话（ne_options），
#      验证 wdfs 确实完成 WebDAV 握手（server 侧记录到 OPTIONS 请求），
#      再进入 FUSE 挂载阶段。挂载本身在无 /dev/fuse 的环境不可达，
#      因此以"server 收到 OPTIONS + 进程未崩溃(非 126/127/139)"为通过条件。
set -u

BIN="$(command -v wdfs 2>/dev/null || true)"
if [ -z "$BIN" ]; then
    echo "FAIL: wdfs 未安装到 PATH"
    exit 1
fi
echo "binary: $BIN"
"$BIN" --version 2>&1 || true

PASS=0
FAIL=0
ok()  { echo "PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

WORKDIR="${TMPDIR:-/tmp}/wdfs-consumer-test-$$"
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"; [ -n "${SRV_PID:-}" ] && kill "$SRV_PID" 2>/dev/null' EXIT

# ── 1) 版本分支 ───────────────────────────────────────────────────────
out="$("$BIN" --version 2>&1)"
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "wdfs version: 1.4.2"; then
    ok "--version: banner 含 'wdfs version: 1.4.2'，rc=0"
else
    bad "--version: rc=$rc output=[$out]"
fi

# ── 2) 帮助分支（同时验证 FUSE 库符号闭合与参数构造） ────────────────
out="$("$BIN" --help 2>&1)"
rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q "locking_timeout"; then
    ok "--help: 打印 wdfs 选项帮助，rc=1"
else
    bad "--help: rc=$rc output=[$out]"
fi

# ── 3) 缺少 webdav uri 的校验分支 ────────────────────────────────────
out="$("$BIN" 2>&1)"
rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q "missing webdav uri"; then
    ok "无参数: 报 'missing webdav uri'，rc=1"
else
    bad "无参数: rc=$rc output=[$out]"
fi

# ── 4) 端到端：真实 WebDAV 会话（本地 stub server） ──────────────────
if command -v python3 >/dev/null 2>&1; then
    PORT="$(python3 -c 'import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()')"
    SRV_LOG="$WORKDIR/server.log"
    MNT="$WORKDIR/mnt"
    mkdir -p "$MNT"
    python3 "$(dirname "$0")/webdav_stub.py" "$PORT" "$SRV_LOG" \
        >"$WORKDIR/server.out" 2>&1 &
    SRV_PID=$!
    # 等待 stub server 就绪（最多 20s）
    i=0
    while [ "$i" -lt 40 ]; do
        if python3 -c "import socket,sys
s = socket.socket()
s.settimeout(1)
sys.exit(s.connect_ex(('127.0.0.1', $PORT)))" 2>/dev/null; then
            break
        fi
        sleep 0.5
        i=$((i + 1))
    done

    out="$(timeout 30 "$BIN" -f -o username=test -o password=test \
        "http://127.0.0.1:$PORT/dav" "$MNT" 2>&1)"
    rc=$?
    seen="$(cat "$SRV_LOG" 2>/dev/null || true)"
    echo "wdfs rc=$rc output=[$out]"
    echo "server log=[$seen]"

    if printf '%s' "$seen" | grep -q "^OPTIONS "; then
        ok "端到端: 本地 WebDAV server 收到 wdfs 的真实 OPTIONS 请求（neon 会话建立）"
    else
        bad "端到端: server 未收到 OPTIONS 请求（wdfs 未完成 WebDAV 握手）"
    fi

    # 0=挂载成功被 timeout 结束？(不会) 1=预期失败(无 /dev/fuse) 124=timeout 杀掉运行中的进程
    if [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ] || [ "$rc" -eq 124 ]; then
        ok "端到端: wdfs 进程正常结束，无崩溃（rc=$rc）"
    else
        bad "端到端: wdfs 异常退出 rc=$rc（126/127/139 视为失败）"
    fi
else
    bad "python3 不可用，无法执行 WebDAV 端到端用例"
fi

echo "-----------------------------------------"
echo "assertions: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
