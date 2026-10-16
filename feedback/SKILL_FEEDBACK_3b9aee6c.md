# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_3b9aee6c.md`

---

## 背景

- **软件名称**: kcharselect
- **版本**: 26.04.0
- **构建日期**: 2026-10-15
- **构建系统**: cmake
- **上游仓库**: https://download.kde.org/stable/release-service/26.04.0/src/kcharselect-26.04.0.tar.xz
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
- qtbase/6.11.1
- kbookmarks/6.18.0
- kcodecs/6.18.0
- kcolorscheme/6.18.0
- kconfig/6.18.0
- kconfigwidgets/6.18.0
- kcoreaddons/6.18.0
- kcrash/6.18.0
- kguiaddons/6.18.0
- ki18n/6.18.0
- kiconthemes/6.18.0
- kitemviews/6.18.0
- kwidgetsaddons/6.18.0
- kxmlgui/6.18.0
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: cmake |
| conan-verify | 配方验证 | 通过 | G0–G4 / L2 / L4 / L5 全 PASS（`reports/conan-verify-report.md`）|
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #15932 已创建，远程 CI 通过 | 4 道 Gate 全过；AI Review 摘要已生成、结论『✅ 未发现问题』；**AI Review 监控工具 NameError 导致 Phase 1 空等 30 分钟超时**（见建议-1）|

### 失败与问题

- **1**: 根因=`find_package(KF6DocTools)` 未找到（CMake Warning）, 解决方案=上游把 KF6DocTools 声明为可选，但 ohpcd 制品仓只有 kdoctools/6.19.0，且手册生成依赖 docbook 工具链
- **2**: 根因=消费者用例在归档 `test_package/` 下留下 Qt 状态文件 `.local/state/kcharselectstaterc`, 解决方案=`main()` 在 QApplication 之前调用 `KIconTheme::initTheme()` + `KStyleManager::initStyle()`，二者把状态写入 `$HOME/.local/state/`；而 test_type="explicit" 的 test_package 构建目录就是 `test_package/` 本身，原配方把 `HOME` 指向了那里
- **3**: 根因=已发布 KF6 库相对 DT_NEEDED：`libKF6BookmarksWidgets.so` 记录 `../../bin/libKF6Bookmarks.so`, 解决方案=OHOS 按**符号链接路径**（非 realpath）解析相对条目，多包 KF6 布局下必然失败
- **4**: 根因=上游无测试 → R51 无 ctest 可跑, 解决方案=项目本身 smoke-only
- **5**: 根因=`QFontDatabase: Cannot find font directory .../lib/fonts`（告警）, 解决方案=Qt6 起不再自带字体，offscreen 平台无 fontconfig 时打印告警
- **6**: 根因=配方配置了 `CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH`，但产物 `readelf -d` 里没有 RPATH, 解决方案=CMake 的安装期 RPATH 只**改写**链接期已产出的 RPATH；本次链接行无 `-rpath`（依赖库以绝对路径给出），故无条目可改写

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 6 条
- **引擎命中情况**: 草稿目录 3567 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**:
  1. `scripts/gitcode_pr.py::cmd_monitor_review` 抛 `NameError: name 'unreplied_opinions' is not defined`（约 1066 行，JSON 输出字典引用未定义变量）→ `submit` 的 AI Review 监控 `_call_monitor_review()` 恒返回 None → **每个任务都必然 Phase 1 空等 30 分钟后超时**，即使摘要与检视结论早已生成（本次 10:19:44 生成，10:49 才超时）。知识图谱无对应条目（属框架缺陷而非适配知识）。
  2. CI worker 侧编译资源耗尽：`clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable`（CMake 编译器自检 TryCompile 阶段）→ 同一 commit 在 worker CI-023（#92593）通过、在 CI-034（#92672）失败，属 infra 抖动；另 `[fail] [Errno 2] No such file or directory: 'curl'` 说明部分 worker 无 curl，预下载步骤静默降级。
  3. 本机（HarmonyOS musl）CPython **无法以裸名 spawn 子进程**：`subprocess.run(["git", ...])` 报 `ENOENT`，而 `shutil.which("git")` 正常 → preflight 的 PF0 环境闸必然 fail-closed（本次以 OHC_PREFLIGHT=0 + 说明跳过，并以 argv[0] 绝对化的驱动脚本独立复核 PF1–PF9）。

