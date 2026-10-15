# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_bdc007be.md`

---

## 背景

- **软件名称**: vector-blf
- **版本**: 2.4.2
- **构建日期**: 2026-10-15
- **构建系统**: cmake
- **上游仓库**: https://github.com/Technica-Engineering/vector_blf/archive/refs/tags/v2.4.2.tar.gz
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
- zlib/1.3.2.1
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: cmake |
| conan-verify | 配方验证 | 通过 | G0-G4 PASS（G2 conan create + test_package 全通过）；L2/L4/L5 因 cache path 查询未带 `@ohpcd/stable` 被整体跳过 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #15899, CI 通过 | AI Review: Phase 1 (等待摘要) |
| 复审 rule12 | 补鸿蒙特有测试 | 完成 | 新增端到端消费者用例 + 独立实现交叉校验 + ELF 加载探针；W3 复验全绿 |

### 失败与问题

- **1**: 根因=`find_package(Doxygen REQUIRED)` 失败（环境无 doxygen）, 解决方案=`OPTION_RUN_DOXYGEN` 上游默认 **ON**，还会连带 `find_package(Graphviz)`
- **2**: 根因=链接期 `cannot open Scrt1.o` / 找不到 `-lc`, 解决方案=手工编译时误用了 PATH 里的 conan clang 包（`~/usr/local/bin/clang` → clang **22.1.8**，host 版、无 sysroot；与正文使用的 OHOS SDK clang **15.0.4** 是两个不同工具链）
- **3**: 根因=`Vector/BLF/config.h not found`, 解决方案=`config.h` / `vector_blf_export.h` 是 CMake `configure_file` + `generate_export_header` 的**生成头**，只存在于 build 树/安装树
- **4**: 根因=产物没有 `libVector_BLF.so.2` / SONAME, 解决方案=CMake 把 clang 默认三元组 `aarch64-unknown-linux-ohos` 识别为系统 `HarmonyOS`（无 `Platform/HarmonyOS.cmake`），该平台无 soname 支持 ⇒ 上游 `SOVERSION 2`/`VERSION 2.4.2` 不生效
- **5**: 根因=跑上游测试时 `pthread_setcancelstate` 未声明, 解决方案=OHOS musl 无该符号，Boost 1.84 头文件默认调用它
- **6**: 根因=⚠️ **首版配方静默链上宿主 zlib-ng**：`conan create` 产出的 `libVector_BLF.so` 出现 `NEEDED libz.so.1`（指向 `~/.harmonybrew/lib/libz.so.1.3.1.zlib-ng`），而手工编译时链的是 Conan 的静态 `libz.a`, 解决方案=配方 `generate()` 只调了 `CMakeToolchain(self).generate()`，**漏调 `CMakeDeps(self).generate()`** ⇒ build 目录里没有 `ZLIBConfig.cmake`；上游又用 `find_package(ZLIB)` + 旧式 `${ZLIB_LIBRARIES}`，于是退到 CMake 内置 `FindZLIB` 模块模式，命中了构建机上的同名库

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 5 条
- **引擎命中情况**: 草稿目录 3517 条
- **测试统计**: 上游 126/126 + test_package 消费者用例 2/2（合计 128，通过 128、失败 0、跳过 0）
  - 其中**鸿蒙特有测试 1 项**（复审 rule12 后补）：`test_ohos_e2e` 端到端消费者用例（6000 报文 → $TMPDIR/HMDFS 写盘 → 4 个 zlib 压缩容器 → 两遍读回 → 14 checks/0 失败），配 `ref_blf_parser` 独立实现（不链接本库）与 `test_compare` 的 6 条强制不变量（23 共享字段 0 不一致），另有 `ohos_dlopen_probe` 在新进程验证 ELF 可加载性
- **未覆盖的错误模式**（本次新增/建议补充）:
  1. **配方 `generate()` 漏调 `CMakeDeps`** ⇒ build 目录无 `<Pkg>Config.cmake`，上游 `find_package(ZLIB)` + 旧式 `${ZLIB_LIBRARIES}` 退回 CMake 内置 Find 模块，静默链上构建机的同名共享库（本机为 `~/.harmonybrew/lib` 的 zlib-ng），产物出现 `NEEDED libz.so.1`：既违反 R26，又让包依赖 CI 上不存在的宿主路径。**已提草稿 E550**（含四类验证命令）。手工用 `conan install -g CMakeDeps` 验证时不复现，只有 `conan create` 暴露。
  2. **CI worker `make: Resource temporarily unavailable`（EAGAIN）**：CMake 编译器探测阶段 `make` 无法 fork，被 CI 归类为"编译失败/CMake 配置失败"，实为 worker 进程资源耗尽，与配方无关（第 1 次 CI 运行即此因，20.6s 即失败）。
  3. **源下载双通道同时失效**：CI 自动注入的 `gh-proxy.com` 镜像返回 `Access to this resource is forbidden`，同时 worker 直连 `github.com` `ConnectTimeoutError` → `source()` 失败。需知识化"CI 侧镜像列表可能整体失效 + R41 止损口径"的处置流程。

