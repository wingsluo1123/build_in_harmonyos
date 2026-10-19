# E330 — HMDFS 大小写折叠致 git 双大小写路径恒 M（基线恢复）

## 错误特征
- `git status` 对某路径恒显示 ` M`，但该文件从未被本任务修改
- 仓库 HEAD 同时跟踪同路径双大小写条目，例如 `archives/l/libXext/`（大写）与
  `archives/l/libxext/`（小写）；HMDFS 大小写不敏感，物理文件只能体现一份内容
- 磁盘文件 sha256 与 HEAD 某一变体完全一致，但 git 仍报告另一个大小写路径已修改

## 触发条件
- 文件系统: HMDFS（大小写不敏感）；大小写敏感 FS（如 ext4）无此伪影
- 仓库: 存在双大小写路径并存的历史（如 libXext 与 libxext 多版本共存）
- 阶段: worktree checkout / git status / finish W2 原子性检查

## 根因分析
HMDFS 不区分路径大小写，git checkout 只落一份物理文件；HEAD 索引中两个大小写
条目指向同一物理文件时，git 必然对其中一个报告内容不一致（恒 M）。这不是外部
污染，也不是本任务改动，属于仓库基线特性。

## 解决方案

### 推荐方案
1. 记录精确路径与隔离前 SHA-256；
2. 按 checkout 基线内容恢复：`git restore --source=HEAD -- <变体路径>`；
3. 核对恢复后 SHA-256 == HEAD 变体（如空标记文件为 `e3b0c442...`）；
4. 确认 staged/diff/PR 不含该路径。

### 禁止做法
- ❌ 把恒 M 误判为外部污染并提交/删除该路径
- ❌ 在两个大小写变体之间反复 `git checkout` 切换分支

## 验证
```bash
git ls-files | grep -iE 'libXext|libxext'   # 确认双大小写条目
sha256sum archives/l/libXext/README.md      # 核对与 HEAD 变体一致
git diff --quiet -- archives/l/libXext/ && echo CLEAN
```

## 关联条目
- 相关: E256（归档标记文件治理面）、E046/E050/E079（HMDFS 文件系统限制族）
