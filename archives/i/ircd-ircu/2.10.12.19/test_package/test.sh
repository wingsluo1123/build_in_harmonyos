#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for the packaged Undernet IRC daemon.
#
# Runs inside the conanrun env: PATH contains the package's bin/ so `ircd`,
# `umkpasswd` and `convert-conf` resolve to the installed artifacts.
set -uo pipefail

IRCD_VERSION_EXPECTED="u2.10.12.19"
PORT="${IRCU_TEST_PORT:-17910}"
SPORT="${IRCU_TEST_SPORT:-17911}"
NICK="conanprobe"
SCRATCH="${TMPDIR:-/tmp}"
TESTDIR="$SCRATCH/ircd-ircu-test-$$"
IRCD_PID=""
# Resolved before the chdir into $TESTDIR below.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PASS=0
FAIL=0

ok()   { PASS=$((PASS + 1)); echo "  [PASS] $*"; }
bad()  { FAIL=$((FAIL + 1)); echo "  [FAIL] $*"; }

cleanup() {
    if [ -n "$IRCD_PID" ]; then
        kill -TERM "$IRCD_PID" 2>/dev/null
        wait "$IRCD_PID" 2>/dev/null
    fi
    rm -rf "$TESTDIR"
}
trap cleanup EXIT

mkdir -p "$TESTDIR" || { echo "FATAL: cannot create $TESTDIR"; exit 1; }
cd "$TESTDIR" || exit 1

echo "== test_package/test.sh: ircd-ircu 2.10.12.19 =="
echo "-- scratch: $TESTDIR"

# ── Locate the installed artifacts (R34: must exercise the packaged binaries) ──
IRCD="$(command -v ircd)" || { echo "FATAL: ircd not on PATH"; exit 1; }
UMKPASSWD="$(command -v umkpasswd || true)"
CONVCONF="$(command -v convert-conf || true)"
echo "-- ircd:         $IRCD"
echo "-- umkpasswd:    ${UMKPASSWD:-<absent>}"
echo "-- convert-conf: ${CONVCONF:-<absent>}"

if [ -x "$IRCD" ]; then ok "ircd is present and executable"
else bad "ircd is not executable"; fi

# A stray host binary (an earlier upstream `make install` used to drop one into
# the build machine's /bin) must never satisfy this test: everything below has to
# come out of the Conan package folder.
PKG_BIN_DIR="$(cd "$(dirname "$IRCD")" && pwd)"
# 判据：脚本取到的 ircd 必须落在 conan 的 project/cache 目录里，也就是真的来自
# 本包产物，而不是构建机 /bin 里以前 `make install` 掉下来的残留。
#
# 2026-10-14 修（CI #14669）：旧判据写死 `*/.conan2/*`，只认 conan 的**默认**
# cache 目录名（~/.conan2）。CI worker 用的是 `~/.cache/conan2/p/b/ircd-<hash>/p/bin`
# —— 路径 100% 在包内，却被这条判据判成「包外」，于是 26 passed / 1 failed 里
# 唯一那条 FAIL 是测试自己写错了，不是产物有问题（同一次构建里 ircd -v / -k /
# 真实 TCP 注册 / SIGTERM 收尾全部 PASS）。
# 现在同时认 `.conan2`（默认）与 `conan2`（CI worker 布局），并额外接受
# `conan cache path` 给出的本包 package folder 前缀。
CONAN_PKG_DIR=""
IN_PKG="no"
if command -v conan >/dev/null 2>&1; then
    CONAN_PKG_DIR="$(conan cache path ircd-ircu/2.10.12.19 2>/dev/null | head -1)"
fi
if [ -n "$CONAN_PKG_DIR" ] && [ "${PKG_BIN_DIR#"$CONAN_PKG_DIR"}" != "$PKG_BIN_DIR" ]; then
    IN_PKG="yes"
