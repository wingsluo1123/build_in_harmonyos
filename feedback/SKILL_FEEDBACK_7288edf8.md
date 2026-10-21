# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_7288edf8.md`

---

## 背景

- **软件名称**: libwraster
- **版本**: 0.96.0
- **构建日期**: 2026-10-15
- **构建系统**: autotools（WindowMaker 0.96.0 顶层 configure + 仅编 `wrlib/`）
- **上游仓库**: https://www.window-maker.org/ （WindowMaker 0.96.0 源码包）
- **适配路径**: 路径 B（探索性适配：手写 conanfile.py + 2 个平台补丁）
- **补丁数量**: 2（`config.guess` 识别 `aarch64-unknown-linux-ohos`；`config.sub` OS 列表补 OHOS）
- **编译依赖**: libx11/6.4.0、libxext/6.4.0、libxpm/3.5.17
- **最终状态**: 成功（PR #16064 CI 校验通过，等主编合入后发布制品仓）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | WindowMaker-0.96.0.tar.gz，sha256 4fe130ba23cf4aa2… |
| build | 编译构建 | 成功 | 构建系统: autotools（顶层 configure + `make -C wrlib`，只编 wrlib） |
| conan-verify | 配方验证 | 通过 | G0-G4 全绿（去掉 libxft 假依赖后重跑），L1 测试 15/15 |
| finish | 归档收尾 | 完成 | W2 结构 + R36 依赖 + W3 conan create 通过（`.ci-result.json` exit 0） |
| submit | PR提交+AI检视+CI | 完成 | PR #16064；AI Review: 1 条 Info「✅ 未发现问题」；CI: ✅ 校验通过 |

### 失败与问题

1. **Xft 假依赖导致下游产物被注入外部库（最耗时）**
   libwraster 顶层 `configure` 通过 `pkg.m4` 对 `xft >= 2.1.0` 做**硬探针**（`configure` 18896-18945），
   而 `wrlib/` 源码零引用 Xft。原配方把 libxft 写进 `cpp_info.requires`，于是下游 wmglobe 的 ELF
   被链接出 `NEEDED libXft.so.2`（运行期依赖平台外库，违反 R26）。修正方式：配方去掉 libxft 依赖，
   用 `XFT_CFLAGS`/`XFT_LIBS` 旁路该探针；`readelf` 复核 wmglobe 产物 `DT_NEEDED` 中 libXft 计数为 0。
2. **CI 端 `config-paths.h` 无生成规则**
   本地 `make -j1 config-paths.h` 命中顶层 `Makefile.in:929` 的 BUILT_SOURCES 规则；CI worker 上
   fork 资源耗尽（`config.status: can't fork - try again`）导致生成的顶层 Makefile 缺该规则，
   报 `No rule to make target 'config-paths.h'`。修正方式：配方内自生成 `config-paths.h`（不经顶层 make 规则）。
3. **本地工具链通道问题**：`gitcode_pr.py create-pr` 的 `POST /pulls` 长挂 >300s（未写 `.submit-state.json`）；
   手动 `conan create` 因超时反复被杀，改用 `conan export` 到 plain ref + 下游 `--build=missing` 现场编译绕过。

本次流程未遇到阻塞性问题（无外部依赖止损）。

### 知识图谱使用情况

- **引用知识条目**: E540（runner-path-prepend，wmglobe 侧 conan-verify 命中）
- **新增知识草稿**: 无（本次三个问题未生成草稿，建议补条见「知识图谱覆盖」）
- **引擎命中情况**: libwraster 侧未命中已有条目
- **测试统计**: L1 `test_package` 通过；上游 `wrlib/test.c` 仅测 X 无关核心 API
- **未覆盖的错误模式**:
  1. pkg-config 硬探针（`PKG_CHECK_MODULES`）造成的「假依赖」，并经 `cpp_info.requires` 泄漏给下游；
  2. CI 构建机 fork 耗尽 → autotools 生成文件（`config-paths.h`）规则缺失；
  3. 本机 `conan download -r=ohpcd` 对未发布包报 `system acceleration policy not enabled`，与「真未发布」不可区分。

### AI 检视结果

- **检视阶段到达**: Phase 1-3（「变更摘要」30 分钟未生成 → 直接进入 CI 监控）
- **变更摘要评估**: 未生成（`handoff:ai_review_summary_timeout`）
- **检视意见数量**: 1 条（atomgit-bot「代码审查 ✅ 未发现问题」，Info 级）
- **检视意见处理**: 无实质意见，无需修改；已核验 `get-review-comments` 仅此 1 条

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`conan create` exit 0，日志 sha256 e60814783896dabe，含 L0 质量门禁）
- **远程 CI (PR 校验)**: ✅ 校验通过（2026-10-15 21:56:50；首轮 21:24 因 `config-paths.h` 缺规则失败，修复后转绿）
- **CI 失败原因**: `make -j1 config-paths.h` → `No rule to make target 'config-paths.h'`（CI worker fork 耗尽连带）

### 效率分析

- **HANDOFF 次数**: 3（自检 packaging/test_report 缺失 → 修复；create-pr 超时；AI 检视摘要超时）
- **重试次数**: 4（`submit --resume` ×2、CI 修复重推 ×2）
- **关键瓶颈**:
  1. 本地通道：`create-pr` `POST /pulls` 长挂 >300s；手动 `conan create` 被 60s 工具超时杀；
  2. CI worker fork 资源耗尽（`config.status: can't fork`）连带生成文件不全；
  3. AI 检视「变更摘要」30 分钟不生成，submit 白等一轮。
