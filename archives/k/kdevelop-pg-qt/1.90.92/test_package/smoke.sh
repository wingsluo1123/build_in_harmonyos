#!/bin/sh
# 消费侧真实执行 smoke（与 conanfile.py test() 的断言同源，sh 形态便于独立复跑）：
# 用随 test_package 交付的上游语法样例 fact.g 真跑一次生成器，
# 断言产出了非空的解析器实现关键件（factparser.cpp）。
# 与 KDevelop 的 KDEVPGQT_GENERATE 宏同一调用形态：
#   kdev-pg-qt --output=<name> <grammar.g>
set -eu

GENERATOR="$1"
GRAMMAR="$2"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/kdevpg-smoke.XXXXXX")"

# OHOS 上这些 ELF 没有 RUNPATH，运行时靠调用方注入 LD_LIBRARY_PATH/PATH（见 conanfile.py）。
cd "$WORK"
"$GENERATOR" --output=fact "$GRAMMAR"

if [ ! -s factparser.cpp ]; then
    echo "smoke FAILED: factparser.cpp missing or empty" >&2
    exit 1
fi
echo "smoke ok: factparser.cpp $(wc -c < factparser.cpp) bytes"
rm -rf "$WORK"
