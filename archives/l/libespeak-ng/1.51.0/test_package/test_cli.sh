#!/bin/sh
# test_cli.sh — libespeak-ng 1.51.0 CLI 端到端消费者用例（鸿蒙特有测试）
#
# 真实调用打包产物中的 espeak-ng 命令行工具，走完整 TTS 流程：
#   1. espeak-ng --version 验证工具可执行、数据路径正确；
#   2. espeak-ng "文本" -w out.wav 真实合成语音到 WAV 文件；
#   3. 校验 WAV 文件为合法 RIFF/WAVE（魔数）+ 非空（> 100 字节）。
#
# 与 test_libespeak-ng.c（库 API 级）互补：本用例验证 CLI 工具级
# 端到端合成链路（命令行解析 → 引擎初始化 → 语音合成 → 文件写出），
# 属于完整消费者用例而非纯断言（R34/鸿蒙特有测试要求）。
#
# 用法: test_cli.sh <bindir> <datadir> <libdir>
#   bindir  — 包内 bin/ 目录（含 espeak-ng/speak-ng）
#   datadir — 包内 share/espeak-ng-data（语音/字典数据）
#   libdir  — 包内 lib/ 目录（libespeak-ng.so，供 LD_LIBRARY_PATH）
set -eu
# 注：不用 pipefail（toybox/OHOS sh 不支持），关键命令已逐个显式校验退出码。

BIN_DIR="$1"
DATA_DIR="$2"
LIB_DIR="$3"

if [ -z "$BIN_DIR" ] || [ -z "$DATA_DIR" ] || [ -z "$LIB_DIR" ]; then
    echo "FAIL: usage: test_cli.sh <bindir> <datadir> <libdir>"
    exit 1
fi

CLI="$BIN_DIR/espeak-ng"
if [ ! -x "$CLI" ]; then
    echo "FAIL: espeak-ng CLI not found at $CLI"
    exit 1
fi

export LD_LIBRARY_PATH="$LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export ESPEAK_DATA_PATH="$DATA_DIR"

# 1) 版本与数据路径
ver="$("$CLI" --version 2>&1 || true)"
echo "$ver" | grep -q "eSpeak NG text-to-speech" || {
    echo "FAIL: espeak-ng --version output unexpected: $ver"
    exit 1
}
echo "$ver" | grep -q "espeak-ng-data" || {
    echo "FAIL: ESPEAK_DATA_PATH not reflected in --version: $ver"
    exit 1
}

# 2) 真实合成语音到 WAV（端到端 CLI 流程）
out="${TMPDIR:-/tmp}/espeak_cli_e2e_$$.wav"
rm -f "$out"
"$CLI" "Hello, this is eSpeak NG on HarmonyOS PC." -w "$out" || {
    echo "FAIL: espeak-ng -w synthesis failed"
    exit 1
}
if [ ! -f "$out" ]; then
    echo "FAIL: WAV file not created: $out"
    exit 1
fi

# 3) 校验 WAV：RIFF/WAVE 魔数 + 非空
sz=$(wc -c < "$out")
if [ "$sz" -le 100 ]; then
    echo "FAIL: WAV too small ($sz bytes)"
    rm -f "$out"
    exit 1
fi
magic=$(head -c 12 "$out" | od -An -c | tr -d ' \n')
case "$magic" in
    *R*I*F*F*W*A*V*E*)
        ;;
    *)
        echo "FAIL: WAV RIFF/WAVE magic not found: $magic"
        rm -f "$out"
        exit 1
        ;;
esac

rm -f "$out"
echo "CLI e2e PASSED: espeak-ng --version OK, WAV $sz bytes (RIFF/WAVE)"
exit 0
