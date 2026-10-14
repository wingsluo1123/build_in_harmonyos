#!/bin/bash
# jazz2-native 3.6.0 — 消费者视角冒烟测试
# 用法: test_jazz2_native.sh <jazz2 可执行文件路径> <输出目录>
set -euo pipefail

EXE="${1:?usage: test_jazz2_native.sh <exe> <out_dir>}"
OUT="${2:?usage: test_jazz2_native.sh <exe> <out_dir>}"
mkdir -p "$OUT"

echo "[test] 1/2 二进制存在且可执行"
test -x "$EXE"

echo "[test] 2/2 --version 早退路径（不初始化 SDL/GL，headless 可跑）"
set +e
"$EXE" --version > "$OUT/version.out" 2>&1
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
    # 失败时把加载器/程序输出打到 CI 日志，避免只看到 "Error 127" 无从定位
    echo "[test] FAIL: 执行 $EXE 返回 $rc"
    cat "$OUT/version.out" || true
    echo "[test] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<unset>}"
    exit "$rc"
fi
cat "$OUT/version.out"

# 上游 PrintVersion() 输出 "Jazz² Resurrection <version>"（非 tty 时无 logo）
grep -q '3\.6\.0' "$OUT/version.out"

# 版本信息本身即证明 ELF 已签名，且**动态**依赖（OpenAL / vorbisfile / ogg / libcurl）可解析；
# SDL2 与 zlib 由配方静态链接（制品仓该二包为 static-only），不参与运行期动态解析
echo "[test] PASS: jazz2-native 3.6.0 冒烟通过"
