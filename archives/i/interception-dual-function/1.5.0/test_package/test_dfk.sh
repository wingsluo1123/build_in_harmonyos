#!/usr/bin/env bash
# 上游接口功能测试（消费者视角）。
#
# dual-function-keys 是 interception-tools 的过滤插件：从 stdin 读
# struct input_event 二进制流，按 -c 指定的 YAML 配置改写，再写回 stdout。
# 本脚本驱动该公开接口，断言上游文档化的 tap/hold/透传行为与命令行契约。
set -eu
BIN_DIR="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/test_dfk.py" "$BIN_DIR" "$HERE/cfg.yaml"
