# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_61fdda1b.md`

---

## 背景

- **软件名称**: adaptivecpp
- **版本**: 25.10.0
- **构建日期**: 2026-10-02
- **构建系统**: cmake
- **上游仓库**: https://github.com/AdaptiveCpp/AdaptiveCpp/archive/refs/tags/v25.10.0.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 11
- **编译依赖**:
- clang/22.1.8
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 制品仓 clang/22.1.8 binary 从 ohpcd 消费，未使用本地缓存绕过 |
| build | 编译构建 | 成功 | 构建系统: cmake；真机 aarch64 原生编译（不设 CMAKE_SYSTEM_NAME） |
| conan-verify | 配方验证 | 通过 | G0/G1/G2/G3/G4 全 PASS，R46 result.json 已上报 |
| finish | 归档收尾 | 完成 | W3 阻塞门禁通过；Step2.5(G0 干净构建)/Step6/Step8 有非阻塞告警 |
| submit | PR提交+AI检视+CI | 进行中 | PR #15063；AI Review: — |

### 失败与问题

1. **W3 本地 CI 曾整轮失败（HANDOFF 1 次）**：`conan create` 在 source 阶段的
   `set_dirty_context_manager` 清理 `s.dirty` 时抛 `FileNotFoundError`，W3 判
   `L1_RESULT=fail: conan create failed`。根因为宿主 safe-delete 钩子与 conan
   清理逻辑冲突，按 SKILL 提示加
   `env -u CODEBUDDY_SAFE_DELETE_BULK_STATE_DIR -u CODEBUDDY_TOOL_CALL_ID -u CODEBUDDY_SAFE_DELETE_BIN_DIR`
   后消失。
2. **CI L5c（SONAME 质量门禁）长期失败，且此前被归因错误**：归档记录把原因
   归为「conan binary 复用导致修正未体现」。**该归因经实测证伪**：
   `conan remove "adaptivecpp/25.10.0*" -c` 后全量重建，L5c 依旧复现。真实根因
   是配方修正正则 `IMPORTED_NO_SONAME\s+TRUE` 与 CMake 真实产物
   `IMPORTED_NO_SONAME_RELEASE "TRUE"`（带配置后缀 + 引号）不匹配，修正函数
   静默空转（重建日志里没有 `corrected ...` 输出）。改为
   `(IMPORTED_NO_SONAME(?:_[A-Za-z0-9]+)?\s+)"?[Tt][Rr][Uu][Ee]"?` 后修复生效，
   W3 由 `L5_RESULT=fail` 变为 `L5_RESULT=pass`。
3. **conan-verify 的 E017 镜像注入需人工确认回滚**：G2 会把 `conandata.yml` 的
   `sources.url` 临时注入 `ghfast.top` 前缀。本轮**执行中被外部 SIGKILL 打断**
   （verify 主进程退出但 finally 未落），残留为 `[gh-proxy.com 镜像, 官方]` 列表形态。
   已在提交前用快照比对还原为官方单值，并由 `git show <commit>:conandata.yml`
   复核 PR 内确实为单值。
4. **W3 的 junk_check 模式退化**：本机 `origin/main` 已前移越过 HEAD，若走
   incremental 模式会扫到主干上无关的运行期标记（`.staging-verified` 等）而误判
   FAIL。按 prdiff 模式提供 `JUNK_PR_DIFF` 后 JC pass（23 个文件，单软件）。
5. **`manifest.yaml` 的 `patches_applied` 为 `[]` 而实际带 11 个补丁**：conan-verify
   自身的 finalize 也报出「补丁数不一致: manifest=0 vs disk=9」。已补齐 11 条清单。