### AI 检视结果

- **检视阶段到达**: Phase 1 (等待摘要)
- **变更摘要评估**: 摘要内容与实际改动一致（配方/CMakeDeps/关闭 Doxygen/test_package/元数据/E550 草稿五项均如实描述），无需修改。
- **检视意见数量**: 0 条（仅有 atomgit-bot 的"变更摘要"与"AI 代码检视正在进行中"两条，无任何检视意见）
- **检视意见处理**: 无需处理。⚠️ 工具侧 Phase 1 轮询从 02:31 到 03:01 持续报"获取检视状态失败，重试"并最终以 `ai_review_summary_timeout` HANDOFF 退出——但变更摘要 02:31:28 就已生成；人工用 `get-comments` 核对确认检视已完成且无意见。建议该 API 失败时回退到评论解析（见建议-自动化补全）。

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 通过 (PR 校验)
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 5 次（self_check_failed:packaging_present ×1、pr_creation_failed:PF0 ×1、pr_creation_failed:PF9 ×1、ai_review_summary_timeout ×1、result_invalid 需 --force ×1）
- **重试次数**: submit 共执行 4 次；CI 共触发 3 次（第 1 次 worker 资源耗尽、第 2 次源下载超时、第 3 次通过）；W4 独立审计共 4 轮（前 3 轮各发现并修复 1 个真实问题）
- **关键瓶颈**: ① submit 三处环境/门禁问题（`packaging_present` 要求已废弃的 `packaging/*.tar.gz`；PF0 在本机 Python 上无法解析裸命令名 `git`；PF9 把 ARCHIVE-SPEC 允许的软件级 `README.md`/`manifest.yaml` 判为缺版本目录层）——合计占用约 25 分钟；② AI Review 状态轮询 API 全程失败导致空等 30 分钟；③ CI worker 抖动（资源耗尽 + 源下载超时）导致 2 次无效 CI 轮次；④ 机器被多个并行任务共享（load average ≈45），编译与 conan create 明显变慢
- **耗时较长的步骤**:
  1. 上游 126 项 Boost.Test 真机编译（header-only Boost.Test 入口，每个 TU 约 50s，-j3~6，机器高负载下约 70 分钟）+ 运行 6.6s
  2. `conan create` 共 4 次（conan-verify ×2 + finish W3 + CI 无关），每次约 8-10 分钟
  3. `submit` AI Review 空等 30 分钟（API 失效）
  4. W4 独立审计 4 轮（每轮 3-5 分钟，含一次真实事实性错误修正）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 6 个事件（含 4 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-15T02:08:38 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit vector-blf 2.4.2 |
