# W2/W3 基线隔离复验审计 — xeus 5.0.0

- task_id: xeus-5.0.0-r01-pc3-5-20261009T094604Z
- 生成时间: 2026-10-09

## 触发场景

`finish` Step 5/10（W3 本地 CI 模拟 build_and_test.sh）的 JC 垃圾文件门禁
（ci/scripts/junk_check.sh，full 模式基于 `git ls-files` 整仓扫描）命中两个
**其他库（cloog 0.21.1）提交前已存在于 HEAD 的基线文件**。经核实这两个文件
为仓库历史提交（906cc59ae7 【知识库扩展】feat: adapt cloog 0.21.1）中的
运行时状态标记，非本任务产生、非 xeus 允许范围内，属于"当前库允许范围外、
提交前已存在的其他库基线文件"场景，按 oh-executor/基线隔离规则执行隔离复验。

## 逐项审计

### 条目 1

| 字段 | 值 |
|---|---|
| path | archives/c/cloog/0.21.1/.build-closed |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| isolation_command | `mv archives/c/cloog/0.21.1/.build-closed archives/c/cloog/0.21.1/.staging-verified /storage/Users/currentUser/tmp/baseline-isolation-cloog/ && git rm --cached --quiet archives/c/cloog/0.21.1/.build-closed archives/c/cloog/0.21.1/.staging-verified` |
| rerun_command | `python3 scripts/ohc-run.py finish xeus 5.0.0 built`（W3 Step5/10） |
| rerun_exit_code | 0（finish EXIT_REASON=finish_success, EXIT_CODE=0；.ci-result.json exit_code=0, log_sha256=e9b9009639ebac721e711b029872d99ffd1d964c8901c065f02c3b507b49b677） |
| restore_command | `mv /storage/Users/currentUser/tmp/baseline-isolation-cloog/.build-closed /storage/Users/currentUser/tmp/baseline-isolation-cloog/.staging-verified archives/c/cloog/0.21.1/ && git reset --quiet HEAD -- archives/c/cloog/0.21.1/.build-closed archives/c/cloog/0.21.1/.staging-verified` |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

### 条目 2（同批次第二条路径）

| 字段 | 值 |
|---|---|
| path | archives/c/cloog/0.21.1/.staging-verified |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| isolation_command | 同上（同一条隔离命令） |
| rerun_command | 同上 |
| rerun_exit_code | 0 |
| restore_command | 同上（同一条恢复命令） |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

## 自检结论

- pre_sha256 == post_sha256：✅ 两条路径均相等（隔离前与恢复后字节一致，均为空文件）
- 当前库 diff 未包含该路径：✅ `git status --short archives/c/cloog/` 为空
- staged 未包含该路径：✅（恢复后 `git reset HEAD` 同步索引与 HEAD 一致）
- PR 文件列表未包含该路径：✅（本 PR 仅 archives/x/xeus/ 变更）
- 隔离复验期间 build_and_test.sh（含 conan create + L0-L5）通过，JC gate 转绿后无其他
  当前库相关失败 → 按规则继续 xeus 审计与交付，不将该问题写成 external_blocked

## 其他说明

- `finish` step8 gen_summary 非阻塞警告（`'str' object has no attribute 'append'`）经定位为
  仓库既有 archives/q/qpdf/{12.3.2,12.3.2.1}/manifest.yaml 的解析兼容问题（qpdf 自身归档
  基线文件），非 xeus 任务引入，不在本任务允许范围内，不修改其他库文件。
- W3 期间 build_and_test.sh 预下载机制会把 conandata.yml 临时改写为镜像/file:// 形式并在
  退出时还原；最终归档 conandata.yml 已人工核验为官方 HTTPS 单 URL + 真实 sha256
  （eabe5dc2...），且已清理 .ghfast-bak/.orig 等备份残留（JC1 防拦截）。