6. ~~**上游测试未运行**（非失败，属能力边界）：环境缺 Catch2/GoogleTest，且
   `tests/` 大量依赖 CUDA/ROCm/HIP 与真实 GPU，无可运行 CPU 子集。~~
   **该结论已被推翻（本次会话复核）**：上游框架是 **Boost.Test**（不是 Catch2/gtest），
   且 `boost/1.84.0` 在本 profile 下**可从 ohpcd 直接消费**；`tests/CMakeLists.txt` 把
   `pstl_tests`/`pcuda_tests` 放在 `WITH_PSTL_TESTS` 与 CUDA/ROCm 开关之后，**默认目标集
   本身就是可跑的 CPU 子集**。实际已在真机跑通：`sycl_tests` 335 用例（334 通过 / 1 失败）、
   `rt_tests` 2、`device_compilation_tests` 8，合计 **345 用例 / 344 通过**。
   教训与「未运行」判定同源：**下"不可行"结论前必须先实测一次**，而不是依据静态特征推断。

### 知识图谱使用情况

- **引用知识条目**: E017（GitHub 下载不稳 → 镜像/重试）、E092（CMake 不识别
  HarmonyOS 目标平台）、E011（鸿蒙共享卷 umask 限制）
- **新增知识草稿**: 4 条
- **引擎命中情况**: 草稿目录 2997 条；W5 报 E219/E253/E305 存在 `root_cause` 空字段（历史条目，非本次）
- **测试统计**: 流水线自动统计为 总计 0, 通过 0, 失败 0, 跳过 0（未接入本包的
  test_package 断言计数与上游 Boost.Test 输出）；**人工核实**：
  ① 上游套件（CPU 子集，以本包产物消费运行）**345 用例 / 344 通过 / 1 失败**——
  `sycl_tests` 335（1 项失败为 CPU 设备无 profiling 时间戳）、`rt_tests` 2、`device_compilation_tests` 8；
  ② 新增消费者用例 3 个 / **299** 条判定（256 SYCL 逐元素 + 3 CLI 冒烟 + 40 鸿蒙平台/补丁回归），真机全部通过。
  （早前修订曾写「上游未运行（0/0）」与 283 条，均已更正。）
- **未覆盖的错误模式**: 见「知识图谱覆盖」

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: —
- **检视意见数量**: —
- **检视意见处理**: —

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（L0/L1/L2/L5 pass，JC/KC pass，Build Summary 1/1 100%）
- **远程 CI (PR 校验)**: 进行中（PR #15063，`/rebuild` 已触发，ohpcd-robot 已回执）
- **CI 失败原因**: 无（远程结果待回）

### 效率分析

- **HANDOFF 次数**: 1（`w3_local_ci_failed`，Step5）
- **重试次数**: 全量 `conan create` 3 次（① 复现 L5c ② 验证正则修复 ③ finish/verify 内部各一次），
  另有 W3 重跑 1 次、conan-verify 重跑 1 次
- **关键瓶颈**: 单次 `conan create` 约 8 分钟（含包内 libomp 的 LLVM 22 源码全量构建）；
  L5c 的错误归因导致多花一轮清缓存全量重建才定位到「正则永不命中」这一根因
- **耗时较长的步骤**: conan create（约 8min/次）、W3 本地 CI 模拟（约 10min）、
  conan-verify G2 干净构建（约 8min）

---

## 建议

### SKILL 设计改进

1. **门禁失败给「已修复但门禁仍红」时，应提示检查修正函数是否真的生效**，而不是
   一律归因 conan binary 复用。本轮 `_fix_exported_no_soname` 属于「有修正代码、
   有重建、门禁仍红」的典型形态，若 L5c 报错旁直接提示「检查修正函数的输出是否
   出现在构建日志中」，可省掉一整轮清缓存重建。
2. **W3 的 G0/Step2.5 应在非真机（无 tarball 缓存）时给出更明确的跳过语义**。
   本轮 Step 3/10 报 `G0: 找不到原始 tarball` 后仅 WARN 继续，容易与真实失败混淆。
