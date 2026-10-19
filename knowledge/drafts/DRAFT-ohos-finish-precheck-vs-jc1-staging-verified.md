# DRAFT-ohos-finish-precheck-vs-jc1-staging-verified：finish Step10 预检要求 `.staging-verified` 存在，JC1 却把"被 git 跟踪的它"判垃圾——设备端创建、绝不提交

> Source: xmedcon/0.26.1-gtk3 真机 shadow CI r3–r6、r14–r16（2026-10-13/16）
> 对应 KV: knowledge/drafts/DRAFT-ohos-finish-precheck-vs-jc1-staging-verified.kv
> 同族: DRAFT-13618（G0e 根目录白名单也读 git 索引，repo-source 会继承暂存文件）——本条是**包内标记文件**侧的同一机理增量

## 一句话

`ohc-run.py finish` 的 Step10 submit 预检要求包目录存在空的 `.staging-verified`；
而 `junk_check.sh` JC1/JC5 会把**被 git 跟踪**的 `.staging-verified` 判为运行时状态
垃圾。处置：**设备端/本地 touch 该文件但绝不 `git add`**；若从 repo-source 快照
继承了被跟踪的同名文件，必须 `git rm --cached`（光删工作区无效）。

## 使用说明

```sh
# 1) 本地/设备端：只创建，不提交（.staging-verified 不在 .gitignore 时注意）
touch archives/<首字母>/<库名>/<版本>/.staging-verified
git status --short | grep staging-verified   # 应无输出（未跟踪不犯 JC1）

# 2) repo-source 快照若已跟踪该文件（JC 报"被跟踪"而工作区已删时）：
git -C <job>/repo rm --cached --quiet archives/l/<lib>/<ver>/.staging-verified
rm -f archives/l/<lib>/<ver>/.staging-verified

# 3) 检索命令（确认 JC 读的是索引而非磁盘）：
grep -n "git ls-files" ci/scripts/junk_check.sh
```

## 适用范围

- 所有走 `finish`（Step10 submit 就绪预检）+ `build_and_test.sh`（JC 门禁）的
  真机/本地流程；任何"标记文件被预检要求、又被 JC 按跟踪状态判垃圾"的对偶
  场景（`.staging-verified`、`.build-closed`、`.handoff.json` 同理）。
- 不适用：网站 CI 侧（那里以提交树为准，`.staging-verified` 本来就不该在提交里）。

## 输入 / 输出

- 输入：Step10 预检报"需创建 .staging-verified"；或 JC1 报"运行时状态文件被跟踪"。
- 输出：预检 ✅ 且 JC pass；提交树中不含任何 `.staging-verified`。

## 示例（xmedcon 实测）

- r5→r6：repo-source（libxft 快照）的 `archives/l/libxft/2.3.9/.staging-verified`
  工作区已删仍被 JC 报 → `git rm --cached` 后 JC 放行。
- r15→r16：预检报"需创建"，设备端 `touch` 后 ✅（设备 job repo 无 .git，JC 退化
  为跳过/全量扫描，不冲突）。
- 提交边界：本地 worktree **不提交**该文件，PR 树干净（已实测 PR #16199 CI 无 JC 告警）。

## 查重边界（2026-10-16 全库扫描）

| 既有条目 | 差异 |
|---|---|
| DRAFT-13618-shadow-repo-source-g0e-git-index-staged-root-file | 那条讲 **G0e 根目录白名单**读 git 索引、repo-source 继承根目录暂存文件；本条讲 **JC1/JC5 对包内标记文件**的同一机理 + 与 Step10 预检的**需求矛盾**及"设备端创建、git rm --cached"组合处置 |
| DRAFT-*jc-fullmode-baseline-isolation 系列 | 那是 JC 全量扫描的基线噪声豁免；本条是单文件跟踪状态矛盾，不涉基线 |
| finish Step10 预检本身 | 无条目说明其要求与 JC1 的冲突，属流程空白增量 |
