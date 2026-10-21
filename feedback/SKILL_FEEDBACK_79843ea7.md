# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_79843ea7.md`

---

## 背景

- **软件名称**: wmjupiter
- **版本**: 1.21
- **构建日期**: 2026-10-16（最终 W3 复验日；编译始于 10-15）
- **构建系统**: makefile
- **上游仓库**: https://codeload.github.com/engerim42/wmjupiter/tar.gz/refs/tags/1.21
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 2
- **编译依赖**:
- libx11/6.4.0
- libxext/6.4.0
- libxpm/3.5.17
- xorgproto/2025.1
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: makefile |
| conan-verify | 配方验证 | 通过 | G0-G4 + L2/L4/L5 全 PASS（G3 系统同名库隔离无冲突） |
| finish | 归档收尾 | 完成 | W2 结构 + R36 依赖 + W3 conan create 通过（.ci-result.json exit_code=0） |
| submit | PR提交+AI检视+CI | 部分失败→手工续环 | 内建建 PR 路径挂死（preflight 探测无超时，rc=124×2）→ `--no-preflight` 手工建 PR #16039；AI 检视 4 条意见已逐条处理（其中 2 条已修复并标记已解决）；CI 续环至绿（构建 #94748） |

### 失败与问题

本次遇到两处**工具级**阻塞（非软件适配问题，细节见「建议」1-3）：

1. `submit` 内建建 PR 路径挂死（preflight 闸门探测无超时，rc=124×2），只能改走
   `create-pr --no-preflight` 手工建 PR，并手工续环 CI；
2. `monitor-review` 崩溃（`gitcode_pr.py:1066` NameError），AI 检视闭环改由
   `get-review-comments` + `handle-review-opinion` 手工完成。

软件侧（编译 / 配方 / 用例）无阻塞：W3 本地 conan create 与远程 CI 均绿。

### 知识图谱使用情况

- **引用知识条目**: E491（clang 15 `-fno-common` 下 `xutils.h` 试探性定义 → 链接期 duplicate symbol；按其 `rec_approach` 改 extern 声明 + 单一定义，并规避其 `forbid_1`）
- **新增知识草稿**: 1 条
- **引擎命中情况**: 草稿目录 3574 条
- **测试统计**: 总计 24, 通过 24, 失败 0, 跳过 0（`test_package/test_wmjupiter.sh`：A 类失败路径 7 + B 类协议级端到端消费者用例 17）
- **未覆盖的错误模式**: 无知识缺口。本次核心修法（clang 15 `-fno-common` 下 `xutils.h` 试探性定义引发的链接期 duplicate symbol）直接命中既有条目 **E491**，按其 `rec_priority: 1` 采用「extern 声明 + 单一定义」并显式规避其 `forbid_1`（`-fcommon`）。两处新问题是**工具缺陷而非错误模式**：(a) `create-pr` 预检（PF 闸门探测）无超时导致 submit 进程永久挂起；(b) `monitor-review` 因 `NameError: unreplied_opinions` 崩溃。二者已按平台问题回报，不进 E-entry。

### AI 检视结果

- **检视阶段到达**: Phase 4（4 条行级意见全部处理完毕）
- **变更摘要评估**: 监控工具 `monitor-review` 在本检出中崩溃（`scripts/gitcode_pr.py:1066` `NameError: name 'unreplied_opinions' is not defined`），AI 检视闭环改由 `get-review-comments` + `handle-review-opinion` 手工完成
- **检视意见数量**: 4 条——2 条 ⚪ Info（`193995639`/`194007412`，「代码审查 ✅ 未发现问题」，无待修复项）＋ 1 条 Critical（`194099989`）＋ 1 条 Medium（`194109382`），后两条同根：`x11_headless.py` 请求字段偏移
- **检视意见处理**: 已闭环——Critical/Medium 均按权威线格式修复（`_req_97` 的 width/height 改读偏移 8/10；同类排查一并改净 `_req_91` 与 SHAPE 三个请求），提交 `810e2556d8`，逐条回复并标记已解决（`reply_to: 194099989 / 194109382`）；两条 Info 无待修复项

