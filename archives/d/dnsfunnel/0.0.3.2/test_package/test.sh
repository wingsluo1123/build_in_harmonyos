#!/usr/bin/env bash
# test_package/test.sh — dnsfunnel 消费者测试（真实安装的二进制）
# 在 conanrun 环境中执行（PATH 含本包 bin/）。任何一条断言失败即非零退出（R34 L1e）。
set -euo pipefail

DAEMON_PID=""
cleanup() {
  local rc=$?
  if [ -n "$DAEMON_PID" ]; then
    kill -TERM "$DAEMON_PID" 2>/dev/null || true
    sleep 1
    kill -9 "$DAEMON_PID" 2>/dev/null || true
  fi
  rm -f resolv.conf caches caches2 ready.txt daemon.err
  exit $rc
}
trap cleanup EXIT

fail() { echo "[fail] $1" >&2 ; exit 1 ; }

command -v dnsfunneld         >/dev/null 2>&1 || fail "dnsfunneld 不在 PATH 中"
command -v dnsfunnel-translate >/dev/null 2>&1 || fail "dnsfunnel-translate 不在 PATH 中"

# --- 1. dnsfunneld：非法选项 → 上游 usage 文本，退出码 100 ------------------
set +e
out=$(dnsfunneld -Z 2>&1)
rc=$?
set -e
[ "$rc" -eq 100 ] || fail "dnsfunneld -Z 退出码=$rc，期望 100"
case "$out" in
  *"usage: dnsfunneld"*) ;;
  *) fail "dnsfunneld 未打印 usage: $out" ;;
esac
echo "[ok] dnsfunneld usage 路径（退出码 100）"

# --- 2. dnsfunnel-translate：解析 resolv.conf → 生成缓存列表 -----------------
printf 'nameserver 9.9.9.9\nnameserver 8.8.8.8\nnameserver 1.1.1.1\nnameserver 127.0.0.1\n' > resolv.conf
rm -f caches
dnsfunnel-translate -i resolv.conf -o caches
[ -f caches ] || fail "caches 未生成"
got=$(tr '\n' ' ' < caches)
# 127.0.0.1 是默认被忽略的地址，必须只留下三个公网解析器
[ "$got" = "9.9.9.9 8.8.8.8 1.1.1.1 " ] || fail "caches=[$got]，期望 [9.9.9.9 8.8.8.8 1.1.1.1 ]"
echo "[ok] dnsfunnel-translate 生成缓存列表 caches（回环地址已按默认规则剔除）"

# --- 3. dnsfunnel-translate：输入缺失 → 退出码 111 --------------------------
set +e
err=$(dnsfunnel-translate -i ./no-such-resolv.conf -o caches2.txt 2>&1)
rc=$?
set -e
[ "$rc" -eq 111 ] || fail "缺文件退出码=$rc，期望 111"
case "$err" in
  *"no-such-resolv.conf"*) ;;
  *) fail "缺文件错误文本缺失: $err" ;;
esac
echo "[ok] dnsfunnel-translate 缺输入路径（退出码 111）"

# --- 4. 端到端：dnsfunneld 监听并真实转发一次 DNS 查询 ----------------------
PORT=$(( 20000 + ($$ % 20000) ))
dnsfunneld -i 127.0.0.1 -p "$PORT" -R "" -t 20000 -1 > ready.txt 2> daemon.err &
DAEMON_PID=$!

# -1 就绪信号：绑定成功并初始化完成后向上游 stdout 写一个换行
ready=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if [ -s ready.txt ]; then ready=1; break; fi
  if ! kill -0 "$DAEMON_PID" 2>/dev/null; then
    fail "dnsfunneld 启动即退出: $(cat daemon.err 2>/dev/null)"
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || fail "dnsfunneld 未在 10s 内发出就绪信号"
echo "[ok] dnsfunneld 绑定 127.0.0.1:$PORT 并发出就绪信号"

# 外网 DNS 探针：决定端到端转发断言是否可执行（不可达时显式跳过并说明原因）
if dig +noedns @9.9.9.9 example.com A +time=4 +tries=1 >/dev/null 2>&1; then
  set +e
  ans_out=$(dig @"127.0.0.1" -p "$PORT" +noedns +time=8 +tries=2 example.com A 2>&1)
  dig_rc=$?
  set -e
  [ "$dig_rc" -eq 0 ] || fail "经 dnsfunneld 的转发查询失败(退出码 $dig_rc): $ans_out"
  printf '%s\n' "$ans_out" | grep -q "status: NOERROR" || fail "转发响应状态非 NOERROR: $ans_out"
  printf '%s\n' "$ans_out" | grep -q "ANSWER SECTION" || fail "转发响应无 ANSWER SECTION: $ans_out"
  n=$(printf '%s\n' "$ans_out" | sed -n '/ANSWER SECTION/,$p' | grep -c "IN" || true)
  [ "$n" -ge 1 ] || fail "转发响应 A 记录数为 0: $ans_out"
  echo "[ok] 端到端转发：example.com 经 127.0.0.1:$PORT 返回 $n 条 A 记录"
else
  echo "[skip] 外网 DNS 探针不可达，端到端转发断言未执行（监听/就绪断言已通过）"
fi

echo "dnsfunnel 消费者测试通过：5 条断言"
exit 0