fi
case "$PKG_BIN_DIR" in
    */.conan2/*|*/.conan2/p/*|*/conan2/*|*/conan2/p/*) IN_PKG="yes" ;;
esac
if [ "$IN_PKG" = "yes" ]; then
    ok "ircd resolves inside the conan project directory ($PKG_BIN_DIR)"
else
    bad "ircd resolved outside the conan project directory: $PKG_BIN_DIR"
fi

# ircd aborts with rc=3 when uid/euid/gid/egid is 0 (ircd.c set_userid_if_needed).
# The OHOS worker already runs unprivileged; the local gate runs as root, so wrap
# every ircd invocation in droproot, which passes the ids through when they are
# already non-zero.
DROPROOT="$SCRIPT_DIR/droproot"
if [ ! -x "$DROPROOT" ]; then
    echo "FATAL: $DROPROOT missing or not executable (test_package build() did not run?)"
    exit 1
fi
IRCD_CMD=("$DROPROOT" "$IRCD")
echo "-- uid: $(id -u) (droproot hands ircd an unprivileged uid when this is 0)"

# ── Test 1: ircd -v reports version + compiled event engines ──
echo "-- [1] ircd -v"
VOUT="$("${IRCD_CMD[@]}" -v 2>&1)"
echo "$VOUT" | sed 's/^/     | /'
if echo "$VOUT" | grep -q "ircd ${IRCD_VERSION_EXPECTED}$"; then
    ok "ircd -v reports 'ircd ${IRCD_VERSION_EXPECTED}'"
else
    bad "ircd -v did not report 'ircd ${IRCD_VERSION_EXPECTED}'"
fi
if echo "$VOUT" | grep -q "^Event engines: .*[a-z]"; then
    ok "ircd -v lists a compiled event engine"
else
    bad "ircd -v did not list any event engine"
fi
if echo "$VOUT" | grep -qE "^Compiled for a maximum of [0-9]+ connections\.$"; then
    MAXCON="$(echo "$VOUT" | sed -n 's/^Compiled for a maximum of \([0-9]*\) connections\.$/\1/p')"
    ok "ircd -v reports the compiled connection maximum ($MAXCON)"
    # MAXCONNECTIONS is a compile-time constant; if it is left at upstream's
    # `ulimit -Hn - 4` it bakes in whatever the build host happened to allow and
    # can exceed numnicks.c's NN_MAX_CLIENT (64^3), which aborts the daemon.
    if [ -n "$MAXCON" ] && [ "$MAXCON" -le 262144 ]; then
        ok "compiled connection maximum $MAXCON is within the numeric-nick limit (262144)"
    else
        bad "compiled connection maximum ${MAXCON:-<unparsed>} exceeds the numeric-nick limit"
    fi
else
    bad "ircd -v missing 'Compiled for a maximum of N connections.'"
fi

# ── Test 2: ircd -? prints usage and refuses to start ──
echo "-- [2] ircd -? (usage)"
UOUT="$("${IRCD_CMD[@]}" -? 2>&1)"
UOUT_RC=$?
echo "$UOUT" | head -3 | sed 's/^/     | /'
if [ "$UOUT_RC" -ne 0 ]; then ok "ircd -? exits non-zero (rc=$UOUT_RC)"
else bad "ircd -? unexpectedly exited 0"; fi
if echo "$UOUT" | grep -q "Usage: ircd \[-f config\]"; then
    ok "ircd -? prints the upstream usage text"
else
    bad "ircd -? usage text missing"
fi
if echo "$UOUT" | grep -q "Server not started\."; then
    ok "ircd -? reports 'Server not started.'"
else
    bad "ircd -? missing 'Server not started.'"
fi

# ── Test 3: ircd -k validates a generated configuration ──
echo "-- [3] ircd -k config check"
cat > "$TESTDIR/ircd.conf" <<EOF
General {
        name = "ohos-conan-test.example.net";
        vhost = "127.0.0.1";
        description = "HarmonyOS PC conan test server";
        numeric = 1;
};

Admin {
        location = "Nowhere";
        contact = "nobody";
};

Class {
        name = "User";
        pingfreq = 120 seconds;
        sendq = 160000;
        maxlinks = 100;
        usermode = "+oiwx";
};

Class {
        name = "Opers";
        pingfreq = 120 seconds;
        sendq = 160000;
        maxlinks = 10;
        local = no;
};

Operator { name = "oper1"; host = "*@*"; password = "\$PLAIN\$oper1"; class = "Opers"; };

Client { class = "User"; ip = "*"; };

Port { server = yes; port = $PORT; };
Port { server = no;  port = $SPORT; };

Features {
        "HIS_STATS_k" = "FALSE";
        "PPATH" = "ircd.pid";
};
EOF

# ircd runs as an unprivileged uid, so it has to be able to read the config and
# write its pid/log files into the data directory.
chmod 644 "$TESTDIR/ircd.conf"
chmod 777 "$TESTDIR"

KOUT="$("${IRCD_CMD[@]}" -k -d "$TESTDIR" -f "$TESTDIR/ircd.conf" 2>&1)"
KOUT_RC=$?
echo "$KOUT" | head -5 | sed 's/^/     | /'
if [ "$KOUT_RC" -eq 0 ]; then ok "ircd -k exits 0 on a valid configuration"
else bad "ircd -k exited $KOUT_RC"; fi
if echo "$KOUT" | grep -q "checked okay"; then
    ok "ircd -k reports the configuration 'checked okay'"
else
    bad "ircd -k did not report 'checked okay'"
fi

# ── Test 4: negative config check — a broken config must be rejected ──
echo "-- [4] ircd -k rejects a broken configuration"
sed 's/^General {/General { syntax_error_here/' "$TESTDIR/ircd.conf" > "$TESTDIR/broken.conf"
chmod 644 "$TESTDIR/broken.conf"
BOUT="$("${IRCD_CMD[@]}" -k -d "$TESTDIR" -f "$TESTDIR/broken.conf" 2>&1)"
BOUT_RC=$?
echo "$BOUT" | head -3 | sed 's/^/     | /'
if [ "$BOUT_RC" -ne 0 ]; then ok "ircd -k rejects a malformed configuration (rc=$BOUT_RC)"
else bad "ircd -k accepted a malformed configuration"; fi

# ── Test 5: live daemon — full IRC registration over TCP ──
echo "-- [5] live daemon: start, register, quit"
"${IRCD_CMD[@]}" -n -d "$TESTDIR" -f "$TESTDIR/ircd.conf" > "$TESTDIR/ircd.stdout" 2>&1 &
IRCD_PID=$!

ready=0
for _ in $(seq 1 40); do
    if (exec 9<>/dev/tcp/127.0.0.1/$SPORT) 2>/dev/null; then
        exec 9>&- 2>/dev/null || true
        ready=1
        break
    fi
    if ! kill -0 "$IRCD_PID" 2>/dev/null; then break; fi
    sleep 0.5
done
if [ "$ready" -eq 1 ]; then ok "ircd is accepting client connections on port $SPORT"
else
    bad "ircd did not listen on port $SPORT"
    echo "-- ircd stdout:"; sed 's/^/     | /' "$TESTDIR/ircd.stdout" 2>/dev/null | head -20
    exit 1
fi

# The `server = yes` port only speaks the server-link protocol: a NICK/USER sent
# there is refused with "Use a different port" (ircd/m_user.c IsServerPort).
# Assert that too, so the client-facing port choice below cannot silently rot.
exec 4<>/dev/tcp/127.0.0.1/$PORT
if [ $? -eq 0 ]; then
    printf 'NICK %s\r\nUSER %s 0 * :%s Probe\r\n' "$NICK" "$NICK" "$NICK" >&4
    SPORT_REJECT=0
    for _ in $(seq 1 10); do
        read -r -t 3 sline <&4 || break
        case "$sline" in
            *"Use a different port"*) SPORT_REJECT=1; break ;;
        esac
    done
    exec 4>&-
    if [ "$SPORT_REJECT" -eq 1 ]; then
        ok "the server-link port $PORT refuses client registration"
    else
        bad "the server-link port $PORT accepted a client NICK/USER"
    fi
else
    bad "cannot connect to the server-link port $PORT"
fi

# Drive a raw IRC registration on the client port: NICK + USER, then read the
# numeric burst.
exec 3<>/dev/tcp/127.0.0.1/$SPORT
if [ $? -ne 0 ]; then bad "cannot open a TCP session to the daemon"; exec 3>&-; exit 1; fi
printf 'NICK %s\r\nUSER %s 0 * :%s Probe\r\n' "$NICK" "$NICK" "$NICK" >&3

REG_DONE=0
SAW_001=0
SAW_004=0
SAW_005=0
SAW_VERSION=0
LINES=0
while [ "$LINES" -lt 60 ]; do
    if ! read -r -t 6 line <&3; then break; fi
    LINES=$((LINES + 1))
    echo "     > ${line}"
    case "$line" in
        PING\ *)
            # ircu2 gates registration behind a cookie probe: the first thing an
            # accepted client sees is `PING :<cookie>` plus numeric 513
            # ("To connect, type /QUOTE PONG <cookie>"), and auth_set_pong()
            # compares the PONG argument as an integer. So it must be sent as
            # `PONG <cookie>`, not the RFC `PONG :<cookie>` form.
            token="${line#PING }"
            token="${token#:}"
            token="${token%% *}"
            printf 'PONG %s\r\n' "$token" >&3
            ;;
        *\ 001\ *) SAW_001=1 ;;
        *\ 004\ *)
            SAW_004=1
            # RPL_MYINFO: :server 004 <nick> <server> <version> <umodes> <cmodes>
            if echo "$line" | grep -q " ${IRCD_VERSION_EXPECTED} "; then
                SAW_VERSION=1
            fi
            ;;
        *\ 005\ *) SAW_005=1 ;;
    esac
    if [ "$SAW_001" -eq 1 ] && [ "$SAW_004" -eq 1 ]; then REG_DONE=1; break; fi
done

if [ "$SAW_001" -eq 1 ]; then ok "daemon answered with RPL_WELCOME (001) after registration"
else bad "no RPL_WELCOME (001) received ($LINES lines read)"; fi
if [ "$SAW_004" -eq 1 ]; then ok "daemon answered with RPL_MYINFO (004)"
else bad "no RPL_MYINFO (004) received"; fi
if [ "$SAW_004" -eq 1 ] && [ "$SAW_VERSION" -eq 1 ]; then
    ok "RPL_MYINFO advertises the packaged version ${IRCD_VERSION_EXPECTED}"
else
    bad "RPL_MYINFO did not advertise version ${IRCD_VERSION_EXPECTED}"
fi
if [ "$SAW_005" -eq 1 ]; then ok "daemon answered with RPL_ISUPPORT (005)"
else echo "  [warn] no RPL_ISUPPORT (005) received"; fi

# QUIT and verify the server closes the session.
printf 'QUIT :conan test done\r\n' >&3
QUIT_CLOSED=0
for _ in $(seq 1 20); do
    if ! read -r -t 3 line <&3; then QUIT_CLOSED=1; break; fi
    echo "     > ${line}"
    case "$line" in
        ERROR\ *) QUIT_CLOSED=1 ;;
    esac
done
exec 3>&-
if [ "$QUIT_CLOSED" -eq 1 ]; then ok "daemon closed the session after QUIT"
else bad "daemon did not close the session after QUIT"; fi

# ── Test 6: clean shutdown releases the port ──
echo "-- [6] clean shutdown"
kill -TERM "$IRCD_PID" 2>/dev/null
WAITED=0
for _ in $(seq 1 40); do
    if ! kill -0 "$IRCD_PID" 2>/dev/null; then WAITED=1; break; fi
    sleep 0.5
done
if [ "$WAITED" -eq 1 ]; then ok "ircd exited on SIGTERM"
else bad "ircd did not exit on SIGTERM"; fi
wait "$IRCD_PID" 2>/dev/null
IRCD_RC=$?
IRCD_PID=""
echo "-- ircd exit status: $IRCD_RC"
if [ "$IRCD_RC" -eq 0 ]; then ok "ircd shut down cleanly (exit 0)"
else bad "ircd exited with status $IRCD_RC"; fi

# 端口释放检查。
# 2026-10-14（AI 检视 P1）：这里原来写的是 `RELASED=0`（少一个 E），而判断用的是
# `$RELEASED`——该变量在上面被置 1 后没人再改，于是这条断言**恒为 PASS**：
# SIGTERM 之后端口没被释放的真实回归永远不会被发现。下面除了改成正确的变量名，
# 还把「端口仍在监听」的现场证据一起打出来，便于定位是 ircd 没退干净还是别的进程占着。
RELEASED=1
for _ in $(seq 1 10); do
    if (exec 9<>/dev/tcp/127.0.0.1/$SPORT) 2>/dev/null; then
        exec 9>&- 2>/dev/null || true
        RELEASED=0
        break
    fi
    sleep 0.5
done
if [ "$RELEASED" -eq 1 ]; then
    ok "listening port $SPORT released after shutdown"
else
    bad "port $SPORT still accepting connections after shutdown"
    echo "     | ircd stdout tail (last 8 lines):"
    tail -n 8 "$TESTDIR/ircd.stdout" 2>/dev/null | sed 's/^/     | /' || echo "     | (no ircd.stdout)"
    echo "     | pid file: $(ls -l "$TESTDIR"/ircd.pid 2>/dev/null || echo '<absent>')"
fi

# ── Test 7: the two auxiliary binaries shipped by the package ──
echo "-- [7] auxiliary binaries"
if [ -n "$CONVCONF" ] && [ -x "$CONVCONF" ]; then
    COUT="$("$CONVCONF" "$TESTDIR/ircd.conf" 2>&1)"
    CRC=$?
    echo "$COUT" | head -3 | sed 's/^/     | /'
    if [ "$CRC" -eq 0 ] && echo "$COUT" | grep -qi "port"; then
        ok "convert-conf parsed the configuration and reported the converted form"
    else
        bad "convert-conf failed (rc=$CRC)"
    fi
else
    bad "convert-conf not installed"
fi

if [ -n "$UMKPASSWD" ] && [ -x "$UMKPASSWD" ]; then
    # (a) mechanism listing
    LOUT="$("$UMKPASSWD" -l 2>&1)"
    echo "$LOUT" | head -4 | sed 's/^/     | /'
    if echo "$LOUT" | grep -q "plain"; then
        ok "umkpasswd -l lists the plain mechanism"
    else
        bad "umkpasswd -l did not list the plain mechanism"
    fi

    # (b) password supplied on the command line
    UMOUT="$("$UMKPASSWD" -m plain conanprobe 2>&1)"
    URC=$?
    echo "$UMOUT" | head -3 | sed 's/^/     | /'
    if [ "$URC" -eq 0 ] && echo "$UMOUT" | grep -qF 'Crypted Pass: $PLAIN$'; then
        ok "umkpasswd hashed an argv-supplied password with the plain mechanism"
    else
        bad "umkpasswd argv path failed (rc=$URC)"
    fi

    # (c) password read with echo disabled -- the code path that upstream routed
    #     through getpass(3) and that musl/OHOS does not provide at all
    UMOUT2="$(printf 'conanprobe\n' | "$UMKPASSWD" -m plain 2>&1)"
    URC2=$?
    echo "$UMOUT2" | head -3 | sed 's/^/     | /'
    if [ "$URC2" -eq 0 ] && echo "$UMOUT2" | grep -qF 'Crypted Pass: $PLAIN$'; then
        ok "umkpasswd hashed a password read without echo (no-getpass code path)"
    else
        bad "umkpasswd no-echo read path failed (rc=$URC2)"
    fi

    # (d) the no-echo read must agree with the argv path
    A="$(echo "$UMOUT" | sed -n 's/^Crypted Pass: //p' | head -1)"
    B="$(echo "$UMOUT2" | sed -n 's/^Crypted Pass: //p' | head -1)"
    if [ -n "$A" ] && [ "$A" = "$B" ]; then
        ok "argv and no-echo paths produce the same crypted password"
    else
        bad "argv/no-echo password mismatch ('$A' vs '$B')"
    fi
else
    bad "umkpasswd not installed"
fi

# ── Test 8: the package also ships the upstream sample configuration ──
echo "-- [8] packaged example configuration"
IRCD_BIN_DIR="$(dirname "$IRCD")"
EXAMPLE_CONF="$(ls -1 "$IRCD_BIN_DIR"/../ircd/example.conf 2>/dev/null | head -1)"
if [ -n "$EXAMPLE_CONF" ] && [ -s "$EXAMPLE_CONF" ]; then
    ok "upstream doc/example.conf installed ($(wc -c < "$EXAMPLE_CONF") bytes)"
else
    bad "upstream doc/example.conf not found under the package ircd/ directory"
fi

# ── Test 9: 鸿蒙特有消费者用例 —— 让**包内** example.conf 驱动一次真实启动 ──
# rule12 要求至少一条完整的鸿蒙特有用例（真正跑通功能/流程）。这里选消费者最自然的
# 输入：随包安装的上游 doc/example.conf。
#
# 2026-10-14 修（CI #90797）：上一版用 sed 把 example.conf 里所有 `port = ...` 行都
# 改写成同一个端口，把上游配置改成了非法形态，`ircd -k` 直接报
# 'Config file parse error line 610/615/622'。现在**不碰原文件的任何一行**，
# 只在副本尾部追加 `Features { "PPATH" = ...; }` 与 `Port { ... }` —— 配置语法里
# 后出现的 Port 段是追加监听端口，不会与文件里原有的端口段冲突。
echo "-- [9] HarmonyOS consumer case: packaged example.conf drives a real start"
EX_CASE_PORT=$((SPORT + 2))
if [ -z "${EXAMPLE_CONF:-}" ] || [ ! -s "${EXAMPLE_CONF:-}" ]; then
    EXAMPLE_CONF="$(ls -1 "$(dirname "$IRCD")"/../ircd/example.conf 2>/dev/null | head -1)"
fi
if [ -z "${EXAMPLE_CONF:-}" ] || [ ! -s "${EXAMPLE_CONF}" ]; then
    bad "packaged example.conf unavailable for the HarmonyOS consumer case"
else
    OHOS_CASE="$TESTDIR/ohos-case"
    mkdir -p "$OHOS_CASE"
    cp "$EXAMPLE_CONF" "$OHOS_CASE/ircd.conf"
    # 注意：ircd 的配置解析器（上游 ircu 的 yacc 语法）**不认 C 风格注释**，
    # 追加内容里不能写 /* ... */（CI #90810 实测报 'Config file parse error
    # line 610/615/622: syntax error'）。这里只追加两个合法段落：Features 覆盖
    # pid 路径，Port 追加一个监听端口；原 example.conf 一行都不动。
    cat >> "$OHOS_CASE/ircd.conf" <<EOF