### CI 结果

- **本地 CI 模拟 (W3)**: ✅ 通过（`.ci-result.json` `exit_code=0`，含 conan create 日志 SHA256）
- **远程 CI (PR 校验)**: ✅ PASSED（PR #16039，构建 **#94748**，worker **OpenHarmonyPCDeveloper-CI-011**；Conan test_package / L0 结构完整性 / L1 测试执行三门禁通过，7 个构建步骤全 ✅）
- **CI 失败原因**: 无。门禁结果：Conan test_package 通过 / L0 结构完整性通过 / L1 测试执行验证通过；构建 7 步（worker_preparation、worker-prep、git-clone、checkout-pr、conan-setup、conan-build-test、cleanup）全 ✅

### 效率分析

- **HANDOFF 次数**: 1（`self_check_failed: ['packaging_present']`）；另有 `result` 参数校验 exit 2 两次（缺 `--failed-reason` / 已有草稿需 `--force`），属参数级反馈非任务失败
- **重试次数**: 提交链 4 次——`submit` 2 次（第 1 次被自检拦下、第 2 次建 PR 段挂死）+ 手工 `create-pr` 2 次（try1 rc=124 超时、try2 `--no-preflight` 成功）
- **关键瓶颈**: `submit` 内建建 PR 路径。preflight 闸门探测无显式超时 → submit 进程在网络读上永久挂起（约 20 分钟零输出、无子进程、无 `.submit-state.json`）；因状态文件从未落盘，`submit`/`--resume` 双双不可用（`resume_no_state`），只能退回手工 `create-pr` 脚本
- **耗时较长的步骤**: ① 手工编译取证（为隔离 AutotoolsDeps flag 变量建 8 个探针目录）；② 建 PR 链路（~25 分钟，含两次 rc=124 等待）；③ 依赖版本线核实（libxpm↔libx11 的 `force=True` 钉版关系）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 3 个事件（含 1 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-15T17:35:37 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-10-15T18:34:35 | skeleton_created | result_partial |
| 2026-10-15T18:44:50 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit wmjupiter 1.21 |
<!-- EVENTS:END -->
---

## 建议

1. **`submit` 建 PR 路径缺超时保护（本次最大阻塞）**：preflight 闸门探测（PF4 制品仓探测等）使 submit 进程在网络读上永久挂起——无输出、无子进程、无状态文件，两次各 240s+ 均 rc=124。建议：① 给 preflight 每次 HTTP 探测加显式 `timeout=`，并设总预算（如 60s，超时降级为警告而非挂起）；② **POST 建 PR 前先落盘 `.submit-state.json`（pending 态）**，使超时/被杀后 `--resume` 仍可用；当前"无状态文件 → resume_no_state → 整链不可用"会把一次网络抖动放大为全流程手工化。
2. **preflight 挂起可复现且可隔离**：同参数下加 `--no-preflight` 立即成功（rc=0，PR 秒建），说明卡点在探测而非 POST。建议把 PF 闸门做成"快速失败 + 可单独运行"（如 `ohc-run.py preflight wmjupiter 1.21` 带进度输出），避免闸门成为不可观测黑盒。
3. **`monitor-review` 崩溃**：`scripts/gitcode_pr.py:1066` `NameError: name 'unreplied_opinions' is not defined`（同文件 `cmd_monitor_review`），AI 检视闭环监控完全失效，只能手动 `get-comments`。建议补单测覆盖该分支（该函数是 R42/R45 闭环的咽喉）。
4. **建 PR 前置自检缺可执行指引**：`packaging_present` 失败仅提示"需创建 packaging/ 目录"，未给生成命令；建议 finish 内在 STAGING 验证通过后自动产出 `packaging/<name>-<ver>.tar.gz`（`p` 前缀包树），或至少打印可复制命令。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