### AI 检视结果

- **检视阶段到达**: 摘要已生成（atomgit-bot 10:19:44）+ 检视结论已出；因监控工具 NameError，harness 侧停在 Phase 1
- **变更摘要评估**: 摘要内容与配方实际一致（路径 A 无补丁、qtbase 6.11.1 + KF6 6.18.0 闭包、`KF6DocTools` 可选、消费者用例与 HOME/XDG 隔离、DT_NEEDED 归一化均被准确描述），**无需修改的点**；唯一措辞提示：摘要称"14 个 KF6 组件依赖"实为 13 个 KF6 包（Bookmarks/CoreAddons/Crash/I18n/WidgetsAddons/XmlGui/ConfigWidgets/IconThemes + 传递 5 个），属摘要概括而非事实错误
- **检视意见数量**: 1 条（Info 级，结论为『✅ 未发现问题』，0 条需修改）
- **检视意见处理**: 已在讨论串内回复闭环（`handle-review-opinion --action reject --comment-id 193874077`，理由为该条是"未发现问题"的结论性 Info、无需修改，并附 5 轮 W4 独立审计与 CI 证据）；因工具缺陷，闭环校验由人工比对 PR 评论完成

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（JC/L0/L1/L1e/L4/L5 全 pass，Success 1/1；L1e 破坏性反向验证 `bin/ moved away → Negative test confirmed`）
- **远程 CI (PR 校验)**: 通过 —— 构建 #92593（worker CI-023）✅ Conan test_package / L0 / L1 全通过、7 步全绿
- **CI 失败原因**: 一次 **worker infra 抖动**：#92672（worker CI-034）在 CMake 编译器自检阶段报 `posix_spawn failed: Resource temporarily unavailable`（fork 资源耗尽），非配方问题——同一 commit `66b73f4e` 在 CI-023 上通过；已评论 `/rebuild` 重跑。另 worker 无 `curl`，预下载步骤降级为 conan 自带下载（非致命）

### 效率分析

