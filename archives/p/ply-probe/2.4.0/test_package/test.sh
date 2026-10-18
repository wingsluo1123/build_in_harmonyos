#!/usr/bin/env bash
# test_package/test.sh — ply-probe 2.4.0 鸿蒙适配测试
#
# 上游测试（test/ 的 QEMU 多架构套件、src/ply/self-test.sh）都要求 Linux 内核追踪后端，
# 在 OHOS 上全部不可运行（实测证据见 archives/p/ply-probe/2.4.0/reports/probe-output.log）：
#   bpf()                     → SIGSYS（信号 31，进程被直接终止，rc=159）
#   perf_event_open()         → EACCES
#   /proc/kallsyms            → 地址被 kptr_restrict 抹零，kallsyms cache 创建失败
#   /sys/kernel/debug/tracing → 目录存在但无后端（仅目录表象，tracepoint 解析失败）
# 故本测试覆盖**产物真实可执行性**与**如实记录的平台能力边界**：
#   1) 版本输出（OHOS 上唯一完整可用的功能路径）
#   2) 用法输出（真实二进制执行）
#   3) 负例：非法脚本必须被解析器拒绝（证明解析器真实工作，非空壳产物）
#   4) kprobe 脚本编译路径在 kallsyms 受限下确定性失败，且失败点不在 bpf() 加载
# 说明：有意不执行 ply -S / ply -T —— 二者会调用 bpf() 被 SIGSYS 杀死并可能落 core 文件，
#       在 CI 中属环境噪声；该平台限制由 reports/probe-output.log 实证留档。
# 有意不启用 -e：第 [4/4] 项需捕获 ply 的非零退出码并做断言（-e 会让脚本提前退出），
# 失败判定统一走 fails 计数器 + 末尾 exit，等价于安全模式。
set -uo pipefail

WORK=$(mktemp -d "${TMPDIR:-$HOME}/ply-test.XXXXXX") || exit 1
trap 'rm -rf "$WORK"' EXIT
fails=0

echo "[1/4] ply -v : 版本信息"
if out=$(ply -v 2>&1) && printf '%s' "$out" | grep -q '2\.4\.0'; then
  echo "PASS: $(printf '%s' "$out" | head -1)"
else
  echo "FAIL: ply -v 未输出版本号 2.4.0（输出: $out）"
  fails=$((fails + 1))
fi

echo "[2/4] ply -h : 用法输出（真实二进制执行）"
if out=$(ply -h 2>&1) && printf '%s' "$out" | grep -q 'Dynamic tracing utility'; then
  echo "PASS: ply -h 输出用法信息"
else
  echo "FAIL: ply -h 输出异常（输出: $out）"
  fails=$((fails + 1))
fi

echo "[3/4] 负例：非法脚本必须被解析器拒绝"
if out=$(ply -e 'garbage@@ nope' 2>&1); then
  echo "FAIL: 非法脚本返回 0（解析器未生效，产物疑似空壳）"
  fails=$((fails + 1))
elif printf '%s' "$out" | grep -q 'syntax error'; then
  echo "PASS: 非法脚本被拒（$(printf '%s' "$out" | head -1 | cut -c1-60)）"
else
  echo "FAIL: 非法脚本失败但无 syntax error（输出: $out）"
  fails=$((fails + 1))
fi

echo "[4/4] kprobe 编译路径：kallsyms 受限 → 确定性非 0，且未下沉到 bpf() 加载"
printf 'kprobe:do_sys_open { printf("ply-probe\\n"); }\n' > "$WORK/probe.ply"
ply -e "$WORK/probe.ply" > "$WORK/e.out" 2>&1
rc=$?
if [ "$rc" -eq 159 ]; then
  echo "FAIL: ply -e 走到 bpf() 加载被 SIGSYS 杀死 —— 平台边界变化，需复核知识条目 E545"
  fails=$((fails + 1))
elif [ "$rc" -ne 0 ]; then
  echo "PASS: ply -e 返回 $rc（编译期因 kallsyms 受限失败，未触发 bpf()）"
else
  echo "FAIL: ply -e 返回 0 —— 出现预期外可用路径，需更新知识条目 E545"
  fails=$((fails + 1))
fi

if [ "$fails" -eq 0 ]; then
  echo "[test] 4/4 通过：产物可执行；内核追踪能力按 E545 声明为平台不支持"
  exit 0
fi
echo "[test] $fails 项失败"
exit 1