1. **反馈骨架的『知识图谱使用情况』字段语义错位**：骨架初稿把「引用知识条目」填成了"无"（本次已人工修正为 E491），而实际修法**直接取自 E491**（`knowledge_gained` 在 manifest 中已记录）；同节「引擎命中情况」却填了草稿目录总数（3574 条）。建议骨架从 `manifest.yaml`/`notes.md` 的 `knowledge_gained` 回填引用条目，并把"草稿目录总数"与"引擎命中"分列。
2. **conanfile 模板仍留空串占位**：`url = ""` 与 `config_version` 注释 `# CI fills this`，虽属全仓惯例（7zip/a52dec 等同样写法），但会被 PF7/PF8 类静态闸与人工检视反复标记。建议模板预填上游官方 URL（`homepage`），或把该行从静态闸的"占位符"清单中显式豁免。
3. **PR body 模板建议补两节**：本次正文需自证「上游测试清点证据」（R51）与「R40 人工确认标注」，二者均为当前模板未设栏位、却属真人评审高频质询点；建议在积分赛模板中加入"上游测试清点证据"小表与"未验证项 / 需人工确认"声明栏。
4. **test_package MANIFEST.yml 与软件级/版本级 manifest 存在三处重复事实**（断言数、测试清点、依赖线），本次审计即抓到"三处写 6/7 不一致"。建议：以版本级 `manifest.yaml` 为单一事实源，MANIFEST.yml 仅保留引用式说明，杜绝多处手写数字。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

1. **packaging 产物自动化**：`packaging/<name>-<ver>.tar.gz`（`p` 前缀包树，内容=conan 包目录）当前需人工 `tar`；finish 阶段已具备 STAGING 树与包目录，可自动产出，消除 `packaging_present` 这一人工前置。
2. **建 PR 的兜底路径工具化**：本次实际形成的流程是「`submit` 挂起 → 定向脚本 `create-pr --no-preflight` → 按源分支复核 → `trigger-ci` 评论 `/rebuild` → 手动轮询」。这套"手工兜底"已是第二次出现（xiccd 线同型），建议收敛为 `ohc-run.py` 的显式开关（如 `submit --direct` 或独立 `resume-pr` 子命令），并在建 PR 后自动回写 `.submit-state.json`，使后续 `--resume` 可续。
3. **`result --status partial` 不应强制 `--failed-reason`**：partial 是"里程碑未完成/replaceable 草稿"语义，本次被迫把"PR 已建、CI 调度中"写成 failed_reason 文案，容易被 ECS 误读为失败。建议该字段对 partial 改为选填（或改名 `--note`）。
4. **CI 触发确认闭环**：`trigger-ci` 已回显 note_id，但"CI 是否真的开跑"仍需人工轮询 `ci-status`；建议 `trigger-ci` 内建"最长 N 秒内确认为 RUNNING/QUEUED，否则重发或报警"的自证逻辑。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

1. **无知识缺口**：本次唯一实质技术障碍（clang 15 默认 `-fno-common` 下头文件里 7 个全局变量（跨 6 行 extern，试探性定义）导致的链接期 duplicate symbol）已被 **E491** 精确覆盖，其 `rec_approach`（改 `extern` 声明 + 单一定义）与 `forbid_1`（禁用 `-fcommon` 全局放开）均直接可用，命中即解，无需新增 E-entry——知识库在本包上表现为"高置信、可执行"。
2. **建议补一条"操作类"知识（非错误模式）**：`submit` 无状态文件（`resume_no_state`）时的手工续环配方——`create-pr --no-preflight` → `list-prs --source-branch` 复核 → `trigger-ci` 评论 `/rebuild` → `ci-status` 轮询 → `result --status success --force`。xiccd 与 wmjupiter 两条独立任务均走到同一路径，建议沉淀为操作知识点（而非错误条目），避免后续 agent 重复摸索 20 分钟以上。
3. **E491 使用侧可补一句**：其适用面可显式扩到"`x86/arm` 老代码 + X11/dockapp 类 1990s C 工程"（本包 `xutils.h` 即典型），便于引擎在老旧 C 代码库上更早命中。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: @hejin111
- **邮箱**: hejin111@noreply.gitcode.com
- **Agent ID**: 5F59
- **生成时间**: 2026-10-15 18:34:35
- **PR 编号**: #16039
- **Git Commit**: bbb5e561f9
