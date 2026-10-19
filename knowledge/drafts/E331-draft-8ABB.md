# E331 — W3 JC full 模式扫描既有基线标记文件（索引级隔离复验）

## 错误特征
- finish W3 本地 CI `build_and_test.sh` 报 `Junk Files: N` /
  `JC1: N 个运行时状态文件被跟踪` / `JC5: N 个 archives 下未登记的隐藏文件`
- 命中的文件属于其他库（如 cloog/kics/thc）提交在 main 上的空基线标记
  （`.build-closed` / `.staging-verified`，SHA-256 均为空文件 `e3b0c442...`），
  与当前适配库无关

## 触发条件
- junk_check.sh 在无 PR diff 时落入 **full 模式**，`CHECK_FILES=$(git ls-files)`
  全仓扫描（数万文件），其他库既有基线标记文件被一并扫描
- CI prdiff 模式只扫 PR 变更文件，不受影响——仅本地 W3/finish 触发
- 仓库 main 上已存在其他库提交的 `.build-closed`/`.staging-verified` 标记

## 根因分析
junk_check.sh 无 PR diff 时用 `git ls-files`（索引全量）作为扫描源，而其他库
提交在 main 的运行时标记文件恰好在索引中 → JC1/JC5 误报。仅移动工作树文件
不改变索引条目，隔离必须**索引级**执行。

## 解决方案

### 推荐方案（基线隔离复验）
1. 记录精确路径与隔离前 SHA-256；
2. 索引级隔离：`git rm --cached -- <path>`（保留工作树文件）；
3. 复跑受影响门禁（finish/W3）；
4. 门禁通过后恢复索引：`git add -f -- <path>`；
5. 核对恢复后 SHA-256 == 隔离前（pre == post）；
6. 确认 staged/diff/PR 不含该路径，继续当前库交付。

### 禁止做法
- ❌ 把其他库基线标记文件删除或提交进当前库 PR
- ❌ 直接修改 junk_check.sh / ci/ 框架文件
- ❌ 隔离后不恢复索引导致 PR 附带无关删除

## 验证
```bash
git ls-files | grep -cE 'staging-verified|build-closed'   # 预判命中
git rm --cached -- <path> && <rerun finish> && git add -f -- <path>
sha256sum <path>   # pre == post
```

## 关联条目
- 相关: E256（commit 内二进制/标记文件致 CI 失败）、E074/E292/E525（make jobserver FIFO 权限）