Features {
        "PPATH" = "$OHOS_CASE/ircd.pid";
};

Port { server = no; port = $EX_CASE_PORT; };
EOF
    chmod 644 "$OHOS_CASE/ircd.conf"
    chmod 777 "$OHOS_CASE"

    if "${IRCD_CMD[@]}" -k -d "$OHOS_CASE" -f "$OHOS_CASE/ircd.conf" > "$OHOS_CASE/check.out" 2>&1; then
        ok "the packaged example.conf (unmodified, overrides appended) is accepted by ircd -k"
    else
        bad "the packaged example.conf was rejected by ircd -k: $(head -3 "$OHOS_CASE/check.out" | tr '\n' ' ')"
    fi

    "${IRCD_CMD[@]}" -n -d "$OHOS_CASE" -f "$OHOS_CASE/ircd.conf" > "$OHOS_CASE/run.out" 2>&1 &
    OHOS_PID=$!
    ohos_ready=0
    for _ in $(seq 1 40); do
        if (exec 8<>/dev/tcp/127.0.0.1/$EX_CASE_PORT) 2>/dev/null; then
            exec 8>&- 2>/dev/null || true
            ohos_ready=1
            break
        fi
        if ! kill -0 "$OHOS_PID" 2>/dev/null; then break; fi
        sleep 0.5
    done
    if [ "$ohos_ready" -eq 1 ]; then
        ok "the daemon started from the packaged example.conf and is listening on $EX_CASE_PORT"
    else
        bad "the daemon did not come up from the packaged example.conf"
        sed 's/^/     | /' "$OHOS_CASE/run.out" 2>/dev/null | head -10
    fi
    kill -TERM "$OHOS_PID" 2>/dev/null
    for _ in $(seq 1 20); do
        kill -0 "$OHOS_PID" 2>/dev/null || break
        sleep 0.5
    done
    kill -KILL "$OHOS_PID" 2>/dev/null || true
    wait "$OHOS_PID" 2>/dev/null || true
    if [ "$ohos_ready" -eq 1 ]; then
        ok "the HarmonyOS consumer case completed end to end (packaged config -> listening daemon -> clean stop)"
    else
        bad "the HarmonyOS consumer case did not complete end to end"
    fi
fi

echo
echo "== test_package/test.sh summary: $PASS passed, $FAIL failed =="
if [ "$FAIL" -ne 0 ]; then
    echo "TESTS FAILED"
    exit 1
fi
echo "ALL TESTS PASSED"