#!/bin/sh
# test_overtls.sh — 消费者侧真实执行 overtls 交付物（R34：真实执行 + 断言，非存在性）
# 用法: sh test_overtls.sh <pkg_dir>
#
# 覆盖四层（每层都是真断言，逐项打印 [ok]/[FAIL]）：
#   A. CLI 契约    —— --version / --help / 未知参数错误路径
#   B. 配置校验    —— 角色与配置不匹配必须非零退出
#   C. 服务发现    —— 服务端 TCP 监听、客户端 SOCKS5 监听（OHOS socket API 真实可用）
#   D. 数据面      —— SOCKS5 握手 → overtls WebSocket 隧道 → 服务端 TCP 转发 →
#                     回显目标 往返字节一致（端到端，不 mock）
# 依赖: python3（conan 运行期自带；仅用于起回显目标与发起 SOCKS5 探针）
set -u

PKG="${1:?usage: test_overtls.sh <pkg_dir>}"
BIN="$PKG/bin/overtls-bin"
FAIL=0
NPASS=0
NFAIL=0
SRV_PID=""
CLI_PID=""
ECHO_PID=""

say()  { printf '%s\n' "$*"; }
ok()   { NPASS=$((NPASS + 1)); say "  [ok]   $*"; }
bad()  { FAIL=1; NFAIL=$((NFAIL + 1)); say "  [FAIL] $*"; }

# ── python3 定位（设备 PATH 可能随 HOME 变化，逐候选回退）────────────
PY=""
for c in python3 /usr/bin/python3 /data/service/hnp/bin/python3 \
         /storage/Users/currentUser/usr/local/bin/python3; do
    if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then
        PY="$c"
        break
    fi
done
[ -n "$PY" ] || { say "  [FAIL] python3 not available — cannot run socket probe"; exit 1; }

say "== overtls 交付物真实执行 =="

cleanup() {
    [ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null
    [ -n "$CLI_PID" ] && kill "$CLI_PID" 2>/dev/null
    [ -n "$ECHO_PID" ] && kill "$ECHO_PID" 2>/dev/null
    wait 2>/dev/null
    # 必须清理工作目录：本脚本由 `conan create` 在 test_package/ 目录**原地**执行
    # （实测 PWD = archives/o/overtls/0.3.12/test_package/，generators 也落在这里），
    # 不清理就会把 overtls-tp-work/（含 *.log）留进 git worktree——而提交面 *.log
    # 是 CI 门禁 H1 的硬拦项、测试产物也不得入库。失败时的两侧日志已在 D 段留档。
    [ -n "${WORK:-}" ] && rm -rf "$WORK" 2>/dev/null
    return 0
}
trap cleanup EXIT INT TERM

[ -x "$BIN" ] || { say "  [FAIL] binary not executable: $BIN"; exit 1; }

WORK="$PWD/overtls-tp-work"
rm -rf "$WORK" 2>/dev/null
mkdir -p "$WORK" || { say "  [FAIL] cannot create $WORK"; exit 1; }

# ══ A. CLI 契约 ══════════════════════════════════════════════════════

# A1 —— --version 必须可用且报出 0.3.12
# 上游 version_info() = "<crate_version> (<GIT_HASH> <BUILD_TIME>)"，BUILD_TIME
# 是编译时刻，故只断言核心版本号子串、不锚定整串。
if OUT=$("$BIN" --version 2>&1); then
    say "  --version → $(printf '%s' "$OUT" | head -1)"
    case "$OUT" in
        *0.3.12*) ok "A1 --version 报出 0.3.12" ;;
        *)        bad "A1 --version 未报出 0.3.12: $OUT" ;;
    esac
else
    bad "A1 --version 执行失败 rc=$? out=$(printf '%s' "$OUT" | head -1)"
fi

# A2 —— --help 必须列出角色参数（clap 命令树真实存在）
if OUT=$("$BIN" --help 2>&1); then
    say "  --help 首行: $(printf '%s' "$OUT" | head -1)"
    case "$OUT" in
        *"Role of server or client"*) ok "A2 --help 列出 --role 参数说明" ;;
        *)                           bad "A2 --help 未见 --role 参数说明" ;;
    esac
else
    bad "A2 --help 执行失败 rc=$?"
fi

