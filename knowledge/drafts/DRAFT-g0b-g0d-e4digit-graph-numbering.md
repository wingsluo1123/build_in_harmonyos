# DRAFT — CI G0b/G0d 知识图谱完整性门禁编号规则未随知识库编号增长更新（框架层）

## 错误特征

任意基于最新 `main` 的 PR 触发 CI，`conan-build-test` 步骤在 G0 前置门禁失败：

```
[step] G0: Knowledge graph integrity check...
[fail] G0b: knowledge/graph/ 下有 1000 个非标准命名的 .kv 文件（仅允许 E###.kv）:
       /storage/Users/currentUser/.cache/buildbot-worker/conan-pr-check/build/knowledge/graph/E1000.kv
       /storage/Users/currentUser/.cache/buildbot-worker/conan-pr-check/build/knowledge/graph/E1001.kv
       ...
program finished with exit code 1
```

失败步骤为 `conan-build-test`（worker_preparation / git-clone / checkout-pr /
conan-setup 均 ✅），失败类别被诊断为"未知"，与包代码无关。

## 触发条件

- 前置: 知识库 `knowledge/graph/` 编号超过 3 位（E1000+）。主编批量归档后，
  线上 `main` 的 `knowledge/graph/` 有 2001 个 `.kv`（E001-E1999），其中
  **E1000-E1999 恰好 1000 个 4 位编号文件**。
- 任意软件包 PR（无论编译是否成功）都会在 G0 前置门禁硬失败，`exit 1`
  跳过所有后续阶段（L0/L1/L2/L4/L5 全部 skip）。

## 根因分析

`ci/conan/build_and_test.sh` 的 G0 知识图谱完整性门禁于 2026-08 引入
（提交 `ccecdc506c feat(ci): G0 知识图谱完整性前置门禁`），当时知识图谱
编号为 E001-E###（3 位）。规则：

```zsh
# G0b: 只允许 E###.kv + _template.kv + principles.kv
G0_BAD_KV=$(ls -1 "${GRAPH_DIR_G0}"/*.kv(N) 2>/dev/null \
  | grep -vE '/E[0-9][0-9][0-9]\.kv$|/_template\.kv$|/principles\.kv$' || true)

# G0d: index.tsv 行数必须与标准 .kv 文件数一致
G0_KV_COUNT=$(ls -1 "${GRAPH_DIR_G0}"/E[0-9][0-9][0-9].kv 2>/dev/null | wc -l)
```

此后主编批量归档知识库（提交 `【知识库归档】20261016-xx`），编号推进到
**E1999（4 位）**，但 G0b 白名单正则 `E[0-9][0-9][0-9]\.kv` 与 G0d 计数 glob
`E[0-9][0-9][0-9].kv` 仍只认 3 位数字：

- G0b: E1000-E1999 全部被判为非标准命名 → `G0_BAD_COUNT=1000` → G0 硬失败
- G0d: 旧规则数出 999 个 .kv，与 `index.tsv` 的 1999 行不匹配（G0b 修复后暴露）

知识库草稿侧早有 4 位编号先例（`knowledge/drafts/` 下存在 E1000-draft-*、
E13538-draft-*、E2164-draft-* 等），正式条目编号增长到 4 位是确定方向。

## 解决方案

### 推荐方案（框架层，单独提交改 ci/conan/build_and_test.sh）
把编号匹配从固定 3 位放宽到 3-4 位：

```zsh
# G0b: 允许 E###.kv / E####.kv + _template.kv + principles.kv
G0_BAD_KV=$(ls -1 "${GRAPH_DIR_G0}"/*.kv(N) 2>/dev/null \
  | grep -vE '/E[0-9][0-9][0-9][0-9]?\.kv$|/_template\.kv$|/principles\.kv$' || true)

# G0d: 统计 3/4 位编号（用 grep 而非 zsh glob，避免扩展 glob 兼容问题）
G0_KV_COUNT=$(ls -1 "${GRAPH_DIR_G0}"/E*.kv(N) 2>/dev/null \
  | grep -cE '/E[0-9][0-9][0-9][0-9]?\.kv$' || true)
```

错误消息"仅允许 E###.kv"同步改为"仅允许 E###.kv / E####.kv"。
放宽后 G0d 校验自动对齐（1999 .kv == index.tsv 1999 行）。

### 协作子任务解除阻塞（不改 ci/）
无法自行修复时，PR 只能等待框架层修复合入 main 后 rebase 重跑；
不要在 PR 里绕过 G0（如删除/移动 knowledge/graph/ 下的文件）——
正式条目由主编审核入库，贡献者不得改。

### 禁止做法
- ❌ 在 PR 中删除/重命名 `knowledge/graph/` 下的 E1xxx.kv（主编编号资产）
- ❌ 往 `knowledge/graph/` 添加任何条目（只能提交草稿到 `knowledge/drafts/`）
- ❌ 通过修改 CI 调用参数/环境变量绕过 G0 检查

## 验证

```bash
# 修复前（旧规则）：
ls -1 knowledge/graph/*.kv | grep -vcE '/E[0-9][0-9][0-9]\.kv$|/_template\.kv$|/principles\.kv$'
# → 1000（E1000-E1999 全部误判非标准）

# 修复后（新规则）：
ls -1 knowledge/graph/*.kv | grep -vcE '/E[0-9][0-9][0-9][0-9]?\.kv$|/_template\.kv$|/principles\.kv$'
# → 0

# G0d 对齐：
ls -1 knowledge/graph/E*.kv | grep -cE '/E[0-9][0-9][0-9][0-9]?\.kv$'   # → 1999
grep -c '^E[0-9]' knowledge/graph/index.tsv                              # → 1999

# 完整 CI 模拟：
CI_PACKAGES="archives/o/or-tools/9.15" CI_BRANCH=feat/or-tools-9.15 zsh ci/conan/build_and_test.sh
```

## 关联

- 实例: PR #13558 or-tools 9.15（构建 #96604 在 conan-build-test 步骤 G0b 失败）
- 机制: `ci/conan/build_and_test.sh` G0 前置门禁（G0b 命名 / G0d 索引一致性）
- 参考: `knowledge/drafts/DRAFT-10000-zsh-nullglob-g0a-empty-draft-dir`（同为
  build_and_test.sh G0 框架层门禁问题）；`knowledge/drafts/` 下 E1000-draft-*、
  E13538-draft-* 等 4 位草稿编号先例