3. **`patches_applied` 应在 close-archive/finalize 阶段自动回填**，而非留给人工。
   本轮 finalize 自己报出「manifest=0 vs disk=9」却不自动修，属可自动化残留。

### 模板改进

1. **积分赛 PR 模板的「上游用例数 / 与上游对比」应支持「跑的是子集」与「未运行」两种显式态**。
   当前模板只有 `[N]` 与自由文本：本轮先是被迫写「上游未运行」（且因同一列的措辞被误读为
   「上游无测试」），复核后实际跑的是**默认目标集的 CPU 子集**（345/544 用例），仍无标准写法。
   建议增加「运行范围」列（全量 / CPU 子集 / 未运行）并要求附不可运行目标与原因，避免
   用 0 或含糊措辞表达。
2. **模板缺少「改进/修复既有配方缺陷」的位置**。本次真正阻塞提交的是一个既有配方
   修正函数的缺陷（正则不匹配），属配方层修复而非平台适配，无处安放，只能写在
   「遇到的问题与解决方案」里。
3. **「上游测试未运行」不应作为默认结论**。本轮初版把上游套件判为「不可运行（缺
   Catch2/GoogleTest + 依赖 GPU）」，但实测：框架是 Boost.Test、`boost/1.84.0` 可从 ohpcd
   直接消费、`pstl/pcuda` 本就在默认目标集之外——即**默认目标集自身就是可跑的 CPU 子集**。
   若模板把「未运行」写成可勾选的一档，容易固化这类未经实测的结论；建议在勾选「未运行」时
   强制要求附一条**实际尝试过的命令与原始输出**。

### 自动化补全

1. **conandata.yml 镜像注入的崩溃恢复应扩展为「进程级签名校验」**：当前
   `_recover_ghfast_bak` 依赖 `.bak` 文件存在，本轮被 SIGKILL 后残留的是
   `[gh-proxy.com, 官方]` 列表形态（**不是 ghfast.top**，与守卫条件不符），
   陈旧守卫因此不认识该形态。建议守卫改为「url 是否为 list 或含任一已知镜像前缀」。
2. **提交前自动比对 `conandata.yml` 与「官方单值」快照**并阻断 commit。本轮是
   靠人工记忆 + 快照才拦住的，属高风险重复坑（已连续两轮踩到）。
3. **W3 的 junk_check 应在 `origin/main` 前移越过 HEAD 时自动切换到 prdiff 模式**
   （本地只要存在待提交 diff 即可生成 pr.diff），而不是退化到 full 模式扫全仓。

### 知识图谱覆盖

建议新增/强化以下条目的沉淀：

1. **「CMake 导出属性带配置后缀」模式**：`IMPORTED_NO_SONAME` 实际写为
   `IMPORTED_NO_SONAME_<CONFIG> "TRUE"`；任何按属性名做文本替换的配方修正都必须
   容忍配置后缀与引号。这是 L5c 门禁的通用坑，不止 adaptivecpp。
2. **「修正函数静默空转」反模式**：配方内基于正则的产物修正应把「命中数」输出到
   日志（本轮 `fixed` 非空才输出，恰好使空转静默）。建议作为配方审查清单项。
3. **OHOS(musl) 上 SYCL/OpenMP 多线程退出死锁**：libomp worker teardown 与
   AdaptiveCpp 退出清理互等（纯 OpenMP 与单线程 SYCL 正常）。目前只有本包 notes.md
   记录，建议提升为正式 E-entry，供后续 SYCL/OpenMP 类适配复用。
4. **OHOS 无 libomptarget，可用 host 语义 shim 替代**（device 指针即 host 指针的
   CPU-only 场景），含「dlopen kernel 库前预载使符号进入全局集合」的手法。

---

## 作者

- **姓名**: Yunan0718
- **邮箱**: 2801558242@qq.com
- **Agent ID**: FD59
- **生成时间**: 2026-10-08 21:38:03
- **PR 编号**: #15063
- **Git Commit**: e3d178be3a