# A3 —— 未知参数须以非零退出（错误路径不被吞掉）
if "$BIN" --definitely-not-a-flag >/dev/null 2>&1; then
    bad "A3 未知参数竟以 0 退出"
else
    ok "A3 未知参数以非零退出"
fi

# ══ 运行期探针脚本（写入工作目录后执行，便于失败时人工复跑）════════

cat > "$WORK/echo_server.py" <<'PYEOF'
import socket, sys, threading
port = int(sys.argv[1])
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", port))
srv.listen(16)
srv.settimeout(60)
def handle(c):
    try:
        while True:
            d = c.recv(4096)
            if not d:
                break
            c.sendall(d)
    except OSError:
        pass
    finally:
        try:
            c.close()
        except OSError:
            pass
while True:
    try:
        c, _ = srv.accept()
    except socket.timeout:
        break
    except OSError:
        break
    threading.Thread(target=handle, args=(c,), daemon=True).start()
PYEOF

cat > "$WORK/wait_port.py" <<'PYEOF'
import socket, sys, time
host, port = sys.argv[1], int(sys.argv[2])
deadline = time.time() + 20
while time.time() < deadline:
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        print("OPEN")
        sys.exit(0)
    except Exception:
        time.sleep(0.25)
print("TIMEOUT")
sys.exit(1)
PYEOF

cat > "$WORK/socks5_probe.py" <<'PYEOF'
import socket, struct, sys, time
proxy_host, proxy_port = sys.argv[1], int(sys.argv[2])
dst_host, dst_port = sys.argv[3], int(sys.argv[4])
payload = sys.argv[5].encode()

s = None
deadline = time.time() + 20
while time.time() < deadline:
    try:
        s = socket.create_connection((proxy_host, proxy_port), timeout=2)
        break
    except Exception:
        time.sleep(0.25)
if s is None:
    print("SOCKS_CONNECT_TIMEOUT")
    sys.exit(2)
s.settimeout(15)
try:
    # ① 协商
    s.sendall(b"\x05\x01\x00")
    resp = s.recv(2)
    if resp != b"\x05\x00":
        print("SOCKS_METHOD_FAIL %r" % resp)
        sys.exit(3)
    print("SOCKS5_METHOD_OK")
    # ② CONNECT
    req = (b"\x05\x01\x00\x01" + socket.inet_aton(dst_host)
           + struct.pack("!H", dst_port))
    s.sendall(req)
    resp = s.recv(10)
    if len(resp) < 2 or resp[0] != 5 or resp[1] != 0:
        print("SOCKS5_CONNECT_FAIL %r" % resp)
        sys.exit(4)
    print("SOCKS5_CONNECT_OK")
    # ③ 数据面往返
    s.sendall(payload)
    got = b""
    while len(got) < len(payload):
        chunk = s.recv(len(payload) - len(got))
        if not chunk:
            break
        got += chunk
    if got != payload:
        print("DATA_ROUNDTRIP_FAIL want=%r got=%r" % (payload, got))
        sys.exit(5)
    print("DATA_ROUNDTRIP_OK")
except Exception as exc:  # noqa: BLE001 - 探针需把异常原样打印给断言层
    print("PROBE_ERROR %s" % exc)
    sys.exit(6)
finally:
    try:
        s.close()
    except OSError:
        pass
PYEOF

# ── 端口分配：一次性申请 3 个空闲端口，降低与共享设备上其他任务的碰撞面 ──
PORTS=$("$PY" - <<'PYEOF'
import socket
socks = []
for _ in range(3):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    socks.append(s)
print(" ".join(str(s.getsockname()[1]) for s in socks))
for s in socks:
    s.close()
PYEOF
) || { bad "B0 端口分配失败"; exit 1; }
set -- $PORTS
ECHO_PORT="$1"; SRV_PORT="$2"; CLI_PORT="$3"
say "  ports: echo=$ECHO_PORT server=$SRV_PORT socks5=$CLI_PORT"

# ── 配置文件（上游 schema 见 src/config.rs；两份配置共用 tunnel_path）──
"$PY" - "$WORK" "$ECHO_PORT" "$SRV_PORT" "$CLI_PORT" <<'PYEOF'
import json, sys
work, echo_port, srv_port, cli_port = (sys.argv[1], int(sys.argv[2]),
                                       int(sys.argv[3]), int(sys.argv[4]))