- **HANDOFF 次数**: 2 次 —— ①`finish` 的知识整理 HANDOFF（非阻塞，exit 0）；②`submit` 的 `ai_review_summary_timeout`（工具缺陷导致的假超时）
- **重试次数**: 3 次 —— W3 本地 CI 首轮因仓库内**其他包**的存量隐藏文件（`archives/c/cloog`、`kics`、`libbfio` 等 8 个 `.staging-verified`/`.build-closed`）在 full 模式被 JC1/JC5 拦截（提交后转为 incremental 模式即通过）；远程 CI 重触发 2 次（1 次工具自动 /rebuild + 1 次人工 /rebuild 绕过 infra 抖动）
- **关键瓶颈**: `scripts/gitcode_pr.py::cmd_monitor_review` 的 NameError 使 AI Review 监控**必然空等 30 分钟**（占本次总耗时约 1/4）；其次是完全相同的 KDE/Qt 配方模板在每包重复手写约 300 行（DT_NEEDED 归一化 + runenv）
- **耗时较长的步骤**: ①AI Review Phase 1 空等 30 分钟（工具缺陷）；②每轮 `conan create` 约 2.5 分钟 × 5 轮（初验 + conan-verify + W3 ×3）；③W4 独立审计 5 轮（每轮 8–15 分钟，其中 2 轮因文档与实测口径不符而返工）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 7 个事件（含 1 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-15T08:16:27 | lang_checked | detected=cpp 与任务 cpp 匹配 |
| 2026-10-15T10:19:45 | skeleton_created | pr_created |
| 2026-10-15T10:19:45 | pr_created | PR #15932 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15932 |
| 2026-10-15T10:49:49 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #15932 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 15932 \| 摘要出现后: python3 scripts/ohc-run.py submit kcharselect 26.04.0 --resume |
| 2026-10-15T12:27:18 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-10-15T12:27:18 | skeleton_exists | resume_pr_exists |
| 2026-10-15T12:27:21 | ci_passed | PR #15932 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **[P0·框架缺陷] `scripts/gitcode_pr.py::cmd_monitor_review` NameError**：`unreplied_opinions` 未定义即被 JSON 输出引用（约 1066 行）→ 该子命令恒崩溃 → `submit` 的 `_call_monitor_review()` 恒返回 None → **AI Review 监控对每个任务都必然空等 30 分钟并 emit `ai_review_summary_timeout` 假超时**；正规闭环（Phase 1→5、`_verify_review_closure`）全部失效（后者 fail-open 放行，掩盖了问题）。修复建议：在函数内定义 `unreplied_opinions`（本意应为筛掉"已回复/无问题"的意见），并给该子命令补一条冒烟测试（`selftest` 的 9 用例未覆盖 gitcode_pr.py）。
2. **[P1·门禁自相矛盾] preflight PF9 与 PF8/R38/L0k 互斥**：PF9 以 `len(f.split("/")) < 5` 判定"缺版本目录层"，把 `ARCHIVE-SPEC.md` 与 R38/PF8/L0k **强制要求**的软件级 `archives/<字母>/<包>/{README.md,commands.json,manifest.yaml}` 判为违规 → 所有 CLI 工具包要么删文件（转成 PF8/L0k 真失败），要么 `OHC_PREFLIGHT=0` **整体跳过**闸门（PF1–PF8 的保护同时失效，这是安全损失）。建议 PF9 白名单软件级三文件（与 PF8 同口径），并在 preflight 单测中固化该场景。
3. **[P1·平台适配] PF0 在本平台必然 fail-closed**：HarmonyOS musl 下 CPython 无法以裸名 spawn（`subprocess.run(["git"])` → ENOENT，`shutil.which` 正常）→ `preflight.run_preflight` 入口即 PF0 拦截，AI 只能整体跳过闸门。建议 preflight/gitcode_pr 内部统一用 `shutil.which()` 解析 argv[0]（或走 shell），使闸门在 OHOS 原生 worker 上可用。
4. **[P2] R46 里程碑草稿被上一任务的残留终态吞掉**：`$HOME/ohpcd-ai-worker-result.json` 里仍是上一个任务（kcolorchooser）的 `draft:false` 终态时，本次 `pr_created` 草稿被跳过（日志："终态 result.json 已上报（draft:false），跳过里程碑草稿"）→ 跨任务共用默认路径时，PR 创建的保底回执缺失。建议草稿写入前比对 `pkg`/`ver`（不一致则覆盖），而非只看 `draft` 标志。
5. **[P2] `result --status partial` 强制 `--failed-reason`**：partial 语义是"环未闭、无失败"，却被要求填写失败原因（本次只能写"环未闭…"）→ 建议 partial 用 `--summary` 即可，或新增 `--pending-reason`。

