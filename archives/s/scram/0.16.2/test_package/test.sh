#!/usr/bin/env bash
# scram test_package 消费者测试：
#   1. scram --version 校验可执行与版本输出
#   2. 端到端故障树分析：验证输入文件处理与报告生成
# 用法: test.sh <scram 二进制绝对路径>
set -euo pipefail

SCRAM_BIN="$1"
if [ -z "$SCRAM_BIN" ] || [ ! -x "$SCRAM_BIN" ]; then
  echo "ERROR: scram 二进制无效: $SCRAM_BIN" >&2
  exit 1
fi

# scram 二进制 NEEDED 为相对路径 ../lib/scram/libscram.so，
# 依赖 cwd 解析；cd 到 bin 目录使包内相对路径可解析。
cd "$(dirname "$SCRAM_BIN")"
SCRAM="./$(basename "$SCRAM_BIN")"

echo "=== 1. scram --version ==="
"$SCRAM" --version
"$SCRAM" --version | grep -q "SCRAM 0.16.2"
echo "OK: 版本输出正确"

echo "=== 2. 端到端故障树分析 ==="
WORKDIR="$(mktemp -d "${TMPDIR:-$HOME/tmp}/scram-test.XXXXXX" 2>/dev/null || mktemp -d "$HOME/tmp/scram-test.XXXXXX")"
cat > "$WORKDIR/input.xml" << 'XML'
<?xml version="1.0"?>
<opsa-mef>
  <define-fault-tree name="TestTree">
    <define-gate name="TopEvent">
      <and>
        <basic-event name="A"/>
        <basic-event name="B"/>
      </and>
    </define-gate>
    <define-basic-event name="A">
      <float value="0.1"/>
    </define-basic-event>
    <define-basic-event name="B">
      <float value="0.2"/>
    </define-basic-event>
  </define-fault-tree>
</opsa-mef>
XML

"$SCRAM" "$WORKDIR/input.xml" > "$WORKDIR/report.xml"
if [ ! -s "$WORKDIR/report.xml" ]; then
  echo "ERROR: 未生成分析报告" >&2
  exit 1
fi
grep -q "Minimal Cut Sets" "$WORKDIR/report.xml" \
  && echo "OK: 故障树分析成功（报告含 Minimal Cut Sets）" \
  || { echo "ERROR: 报告缺少 Minimal Cut Sets" >&2; exit 1; }

rm -rf "$WORKDIR"
echo "=== 全部测试通过 ==="
