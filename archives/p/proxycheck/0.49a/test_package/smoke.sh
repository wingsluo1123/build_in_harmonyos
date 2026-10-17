#!/usr/bin/env bash
# proxycheck 0.49a 消费者测试（7 条断言，离线确定性：只用 127.0.0.1 回环与 .invalid 保留域）
set -u
pass=0
fail=0
ok() { pass=$((pass+1)); echo "ok   $1"; }
bad() { fail=$((fail+1)); echo "FAIL $1"; }

PC="$(command -v proxycheck || true)"
PL="$(command -v proxylogger || true)"
if [ -z "$PC" ]; then echo "proxycheck not on PATH"; exit 1; fi
if [ -z "$PL" ]; then echo "proxylogger not on PATH"; exit 1; fi
echo "proxycheck=$PC"
echo "proxylogger=$PL"

# A1 -h 可用且版本宏正确代入
out="$("$PC" -h 2>&1)"; rc=$?
if [ $rc -eq 0 ] && printf '%s' "$out" | grep -q "Open proxy checker version 0.49a 2004-05-29"; then
  ok A1
else
  bad "A1 rc=$rc"
fi

# A2 帮助里的协议表
if printf '%s' "$out" | grep -q "s5 (socks5" && printf '%s' "$out" | grep -q "fu (ftp-user"; then
  ok A2
else
  bad A2
fi

# A3 无参数 -> 用法错误 rc=1
out="$("$PC" 2>&1)"; rc=$?
if [ $rc -eq 1 ] && printf '%s' "$out" | grep -q "no host(s) to check specified"; then
  ok A3
else
  bad "A3 rc=$rc"
fi

# A4 真实探测回环关闭端口：走完 socket + ev_* 事件循环，判定不是开放代理 -> rc=0 且无输出
out="$("$PC" -t 2 -d 127.0.0.1:9 -c chat:foo:bar 127.0.0.1:1 2>&1)"; rc=$?
if [ $rc -eq 0 ] && [ -z "$out" ]; then
  ok A4
else
  bad "A4 rc=$rc out=[$out]"
fi

# A5 保留域 .invalid 解析失败 -> rc=1 且给出诊断
out="$("$PC" -t 2 -d 127.0.0.1:9 -c chat:foo:bar nosuch.invalid 2>&1)"; rc=$?
if [ $rc -eq 1 ] && printf '%s' "$out" | grep -q "invalid IP address"; then
  ok A5
else
  bad "A5 rc=$rc out=[$out]"
fi

# A6 proxylogger 是 inetd helper：stdin 非 socket 时 getpeername 失败 -> rc=1
printf 'CONNECT example.com:80 HTTP/1.0\r\n\r\n' | "$PL" -n >/dev/null 2>&1; rc=$?
if [ $rc -eq 1 ]; then
  ok A6
else
  bad "A6 rc=$rc"
fi

# A7 手册页 staging
man="${PROXYCHECK_MAN:-}"
if [ -n "$man" ] && grep -q "proxycheck" "$man/man1/proxycheck.1" 2>/dev/null \
   && grep -qi "event" "$man/man3/event.3" 2>/dev/null; then
  ok A7
else
  bad "A7 man=[$man]"
fi

echo "SUMMARY pass=$pass fail=$fail"
[ $fail -eq 0 ] || exit 1
exit 0