> 另：`finish` [3/10] clean-verify 在本包恒报 `configure 失败 (exit 127)`（init-build 把 CMake 工程判成 autotools，clean-verify 于是找 `./configure`）；非阻塞但会污染日志，建议 clean-verify 依据 conanfile.py 的构建系统分支。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **PR body 应默认对齐仓库模板**：`_generate_pr_body()` 生成的固定骨架与 `.gitcode/PULL_REQUEST_TEMPLATE.md` 的章节/字段并不对齐（缺"适配后测试用例统计""补全测试用例说明"等语义），且对"上游 0 用例"的应用包会渲染出 `单元测试 0 / 通过 0/0 一致` 这类误导表格。建议：①直接以 `.gitcode/PULL_REQUEST_TEMPLATE.md` 为渲染模板；②上游无测试时渲染"N/A（上游确无测试，证据见 MANIFEST.yml）"而非 0/0；③占位符校验与模板字段一一对应（本次为保证零占位符，正文为按模板手写）。
2. **test_package 模板（executable/Qt-KF6 形态）缺失**：本包与 kcolorchooser/kblocks/kteatime 的 test_package/conanfile.py 有 ~300 行几乎相同的内容（DT_NEEDED 相对/绝对归一化 + patchelf 重签名 + link farm + Qt 插件路径 + HOME/XDG 隔离），每个 KDE 包都在复制。建议在 `templates/test_package-executable/` 提供 KF6/Qt6 专用模板（或 `ohc test-pkg-gen --kind qt-kf6-app`），把平台适配收敛为一处。
3. **MANIFEST.yml 模板**：建议把"上游测试清点五项证据"（autotests/、tests/、构建注册、CI 模板、CI 依赖声明）做成固定字段块，减少每包自由发挥（R51 的申报一致性主要靠人肉对齐）。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **AI Review 监控自愈**：工具崩溃/超时后应先做一次"评论直读"降级（`get-comments` + `get-review-comments` 已可用），据评论内容判断 phase，而不是盲等 30 分钟；建议把 `_verify_review_closure` 的 fail-open 改为"直读评论失败才放行"，避免工具缺陷被静默吞掉。
2. **CI infra 抖动自动甄别与重跑**：`posix_spawn failed: Resource temporarily unavailable` / `can't fork` / `fork: retry` 等特征应被 `diagnose` 归类为 `infra_flake` 并自动 `/rebuild`（而非计为配方失败轮次、占用 R42 的 2 轮修复额度）。本次失败点在 CMake 编译器自检，与配方零关系。
3. **worker 环境自检**：本次出现 worker 无 `curl`（预下载降级）、依赖 cache 内 `.so` 被 test() 就地改写（跨任务污染风险）两项；建议 `setup.sh` 增加最小工具自检（curl/zsh/clang/ccache）与 cache 完整性校验，并在 worker 维度聚合"资源耗尽"事件。
4. **result.json 输出位置按任务隔离**：默认 `$HOME/ohpcd-ai-worker-result.json` 在多任务串行复用同一 HOME 时相互覆盖（本任务需 `--force` 才能写入），建议默认带 `pkg-ver` 后缀或按任务 ID 分目录。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

建议新增/提升以下条目（本次已落草稿，均为知识图谱此前零覆盖的模式）：
1. `kcharselect-26.04.0-cmake-install-rpath-not-emitted-rely-on-runenv` —— CMake `CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH` 在"依赖以绝对路径入链"时不产生 `-rpath` → 产物 `.dynamic` 无 RPATH，运行期必须走 Conan runenv；**并修正 kcolorchooser 26.04.0 配方/文档中"通过 DT_RPATH 解析"的错误表述**（该 PR 的先例注释被复制到后续 KDE 配方，错误会扩散）。
2. `kcharselect-26.04.0-test-package-home-xdg-state-file-archive-pollution` —— `test_type="explicit"` 的 test_package 构建目录就是归档 `test_package/`：KF/Qt 应用（KIconTheme/KStyleManager/QSettings）会把状态写进 `$HOME/.local/state/*staterc`，而该路径不在 .gitignore 白名单 → 归档树污染；须把 HOME/XDG_* 指向源码树外。
3. `kcharselect-26.04.0-kf6doctools-optional-upstream-doc-subdir-configured-out` —— ECM/KDE 工程 `find_package(KF6DocTools)` 多为可选，不提供即配置掉 `doc/` 与 `kdoctools_install(po)`，只剩 CMake Warning；勿误判为依赖缺口（与既有 poxml 条目互补）。
4. 建议将第 1 条与既有 `DRAFT-14403-registry-so-no-soname-dynstr-normalize-resign` / `DRAFT-E5xx-registry-so-baked-absolute-needed-symlink` 关联（同一"已发布 KF6 产物不可直接运行"根因族）。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: ohc-agent
- **邮箱**: ohc-agent@local
- **Agent ID**: F6CC
- **生成时间**: 2026-10-15 10:19:45
- **PR 编号**: 15932
- **Git Commit**: 66b73f4e5f
