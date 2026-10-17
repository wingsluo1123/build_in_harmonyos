#!/data/service/hnp/bin/bash
# test_package/test.sh — tup 0.8 可执行包冒烟测试
# 运行于 conanrun 环境：PATH 已包含本包 bin/，bin/ 下有 tup + tup-ldpreload.so
set -euo pipefail

echo "[test] tup --version"
tup --version
tup --version | grep -q "0.8" || { echo "❌ 版本串不含 0.8（TUP_LABEL 未生效）"; exit 1; }

echo "[test] tup server（HarmonyOS 平台分支应选择 ldpreload）"
srv="$(tup server)"
[ "$srv" = "ldpreload" ] || { echo "❌ 期望 ldpreload 后端，实际: $srv"; exit 1; }

echo "[test] 依赖追踪注入库必须与可执行文件同目录"
bindir="$(cd "$(dirname "$(command -v tup)")" && pwd)"
[ -f "$bindir/tup-ldpreload.so" ] || { echo "❌ $bindir/tup-ldpreload.so 缺失"; exit 1; }

echo "[test] 端到端：touch 产出输出的规则 + 增量判定"
# 工作目录要可写（OHOS /tmp 是只读 erofs，且 tup 自己也需要可写 TMPDIR），但它落在
# 本仓受跟踪目录内，故用 trap 保证进出都清理：否则 conan create 会在
# test_package/ 下留下 *.log 与 .tup/，被 `git add archives/...` 误提交后触发
# CI 的 junk 检查（*.log 属禁止提交项）。
work="$PWD/tup-test-work"
test_root="$PWD"
rm -rf "$work"; mkdir -p "$work"
trap 'cd "$test_root" && rm -rf "$work"' EXIT
cd "$work"
export TMPDIR="$work"
printf ': |> touch %%o |> out.txt\n' > Tupfile
tup init --no-sync --force > /dev/null
tup > first.log 2>&1 || { echo "❌ 首次构建失败"; cat first.log; exit 1; }
[ -f out.txt ] || { echo "❌ out.txt 未生成"; exit 1; }
grep -q "Updated." first.log || { echo "❌ 首次构建未报告 Updated"; cat first.log; exit 1; }
tup > second.log 2>&1 || { echo "❌ 二次执行失败"; cat second.log; exit 1; }
if grep -q "touch out.txt" second.log; then
	echo "❌ 未变更却重建了 out.txt（依赖追踪失效）"; cat second.log; exit 1
fi

echo "✅ tup 0.8 smoke test 通过（版本 / ldpreload 后端 / 同目录 .so / 端到端增量）"