| 2026-10-15T02:14:36 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/vector-blf-2.4.2 --target main --title 'feat(vector-blf): 2.4.2 适配完成' |
| 2026-10-15T02:18:03 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/vector-blf-2.4.2 --target main --title 'feat(vector-blf): 2.4.2 适配完成' |
| 2026-10-15T02:31:29 | skeleton_created | pr_created |
| 2026-10-15T02:31:29 | pr_created | PR #15899 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15899 |
| 2026-10-15T03:01:33 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #15899 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 15899 \| 摘要出现后: python3 scripts/ohc-run.py submit vector-blf 2.4.2 --resume |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`_check_packaging_present` 与 ARCHIVE-SPEC v3.0 直接冲突，硬拦所有 v3.0 配方**：`submit` 自检要求 `packaging/*.tar.gz` 非空，而 `knowledge/ARCHIVE-SPEC.md` 第 7 行明确"packaging/ 目录废弃（Conan 体系替代手动 tar.gz 打包）"、第 242-245 行要求删除 `packaging/*.tar.gz`。该检查由 `d3c1f8cf84`（2026-10-14 23:43 合并 `feat/wumpus-1.12`）引入 main，本任务实测 `self_check_failed: ['packaging_present']`，另有 2 份历史 feedback（`SKILL_FEEDBACK_009f9300.md`、`SKILL_FEEDBACK_00df57a8.md`）报过同一问题。**建议**：存在 `conanfile.py` 时跳过该检查（或改为"conan create 产物存在"），并清理该函数。
2. **PF9 路径闸误拦软件级归档文件**：PF9 要求 `archives/` 下所有变更路径 ≥5 段（`archives/<字母>/<包>/<版本>/<文件>`），于是 ARCHIVE-SPEC 允许、且近期多个已合并归档（typeshare/synscan/boost-1.85）实际存在的软件级 `README.md`/`manifest.yaml` 被判违规，只能删除或 `--no-preflight`。**建议**：对软件级白名单文件（`README.md`/`manifest.yaml`/`commands.json`）豁免。
3. **PF0 在 OHOS Python 上必失败（裸命令名无法解析）**：本机 Python 3.12 的 `posix_spawnp` 对**所有裸命令名**（git/ls/sh/cmake/python3…）均抛 `FileNotFoundError`，只有绝对路径或 `shell=True` 可用；`scripts/ohc/preflight.py` 第 75/320/578 行用裸 `"git"`，导致每次 `create-pr` 都以 `PF0 环境闸: preflight 执行异常` 收场（与 SKILL v12.17 记录的"3 份反馈被迫 --no-preflight"同源）。**建议**：preflight 用 `shutil.which`/`GIT_BIN` 解析绝对路径（`pre_pr_audit.py` 已有 `_find_git()` 可复用）。
4. **W3/CI 侧 mirror 注入不回滚，会把工作区 conandata.yml 写脏**：`ci/conan/build_and_test.sh` 的 Mirror fallback 会把 `conandata.yml` 的 url 改写成 `gh-proxy.com` 列表且**不还原**，本任务 finish 后 conandata.yml 即被写脏（提交前需人工 `git checkout` 还原），否则直接触发 PF7/R39 违规。**建议**：与 `conan_verify.py` 一样加 trap/finally 还原（并顺带修 `conan_verify.py` 只恢复内容、不 unlink `.ghfast-bak` 的问题——本任务两次 verify 后都残留 `.bak`）。
5. **AI Review 监控只认状态 API，失败时白等 30 分钟**：本机 `submit` Phase 1 全程 `获取检视状态失败，重试`，最终 `ai_review_summary_timeout` HANDOFF，而变更摘要在 PR 创建后 1 秒即生成、且全程零检视意见。**建议**：状态 API 连续失败 N 次后回退为解析 `get-comments`（摘要/意见都从评论里可判），避免把"API 抖动"升级成"评审超时"。
6. **`finish` 的 G0 clean-verify 假定 autotools**：CMake 项目上 `./configure` 不存在 → exit 127 并 emit 一整块 G0 HANDOFF（虽然非阻塞，但误导）。**建议**：按 manifest `build.system` 分派（cmake→`cmake -S . -B build`）。
7. **conan-verify 的 L2/L4/L5 实际未执行**：报告里三项都是"⏭️ 跳过（无 cache 路径）/⚠️ 无法找到程序包 ID"，原因是查缓存用的引用没有 `@ohpcd/stable`（实际创建的是 `vector-blf/2.4.2@ohpcd/stable`）。安全扫描（NX/PIE/RELRO）与产物基线因此全部空转——本任务改为人工 `readelf/llvm-nm` 复核。**建议**：cache path 查询复用 `--user/--channel`。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **`templates/conanfile-cmake.py.tmpl` 缺 `CMakeDeps`**：模板只在 `generate()` 里生成 `CMakeToolchain`。凡上游用 `find_package()` 的 CMake 项目，这会导致 build 目录没有 `<Pkg>Config.cmake`，`find_package` 退回 CMake 内置 Find 模块并可能静默链上宿主同名库（本任务实测 NEEDED libz.so.1，见 E550）。**建议**：模板默认写出 `CMakeDeps(self).generate()`，并在注释里点明原因。
2. **`templates/test_package/conanfile.py.tmpl` 的 `test()` 是潜在空壳**：模板只调 `cmake.test()`，真实的 `self.run(...)` 是注释行。CI L0d 用 `grep "self\.run"` 判空壳，注释行正好能被 grep 命中，于是"检查通过但语义仍是空壳"。**建议**：模板直接给出可用的真实写法（`self.run(f'"{binary}"', env="conanrun")`），与 L0d 口径一致。
3. **PR body 模板的上游用例数取值**：`_generate_pr_body` 从 `test-report.md` 摘要表取"总测试数"，容易把"上游 N + 消费者 M"的合计当成"上游用例数"。本次改为手工撰写 `reports/pr-body.md`（工具在无未填占位符时保留人工版本），建议模板区分"上游用例数/适配后新增用例数"两个字段。
4. **MANIFEST.yml 模板的 `upstream_tests[].description` 易写成失实断言**：本任务 W4 审计两次命中（"no .blf fixture needed"对实际读取固定装置的用例不成立；上游 `#if 0` 死代码里的路径也被当成实际读取）。**建议**：模板给出"可核验措辞"指引（引用的固定装置是否随源码发布/是否位于 `#if 0`），避免审计判 P1/P2。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **源 URL 抓取的镜像策略需更新**：本任务第 2 次 CI 失败于"`gh-proxy.com` 返回 forbidden + github.com 连接超时"，而 CI 侧 `curl` 也不存在（`No such file or directory: 'curl'`，预下载全废，只能靠 conan 自身重试）。**建议**：① 预下载改用 Python（`urllib`）而非外部 curl；② 维护一份可用镜像列表并支持逐个回退；③ 对"连续 2 次双通道失败"的源，自动按 R41 上报 `dependency_missing` 而不是继续耗轮次。
2. **W4 审计输入必须已提交，而提交发生在 submit 内**：`pre_pr_audit.py generate` 用 `git diff origin/main...HEAD` 取变更，因此必须先手工 commit 才能审计；同时 commit 又让 `submit` 的自检从"full"变成"incremental"模式（否则 JC 会扫全仓、被 `archives/c/cloog` 等他人遗留的 `.staging-verified` 误拦——本任务实测）。**建议**：SKILL 明确把"先 commit 再 finish/submit"写成标准顺序，或让 generate 支持未提交变更（`git status`）。
3. **`packaging/` 产物可由 conan 产物自动生成**：既然 submit 自检要 `packaging/*.tar.gz`，建议 `finish`/`close-archive` 直接用 `conan cache path <ref>@<user>/<channel>` 打包成 `<pkg>-<ver>-ohos-aarch64.tar.gz`（gitignored、不入 PR），消除"人工 tar"这一步。
4. **`gen_summary` 崩溃**：Step 8 `gen_summary` 报 `'str' object has no attribute 'append'`（非致命但每次都失败）。**建议**：修掉该异常。
5. **本地 CI 模拟与真实 CI 的失败归类**：CI 把 worker 资源耗尽（`make: Resource temporarily unavailable`）归类为"编译失败/CMake 配置失败"，会诱导 AI 去改配方。**建议**：CI 侧识别 EAGAIN/"Resource temporarily unavailable" 并标记为 infra 重试（自动重跑而非报编译失败）。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **已提草稿 E550**（本次核心沉淀）：Conan 配方 `generate()` 漏调 `CMakeDeps` ⇒ `find_package` 回退 Find 模块 ⇒ 静默链上宿主同名共享库（R26 违规 + 非封闭构建）。含四类可执行验证（readelf NEEDED / llvm-nm 静态符号 / generators 下 Config.cmake / 干净 conan create），并列出"为什么手工验证不复现"。
2. **建议新增条目（基础设施类，建议给独立 severity/分类以便与配方缺陷区分）**：
   - **CI worker 进程资源耗尽**：`make: <path>/make: Resource temporarily unavailable` / `Error 127` 出现在 CMake 编译器探测阶段 ⇒ 判定 infra、自动重跑，**不要**按"CMake 平台不兼容"改配方。
   - **源下载双通道失效**：`gh-proxy.com ... Access to this resource is forbidden` + `ConnectTimeoutError(host='github.com')` ⇒ 按 R41 止损口径（重试上限、`dependency_missing` 上报格式、证据行模板）。
   - **OHOS Python 裸命令名不可解析**：`subprocess.run(["git", ...])` ⇒ `FileNotFoundError: 'git'`（绝对路径/`shell=True` 正常）⇒ 框架脚本必须解析绝对路径。
3. **建议新增条目（review 规则类）**：`rule12 鸿蒙特有测试` 的完整口径——不仅"不能为 0"，且必须是**完整端到端消费者用例**（构造输入→真实执行→产出结果→校验内容），纯断言集合会被判 FAIL；且平台特有性必须**可伪证**（本次踩点：在已链接被测库的二进制里 `dlopen` 是同义反复，因为动态链接在 `main()` 前已映射；容器数/压缩方法等断言若只写在私有键里、比较器又忽略私有键，则等于没有断言）。建议把该条与既有草稿 `DRAFT-genht-1.1.3-rule12-needs-e2e-consumer-case` 合并提升。
4. **可关联既有条目**：E092（CMake 在 OHOS 上把系统名识别为 HarmonyOS，本任务 G0 命中）与 E550 是同一适配中的平台类+配方类组合。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: ohc-agent
- **邮箱**: ohc-agent@local
- **Agent ID**: 4658
- **生成时间**: 2026-10-15 02:31:29
- **PR 编号**: 15899
- **Git Commit**: aeff9d7dc4
