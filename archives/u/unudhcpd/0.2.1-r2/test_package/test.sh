#!/bin/sh
# test_package 消费者验证 — unudhcpd 0.2.1-r2
#
# 验证「已安装产物」可被真实消费者使用：执行 bin/unudhcpd 并断言可观测行为。
# 三条检查覆盖：版本输出路径 / 参数校验（usage）路径 / 服务启动路径
# （getopt 解析 -i/-s/-c/-p 后进入 dhcp_server_start）。
#
# 不做真实收包：绑定接口需 CAP_NET_RAW 权限，CI 中以超时终止常驻进程。
set -u

fails=0
pass() { echo "PASS $1: $2"; }
fail() { echo "FAIL $1: $2"; fails=$((fails + 1)); }

echo "--- unudhcpd 0.2.1-r2 consumer verification ---"

# 1) -v：打印版本并以 0 退出
out=$(unudhcpd -v 2>&1)
rc=$?
if [ "$rc" -eq 0 ] && echo "$out" | grep -q '^unudhcpd '; then
	pass 1 "-v -> $out"
else
	fail 1 "-v rc=$rc out=[$out]"
fi

# 2) 无参数：给出用法并以非 0 退出（参数校验路径）
out=$(unudhcpd 2>&1)
rc=$?
if [ "$rc" -ne 0 ] && echo "$out" | grep -q 'Usage:'; then
	pass 2 "no-arg -> usage, rc=$rc"
else
	fail 2 "no-arg rc=$rc out=[$(echo "$out" | head -1)]"
fi

# 3) 服务启动路径：后台启动 3 秒后终止，断言打印出解析后的真实参数
#    且期间未异常退出（崩溃/立即退出）
#    R10: 临时文件写 $TMPDIR（OHOS /tmp 只读），不污染 recipe 目录
outdir="${TMPDIR:-$HOME/tmp}"
mkdir -p "$outdir" 2>/dev/null
outfile="$outdir/unudhcpd_run_$$.log"
rm -f "$outfile"
unudhcpd -i lo -s 10.9.8.1 -c 10.9.8.2 -p 16767 > "$outfile" 2>&1 &
pid=$!
sleep 3
if kill -0 "$pid" 2>/dev/null; then
	alive=yes
	kill "$pid" 2>/dev/null
	wait "$pid" 2>/dev/null
else
	alive=no
fi

if [ "$alive" = "yes" ] \
	&& grep -q 'Server IP addr: 10.9.8.1:16767' "$outfile" \
	&& grep -q 'client IP addr: 10.9.8.2' "$outfile" \
	&& grep -q 'interface: lo' "$outfile"; then
	pass 3 "server start path: $(head -1 "$outfile")"
else
	fail 3 "alive=$alive log=[$(head -2 "$outfile" 2>/dev/null)]"
fi

echo "unudhcpd 0.2.1-r2: $((3 - fails))/3 checks PASS"
rm -f "$outfile"
[ "$fails" -eq 0 ] || exit 1
exit 0
