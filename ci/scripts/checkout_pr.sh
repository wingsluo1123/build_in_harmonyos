#!/bin/sh
# ============================================================
# checkout-pr — 方案 A（git 协议）: checkout-pr 步骤修复脚本
#
# 问题根因（原 buildbot 命令失败 exit 60）:
#   1. curl URL 误写成 markdown 链接格式 [标题](URL).diff，
#      curl 无法解析 '[' 开头的地址
#   2. GitCode 的 .diff 端点返回空内容 (HTTP 200 size=0)
#
# 方案 A: 用 git 协议拉取 PR 源分支与目标分支，本地生成 diff，
#         不依赖 GitCode .diff 下载端点（最稳健）。
#
# 用法: checkout_pr.sh <repo> <pr_branch> <base_branch> [head_sha]
#   例: checkout_pr.sh OpenHarmonyPCDeveloper/build_in_harmonyos \
#               feat/ocaml-4.14.1.1 main 7b6be941d
# ============================================================
set -e

if [ "$#" -lt 3 ]; then
    echo "usage: checkout_pr.sh <repo> <pr_branch> <base_branch> [head_sha]"
    exit 2
fi

REPO="$1"
PR_BRANCH="$2"
BASE_BRANCH="$3"
HEAD_SHA="${4:-}"

echo "PR 构建: 清理工作区并应用 PR diff patch"
git reset --hard HEAD
git clean -fdx

# 拉取 PR 源分支与目标分支（git 协议，无需 .diff 端点）
git fetch origin "$PR_BRANCH:$PR_BRANCH" "$BASE_BRANCH:base-ref"

# 生成 PR 完整 diff（base...head 三点对比 = PR 合并后变更集）
if [ -n "$HEAD_SHA" ]; then
    git diff "base-ref...$HEAD_SHA" > pr.diff
else
    git diff "base-ref...$PR_BRANCH" > pr.diff
fi
git branch -D base-ref >/dev/null 2>&1 || true

# 校验 diff 非空
test -s pr.diff || { echo "[ERROR] pr.diff 为空——请检查 PR 分支/SHA 是否可达"; exit 1; }

# 应用 PR diff
git apply --whitespace=nowarn pr.diff \
  && echo "已应用 PR diff patch" \
  || { echo "[ERROR] PR diff 无法应用——PR 与 $BASE_BRANCH 分支存在冲突"
       echo "[HINT] 请在 GitCode 上 rebase 你的分支到最新 $BASE_BRANCH，解决冲突后重新推送"
       echo "[HINT] GitCode PR 链接: https://gitcode.com/$REPO/merge_requests"
       exit 1; }
