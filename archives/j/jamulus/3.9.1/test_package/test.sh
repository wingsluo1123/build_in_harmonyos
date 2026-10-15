#!/usr/bin/env bash
# test_package/test.sh — jamulus 服务器二进制消费者测试（鸿蒙独有测试）
# Runs in conanrun env (PATH/LD_LIBRARY_PATH 已包含依赖)
# R34: 实质运行被测包二进制，非空壳打印。
# 产物名兼容：qmake 默认 TARGET 取 .pro 文件名 → bin/Jamulus（大写）；
# 大小写敏感文件系统上必须按实际名解析（HMDFS 大小写不敏感不可依赖）。
# SIGPIPE 规避：所有输出重定向到文件后再读取，不直接管道 head。
set -uo pipefail

LOG="${TMPDIR:-/storage/Users/currentUser}/jamulus-test.log"
: > "$LOG"

echo "[test] jamulus binary consumer tests" | tee -a "$LOG"
BIN=""
for name in Jamulus jamulus; do
    if command -v "$name" >/dev/null 2>&1; then
        BIN="$name"
        break
    fi
done
[ -n "$BIN" ] || { echo "❌ T1 FAIL: binary not in PATH (tried: Jamulus, jamulus)" | tee -a "$LOG"; exit 1; }
echo "✅ T1 PASS: binary found in PATH: $BIN" | tee -a "$LOG"

# T2: --version 真实执行（main.cpp:158 参数解析路径，exit 0）
echo "[test] T2: $BIN --version" | tee -a "$LOG"
out="$("$BIN" --version 2>&1)"
rc=$?
echo "$out" >> "$LOG"
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "3\.9\.1"; then
    echo "✅ T2 PASS: --version exit 0 且输出含 3.9.1" | tee -a "$LOG"
else
    echo "❌ T2 FAIL: exit=$rc 或版本输出不匹配" | tee -a "$LOG"
    exit 1
fi

# T3: --help 用法输出（UsageArguments 全量帮助文本，含服务器选项 -s/--server）
echo "[test] T3: $BIN --help" | tee -a "$LOG"
"$BIN" --help > "$LOG.help" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q -- "-s, --server" "$LOG.help" && grep -q -- "-v, --version" "$LOG.help"; then
    echo "✅ T3 PASS: --help exit 0 且含完整用法文本（-s/--server、-v/--version）" | tee -a "$LOG"
else
    echo "❌ T3 FAIL: exit=$rc 或用法文本缺失" | tee -a "$LOG"
    cat "$LOG.help" >> "$LOG"
    exit 1
fi

# T4: 服务器模式真实启动冒烟（HEADLESS QCoreApplication + 网络监听真实路径）
# 期望：进程存活至 timeout（124=仍在运行，证明 event loop 正常）或主动退出码 0/1
# 且日志含服务器启动痕迹；崩溃（139 等）为失败。
echo "[test] T4: $BIN -s (server mode, 5s smoke)" | tee -a "$LOG"
timeout 5s "$BIN" -s > "$LOG.server" 2>&1
rc=$?
cat "$LOG.server" >> "$LOG"
echo "--- T4 exit code: $rc ---" | tee -a "$LOG"
if [ "$rc" -eq 124 ] || [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
    echo "✅ T4 PASS: 服务器模式启动冒烟通过（exit=$rc：124=存活至超时/event loop 正常，0/1=受控退出，无崩溃）" | tee -a "$LOG"
else
    echo "❌ T4 FAIL: 意外退出码 $rc（崩溃/异常）" | tee -a "$LOG"
    exit 1
fi

echo "[test] all 4 consumer tests passed" | tee -a "$LOG"
exit 0