tunnel = "/secret-tunnel-path/"
# 服务端 + 客户端同文件（上游 config.json 的形态）
both = {
    "remarks": "overtls test_package",
    "test_timeout_secs": 5,
    "method": "none",
    "password": "password",
    "tunnel_path": tunnel,
    "server_settings": {
        "disable_tls": True,
        "forward_addr": "http://127.0.0.1:%d" % echo_port,
        "listen_host": "127.0.0.1",
        "listen_port": srv_port,
    },
    "client_settings": {
        "disable_tls": True,
        "server_host": "127.0.0.1",
        "server_port": srv_port,
        "server_domain": "127.0.0.1",
        "dangerous_mode": True,
        "listen_host": "127.0.0.1",
        "listen_port": cli_port,
    },
}
with open(work + "/overtls-tp.json", "w") as fh:
    json.dump(both, fh, indent=4)
# 仅客户端段的配置——用于「角色与配置不匹配必须报错」的负向断言
client_only = dict(both)
client_only.pop("server_settings")
with open(work + "/client-only.json", "w") as fh:
    json.dump(client_only, fh, indent=4)
print("configs written")
PYEOF

# ══ B. 配置校验负向路径 ══════════════════════════════════════════════
if OUT=$("$BIN" -r server -c "$WORK/client-only.json" 2>&1); then
    bad "B1 角色=server 却拿到仅客户端配置，竟以 0 退出"
else
    say "  负向输出: $(printf '%s' "$OUT" | head -1)"
    ok "B1 角色与配置不匹配时非零退出"
fi

# ══ C. 服务发现（OHOS socket / tokio 监听真实可用）══════════════════

# C0 —— 回显目标（上游数据面的最终落点）
"$PY" "$WORK/echo_server.py" "$ECHO_PORT" > "$WORK/echo.log" 2>&1 &
ECHO_PID=$!

# C1 —— 服务端进程启动
"$BIN" -r server -c "$WORK/overtls-tp.json" > "$WORK/server.log" 2>&1 &
SRV_PID=$!
sleep 2
if kill -0 "$SRV_PID" 2>/dev/null; then
    ok "C1 服务端进程存活 (pid=$SRV_PID)"
else
    bad "C1 服务端进程已退出: $(tail -3 "$WORK/server.log" 2>/dev/null | tr '\n' ' ')"
fi

# C2 —— 服务端 TCP 监听端口可连接
if "$PY" "$WORK/wait_port.py" 127.0.0.1 "$SRV_PORT" >/dev/null 2>&1; then
    ok "C2 服务端 127.0.0.1:$SRV_PORT 可连接（tokio TcpListener 已监听）"
else
    bad "C2 服务端端口 127.0.0.1:$SRV_PORT 20s 内不可连接"
fi

# C3 —— 客户端进程启动（其配置校验阶段会对服务端做一次真实 TCP 连接）
"$BIN" -r client -c "$WORK/overtls-tp.json" > "$WORK/client.log" 2>&1 &
CLI_PID=$!
sleep 2
if kill -0 "$CLI_PID" 2>/dev/null; then
    ok "C3 客户端进程存活 (pid=$CLI_PID)"
else
    bad "C3 客户端进程已退出: $(tail -3 "$WORK/client.log" 2>/dev/null | tr '\n' ' ')"
fi

# C4 —— 客户端 SOCKS5 监听端口可连接
if "$PY" "$WORK/wait_port.py" 127.0.0.1 "$CLI_PORT" >/dev/null 2>&1; then
    ok "C4 客户端 SOCKS5 127.0.0.1:$CLI_PORT 可连接"
else
    bad "C4 客户端 SOCKS5 端口 127.0.0.1:$CLI_PORT 20s 内不可连接"
fi

