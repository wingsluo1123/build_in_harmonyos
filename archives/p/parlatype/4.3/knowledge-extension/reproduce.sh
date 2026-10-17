#!/usr/bin/env bash
# reproduce.sh — 演示「关策略复现原报错 / 开策略通过」
#
# 用法:
#   reproduce.sh [--skill-root <仓库根>] [--work-dir <目录>] [--no-clean]
#
#   A 关策略: 复制本配方到工作目录并剥除「禁用 yelp 帮助页」补丁声明，
#             使 help/ 子目录回到上游行为（无条件 subdir('help') →
#             gnome.yelp() → itstool）。预期 conan create 失败，报 itstool 错误。
#   B 开策略: 用配方原样跑 conan create。预期通过。
#
# 默认（--no-clean 关闭时）每步先 conan remove 本包，保证"干净无缓存"环境；
# 依赖仍走制品仓（--build=missing 只在缺 binary 时回退源码，依赖已在 ohpcd）。
#
# 前置: 本机 patch 必须是可用的 GNU/busybox patch。部分 OHOS 镜像自带 toybox
#       的 patch 是空实现（静默 no-op，退出码 0 却不改文件），脚本会自检并提示。

set -euo pipefail
# 安全模式（code-style#7）。注意本脚本有三处「非零退出码属于预期」的调用，
# 均已显式容错，不会被 -e 提前中断：
#   1) patch 自检——toybox 的 patch 静默 no-op，靠事后比对文件内容判定；
#   2) A 关策略 conan create——预期非 0（复现原报错）才是复现成功；
#   3) B 开策略 conan create——预期 0。两者退出码均由 `|| RC=$?` 捕获后判定。

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# knowledge-extension → 版本 → 包 → 首字母 → archives → 仓库根
REPO_ROOT=$(cd "$SCRIPT_DIR/../../../../.." && pwd)
WORK_DIR="$HOME/tmp/parlatype-kb-repro"
CLEAN=1
PKG_NAME=parlatype
PKG_VER=4.3

while [ $# -gt 0 ]; do
    case "$1" in
        --skill-root) REPO_ROOT="$2"; shift 2 ;;
        --work-dir)   WORK_DIR="$2"; shift 2 ;;
        --no-clean)   CLEAN=0; shift ;;
        -h|--help)    sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

PROFILE_H="$REPO_ROOT/ci/conan/profiles/ohos-aarch64"
PROFILE_B="$PROFILE_H"
RECIPE_DIR="$REPO_ROOT/archives/p/$PKG_NAME/$PKG_VER"

for f in "$PROFILE_H" "$RECIPE_DIR/conanfile.py"; do
    if [ ! -f "$f" ]; then
        echo "FAIL: required file not found: $f" >&2
        exit 2
    fi
done

# ---- patch 可用性自检（toybox 的 patch 是空实现，会让补丁静默失效）----------
PATCH_PROBE=$(mktemp -d 2>/dev/null || echo "$WORK_DIR/.patch-probe")
mkdir -p "$PATCH_PROBE"
printf 'line1\nline2\nline3\n' > "$PATCH_PROBE/f.txt"
cat > "$PATCH_PROBE/p.patch" <<'PATCH'
--- a/f.txt
+++ b/f.txt
@@ -1,3 +1,3 @@
 line1
-line2
+line2-patched
 line3
PATCH
( cd "$PATCH_PROBE" && patch -p1 < p.patch >/dev/null 2>&1 ) || true
if ! grep -q "line2-patched" "$PATCH_PROBE/f.txt" 2>/dev/null; then
    echo "WARNING: 本机 patch 是空实现（补丁静默失效）。"
    echo "         请把可用的 patch（GNU 或 busybox）放到 PATH 最前再运行本脚本，"
    echo "         否则 A/B 两步都不会真正打补丁、结论不可信。"
    rm -rf "$PATCH_PROBE"
    exit 3
fi
rm -rf "$PATCH_PROBE"
echo "patch 自检通过: $(command -v patch)"

mkdir -p "$WORK_DIR"

run_create() {
    _dir="$1"; _log="$2"; _label="$3"
    if [ "$CLEAN" -eq 1 ]; then
        conan remove --confirm "$PKG_NAME/$PKG_VER" >/dev/null 2>&1 || true
    fi
    echo "--- [$_label] conan create $_dir"
    _rc=0
    conan create "$_dir" \
        -pr:h="$PROFILE_H" -pr:b="$PROFILE_B" --build=missing \
        > "$_log" 2>&1 || _rc=$?
    echo "--- [$_label] exit code: $_rc  (log: $_log)"
    return $_rc
}

# ============================================================ A 关策略
NOPATCH_DIR="$WORK_DIR/recipe-skill-off"
rm -rf "$NOPATCH_DIR"
cp -r "$RECIPE_DIR" "$NOPATCH_DIR"
rm -rf "$NOPATCH_DIR/knowledge-extension"

python3 - "$NOPATCH_DIR/conandata.yml" <<'PY'
import re, sys
path = sys.argv[1]
lines = open(path, encoding="utf-8").read().splitlines(True)
out, skipping = [], False
for ln in lines:
    if re.match(r"^patches\s*:", ln):
        skipping = True
        continue
    if skipping:
        # 块内：空行或缩进行；遇到下一个顶层键则结束
        if ln.strip() == "" or ln[:1].isspace():
            continue
        skipping = False
    out.append(ln)
open(path, "w", encoding="utf-8").write("".join(out))
PY
if grep -q "^patches:" "$NOPATCH_DIR/conandata.yml"; then
    echo "FAIL: 未能剥除 conandata.yml 的 patches 声明" >&2
    exit 2
fi
echo "关策略复制件: $NOPATCH_DIR（已剥除 yelp 禁用补丁声明）"

RC_OFF=0
run_create "$NOPATCH_DIR" "$WORK_DIR/skill-off.log" "A 关策略" || RC_OFF=$?

# ============================================================ B 开策略
RC_ON=0
run_create "$RECIPE_DIR" "$WORK_DIR/skill-on.log" "B 开策略" || RC_ON=$?

# ============================================================ 结论
echo
echo "================ 复现结论 ================"
echo "A 关策略 exit code = $RC_OFF  (预期非 0)"
echo "B 开策略 exit code = $RC_ON   (预期 0)"
if [ "$RC_OFF" -ne 0 ]; then
    echo "A 步命中的 itstool 报错特征:"
    # 不用管道 head（SIGPIPE）：先落盘再取前 8 行
    grep -nE "code=126|itstool|Program '.*' not found|yelp" "$WORK_DIR/skill-off.log" \
        > "$WORK_DIR/skill-off-hits.txt" 2>/dev/null || true
    sed -n '1,8p' "$WORK_DIR/skill-off-hits.txt" | sed 's/^/    /'
fi
if [ "$RC_OFF" -ne 0 ] && [ "$RC_ON" -eq 0 ]; then
    echo "结论: 复现成功——关策略报 itstool 错误，开策略通过。"
    exit 0
fi
echo "结论: 与预期不符，请检查上面两份日志。" >&2
exit 1