- **耗时较长的步骤**: conan-verify G2（现场从源码编译 libwraster）、CI 轮询等待、假依赖反向定位（从下游产物 NEEDED 回溯到上游探针）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 7 个事件（含 3 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-15T18:45:45 | skeleton_created | result_partial |
| 2026-10-15T18:45:45 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-10-15T20:33:41 | handoff:self_check_failed | 自检未通过: ['packaging_present', 'test_report_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit libwraster 0.96.0 |
| 2026-10-15T20:43:10 | handoff:pr_creation_timeout | gitcode_pr.py create-pr 超时，请手动重试或检查网络 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/libwraster-0.96.0 --target main --title 'feat(libwraster): 0.96.0 适配完成' |
| 2026-10-15T20:46:03 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-10-15T20:46:03 | skeleton_exists | resume_pr_exists |
| 2026-10-15T21:16:08 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #16064 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 16064 \| 摘要出现后: python3 scripts/ohc-run.py submit libwraster 0.96.0 --resume |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

1. **增加「探针 ≠ 依赖」检查（本次最大耗时根因）**：autotools 包的 `configure`/`pkg.m4` 硬探针会让未真正使用的库进入依赖链，
   再经 `cpp_info.requires` 传给下游，最终表现为**下游产物运行期依赖平台外 .so**。建议 G4/预扫描增加两条：
   ① 扫描 `configure`/`configure.ac` 中 `PKG_CHECK_MODULES` 与源码实际引用的差集并告警；
   ② 对下游产物做 `DT_NEEDED` 白名单校验（每个外部 .so 必须能在 `requires` 闭包里找到来源）。
2. **R36/L0i 本地依赖探针口径统一**：本机 `conan download -r=ohpcd` 对未发布包报 `system acceleration policy not enabled`，
   与「已发布但本机受限」不可区分，AI 只能靠公开 search API 交叉判断。建议 L0i 直接复用 PF4 的公开 search API 探测，
   或在报错里区分「未发布 / 本机受限」。
3. **CI 侧 fork 资源**：worker 出现 `config.status: can't fork` 时生成的 Makefile 不完整，问题被伪装成「配方错误」。
   建议 `build_and_test.sh` 前置 `fork` 可用性探测（或对生成产物做完整性校验），失败时归类为**环境问题**而非配方问题。
4. **本地 W3 与制品仓 single-revision 冲突的变通纳入文档**：`conan create` 在受限环境易被超时杀，
   `conan export` 到 plain ref + 下游 `--build=missing` 现场编译是可复现路径，建议写入 compile-guide。

### 模板改进

1. **autotools 配方模板补「生成文件兜底」范式**：对只在顶层 `Makefile` BUILT_SOURCES 里定义规则的生成文件
   （如本次 `config-paths.h`），模板应给出一段「配方内自生成」的示例，避免 CI 端因环境差异缺规则。
2. **反馈骨架占位符吸收**：本报告背景段与执行概要的 `{BUILD_SYSTEM}` 未被自动填充，仍以占位符形态交付，
   建议 init/finish 阶段探测构建系统后自动回填（本次靠人工修）。
3. **conandata.yml 补丁声明**：`config.guess`/`config.sub` 这类平台补丁应默认带 `platform_only: True`，
   模板可预置该字段提示，减少手工补写。

### 自动化补全

1. **`ci-status` 交叉校验构建步骤**：本次端点曾报 `✅ PASSED`（21:24:43）而 `conan-build-test` 步骤实际失败，
   建议 `ci-status` 同时解析构建步骤表格，避免「假绿」误导决策。
2. **create-pr 通道自适应回退**：本地 `POST /pulls` 长挂时自动改走 AtomGit 官方 API（`POST /repos/{o}/{r}/pulls`），
   并把 PR 号回写 `.submit-state.json`，省掉人工补状态文件。
3. **AI 检视摘要超时的二次触发**：摘要 30 分钟未生成时，submit 可自动重发一次触发评论（与 CI `/rebuild` 同构），
   而不是直接跳过 Phase 1-3 进入 CI 监控。
4. **result.json 路径隔离**：同机多任务共用 `$HOME/ohpcd-ai-worker-result.json` 时会被他任务终态覆盖，
   建议默认按 `<任务/包>` 子目录隔离，或写入前检测串扰。

### 知识图谱覆盖

建议新增 3 条 E-entry（本次实测、可复用）：

1. **pkg-config 硬探针假依赖**：`configure` 中 `PKG_CHECK_MODULES` 命中但源码零引用 → 依赖被当真实依赖传递，
   下游产物出现平台外 `DT_NEEDED`。修复：去掉 `cpp_info.requires` 条目 + 用 `XFT_CFLAGS/XFT_LIBS` 旁路探针。
2. **CI 构建机 fork 耗尽连带生成文件缺失**：`config.status: can't fork - try again` →
   顶层 Makefile 缺 BUILT_SOURCES 规则 → 报 `No rule to make target`。修复：配方内自生成该文件，不依赖顶层 make。
3. **未发布依赖的本机探针歧义**：`conan download -r=ohpcd` 报 `system acceleration policy not enabled` 时，
   必须用公开 search API 交叉验证，禁止直接判定「未发布」（与 R35 同族）。

---

## 作者

- **姓名**: @hejin111
- **邮箱**: hejin111@noreply.gitcode.com
- **Agent ID**: B1BF
- **生成时间**: 2026-10-15 18:45:45
- **PR 编号**: #16064
- **Git Commit**: 3f999351eb