# ══ D. 数据面：SOCKS5 → overtls 隧道 → 服务端 TCP 转发 → 回显 ═══════
PAYLOAD="overtls-harmonyos-pc-roundtrip-0123456789"
# 目标地址用 0.0.0.0 而**不是** 127.0.0.1：上游服务端对隧道目标有 SSRF 防护
# ——`src/server.rs:664 tcp_stream_from_s5_address()` 对每个候选地址无条件判
# `addr_is_private()`（private/loopback/link-local/benchmarking）并 `continue`
# 跳过，且 `server_settings` 里**没有任何开关**可以放开它（src/config.rs 的
# `Server` 只有 disable_tls/panel_sync/certfile/keyfile/forward_addr/listen_*）。
# 实测用 127.0.0.1 时服务端逐字打：
#   [WARN ] ... destination address is private, skipping
#   [ERROR] ... failed to create connection to address '127.0.0.1:<echo>':
#           All addresses failed to connect
# 随后回 "End session"，客户端随即关闭 SOCKS5 连接（探针见 Connection reset）。
# 0.0.0.0（INADDR_ANY）**不在** 上述四类里（Rust Ipv4Addr::is_private/is_loopback/
# is_link_local 对 0.0.0.0 全为 false），而 Linux/OHOS 内核对 connect(0.0.0.0:port)
# 按目标为回环处理 → 既通过 SSRF 检查、又真实落到本机回显目标，因此这条路仍是
# **真实端到端数据面**（探针字节 → SOCKS5 → WS 隧道 → 服务端出站 TCP → 回显 → 原路返回），
# 不是 mock、也不是存在性检查。
PROBE_OUT=$("$PY" "$WORK/socks5_probe.py" 127.0.0.1 "$CLI_PORT" \
             0.0.0.0 "$ECHO_PORT" "$PAYLOAD" 2>&1)
PROBE_RC=$?
say "  probe 输出:"
printf '%s\n' "$PROBE_OUT" | sed 's/^/    /'

# 失败时先把两侧日志尾部留档——工作目录随后会被 trap cleanup 删掉，不留进 worktree
if [ "$PROBE_RC" -ne 0 ]; then
    say "  --- server.log (tail 15) ---"
    tail -15 "$WORK/server.log" 2>/dev/null | sed 's/^/    /'
    say "  --- client.log (tail 15) ---"
    tail -15 "$WORK/client.log" 2>/dev/null | sed 's/^/    /'
fi

case "$PROBE_OUT" in
    *SOCKS5_METHOD_OK*)  ok "D1 SOCKS5 协商成功 (method=0x00 无认证)" ;;
    *)                   bad "D1 SOCKS5 协商失败 (rc=$PROBE_RC)" ;;
esac
case "$PROBE_OUT" in
    *SOCKS5_CONNECT_OK*) ok "D2 SOCKS5 CONNECT 成功（reply=0x00）" ;;
    *)                   bad "D2 SOCKS5 CONNECT 失败 (rc=$PROBE_RC)" ;;
esac
case "$PROBE_OUT" in
    *DATA_ROUNDTRIP_OK*) ok "D3 数据面回显字节一致（隧道端到端往返 ${#PAYLOAD} 字节）" ;;
    *)                   bad "D3 数据面回显不一致 (rc=$PROBE_RC)" ;;
esac
[ "$PROBE_RC" -eq 0 ] && ok "D4 SOCKS5 探针整体 rc=0" \
                     || bad "D4 SOCKS5 探针整体 rc=$PROBE_RC"

# ══ E. 打包产物 ══════════════════════════════════════════════════════
if [ -f "$PKG/share/overtls/config.json" ]; then
    ok "E1 上游默认配置样例随包分发 share/overtls/config.json"
else
    bad "E1 缺 share/overtls/config.json"
fi
if [ -f "$PKG/licenses/LICENSE" ]; then
    ok "E2 LICENSE 随包分发"
else
    bad "E2 缺 licenses/LICENSE"
fi

# ── 汇总 ──────────────────────────────────────────────────────────────
TOTAL=$((NPASS + NFAIL))
say ""
if [ "$FAIL" -eq 0 ]; then
    say "OK: overtls 交付物 $NPASS/$TOTAL 项断言全部通过"
    printf 'HMBS_TEST_PACKAGE_RESULT={"status":"passed","framework":"test_overtls.sh","discovered":%s,"executed":%s,"passed":%s,"failed":0,"skipped":0}\n' \
        "$TOTAL" "$TOTAL" "$NPASS"
    exit 0
else
    say "FAILED: overtls 交付物存在未通过断言（passed=$NPASS total=$TOTAL）"
    printf 'HMBS_TEST_PACKAGE_RESULT={"status":"failed","framework":"test_overtls.sh","discovered":%s,"executed":%s,"passed":%s,"failed":%s,"skipped":0}\n' \
        "$TOTAL" "$TOTAL" "$NPASS" "$NFAIL"
    exit 1
fi
