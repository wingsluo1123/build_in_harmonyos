#!/bin/sh
# sinfo 0.0.48 consumer test — real binary invocations with assertions.
#
# Usage: test_sinfo.sh <sinfo-binary> <sinfod-binary>
#
# 覆盖：
#   1) sinfo/sinfod 版本横幅（-V：rc=0 且含 0.0.48）
#   2) sinfo/sinfod 帮助文本（-?/-h：rc=1 且含关键选项说明）
#   3) 端到端：sinfod 前台守护（-F -q -b 127.0.0.1，广播收窄到环回，不产生
#      对 255.255.255.255 的真实广播）启动存活；sinfo 客户端经 UDP/TCP
#      （SINFO_REQUEST_PORT=60002）直连查询，-H（主机名）/ -L（负载）输出非空
#   4) 守护进程响应 SIGTERM 干净退出
# 交互式 ncurses 界面不测（需要真实终端）；-H/-L 走纯文本路径，不初始化 curses。
set -u

SINFO="$1"
SINFOD="$2"
pass=0
fail=0

ok() { pass=$((pass+1)); echo "ok - $1"; }
no() { fail=$((fail+1)); echo "NOT OK - $1"; }

# run_bin <binary> <timeout-sec> <args...> → 设置 out/rc（stdout+stderr 合并）
run_bin() {
  bin="$1"; tmo="$2"; shift 2
  out=$(timeout "$tmo" "$bin" "$@" </dev/null 2>&1)
  rc=$?
}

# assert_out_rc <expected-rc> <substring> <description> <binary> <args...>
assert_out_rc() {
  expected="$1"; needle="$2"; desc="$3"; bin="$4"; shift 4
  run_bin "$bin" 10 "$@"
  if [ "$rc" -ne "$expected" ]; then
    no "$desc (expected rc=$expected, got rc=$rc)"
    echo "  output: $out"
  elif echo "$out" | grep -q -- "$needle"; then
    ok "$desc"
  else
    no "$desc (missing '$needle')"
    echo "  output: $out"
  fi
}

# assert_nonempty_rc <expected-rc> <description> <binary> <args...>
# 断言 rc 且 stdout+stderr 中存在至少一个非空白字符
assert_nonempty_rc() {
  expected="$1"; desc="$2"; bin="$3"; shift 3
  run_bin "$bin" 30 "$@"
  if [ "$rc" -ne "$expected" ]; then
    no "$desc (expected rc=$expected, got rc=$rc)"
    echo "  output: $out"
  elif echo "$out" | grep -q "[^[:space:]]"; then
    ok "$desc"
  else
    no "$desc (output is empty)"
  fi
}

echo "# sinfo 0.0.48 consumer test"
echo "# sinfo:  $SINFO"
echo "# sinfod: $SINFOD"

# --- 1. 版本横幅（-V → rc=0，含打包版本） ---------------------------------
assert_out_rc 0 "0.0.48" "sinfo -V prints packaged version (rc=0)" "$SINFO" -V
assert_out_rc 0 "0.0.48" "sinfod -V prints packaged version (rc=0)" "$SINFOD" -V

# --- 2. 帮助文本（-?/-h/--help → rc=1） ------------------------------------
assert_out_rc 1 "hostsmode" "sinfo -? prints help and exits rc=1" "$SINFO" "-?"
assert_out_rc 1 "foreground" "sinfod -h prints help and exits rc=1" "$SINFOD" -h

# --- 3. 端到端：前台守护 + 客户端 UDP/TCP 直连查询 --------------------------
# 广播地址收窄到环回：守护进程的 UDP 广播（SINFO_BROADCAST_PORT=60003）只发
# 127.0.0.1，不触碰真实网络；查询服务器仍绑定 SINFO_REQUEST_PORT=60002。
"$SINFOD" -F -q -b 127.0.0.1 >sinfod-test.log 2>&1 &
DPID=$!

alive=0
i=0
while [ "$i" -lt 5 ]; do
  if kill -0 "$DPID" 2>/dev/null; then alive=1; break; fi
  sleep 1
  i=$((i+1))
done
if [ "$alive" -eq 1 ]; then
  ok "sinfod -F starts in foreground and stays alive"
else
  no "sinfod -F exited within 5s (see sinfod-test.log)"
  [ -f sinfod-test.log ] && sed -n "1,20p" sinfod-test.log
fi

if [ "$alive" -eq 1 ]; then
  # 留给守护进程完成 UDP/TCP 60002 绑定（io_service 构造 + endpoint bind）
  sleep 2
  # 客户端默认 host=127.0.0.1、协议 UDP；-q 抑制启动横幅（stderr）
  assert_nonempty_rc 0 "sinfo -q -H lists the daemon host (UDP)" "$SINFO" -q -H
  assert_nonempty_rc 0 "sinfo -q -L lists host load (UDP)" "$SINFO" -q -L
  assert_nonempty_rc 0 "sinfo -q --tcp -H lists the daemon host (TCP)" "$SINFO" -q --tcp -H
fi

# --- 4. 守护进程干净退出 ------------------------------------------------------
if [ "$alive" -eq 1 ]; then
  kill -TERM "$DPID" 2>/dev/null
  i=0
  while [ "$i" -lt 10 ]; do
    if ! kill -0 "$DPID" 2>/dev/null; then break; fi
    sleep 1
    i=$((i+1))
  done
  if kill -0 "$DPID" 2>/dev/null; then
    kill -KILL "$DPID" 2>/dev/null
    no "sinfod ignored SIGTERM for 10s (SIGKILLed)"
  else
    ok "sinfod exits on SIGTERM"
  fi
  wait "$DPID" 2>/dev/null
fi

rm -f sinfod-test.log
echo "1..$((pass+fail))"
echo "# passed: $pass"
echo "# failed: $fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
