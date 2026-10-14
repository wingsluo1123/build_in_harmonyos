# SKILL 执行流程反馈报告

> 本报告记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_ac502d15.md`

---

## 背景

- **软件名称**: tm-align
- **版本**: 20190822
- **构建日期**: 2026-10-08
- **构建系统**: 无（4 个源文件 `TMalign.cpp/.f`、`TMscore.cpp/.f`，配方内直接调用编译器；自动采集渲染为 `{BUILD_SYSTEM}`，已按实修正）
- **上游仓库**: Zhang Lab（University of Michigan）TM-align，<https://zhanggroup.org/TM-align/>（官方站只发布不带版本号的最新文件；20190822 取自 Debian pool 的 `+dfsg` orig 包）
- **适配路径**: 路径 B（知识库扩展：1 份知识草稿 E560）；源码补丁 0 个
- **补丁数量**: 0
- **编译依赖**: 无 Conan 依赖（C++ 标准库 + libm）
- **最终状态**: built（W3 本地 `conan create` 通过）

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| lang-preflight | 语言预检 | 通过 | 检测器判 `cpp`（cpp 2 个，主体 100%，build_system=none）；tarball 另含 Fortran 版 `*.f`，本包只构建 C++ 版 |
| init-build | 源码下载/解压 | 完成 | `.work` 与 `.orig` 为硬链接，已按 E543 处理（无补丁，未写回源码） |
| build | 编译构建 | 成功 | NDK clang++ `-O3 -ffast-math`，零补丁，`TMalign` / `TMscore` 均产出 aarch64 ELF |
| conan-verify | 配方验证 | 通过 | 首次因 G1 缺 `export_sources()` / 补丁应用调用失败，补齐后 G1-G4 全过 |
| finish | 归档收尾 | 部分告警 | W3 通过；`step5b`（G0 干净构建）与 `step8`（gen_summary）为框架侧告警，见下 |
| submit | PR 提交 + AI 检视 + CI | 以 PR 页面为准 | 提交后由用户手动复查 |

### 失败与问题

1. **`get(strip_root=True)` 对根目录平铺的压缩包抛错**：Debian `+dfsg` 包根目录直接是 4 个源文件，`untargz` 报 `Can't untar a tgz containing files in the root with strip_root enabled`（已本地复现）。配方改为不传 `strip_root`。已沉淀草稿 E560。
2. **`conan-init` 对无构建系统包的骨架不适用**：回退为 autotools，生成 `package_type = "library"`、`cpp_info.libs = ["tm-align"]`、`configure/make` 流程；此包只产出命令行工具。手工改写为直接编译 + `package_type=application`。
3. **`conan-verify` G1 要求 `export_sources()` 与补丁应用调用**：零补丁包也必须写（已补，无副作用）。
4. **finish `step5b`（G0 clean-verify）失败**：`tar xf` 在 root 下按 tarball 内记录的 uid/gid（1921090/44400）还原属主，报 `无法将所有权改为 ... 无效的参数`，返回非 0。与适配无关。
5. **finish `step8`（gen_summary）失败**：`'str' object has no attribute 'append'`，非致命。
6. **本机无 binfmt**：测试驱动 `fork/exec` 子进程（aarch64 ELF）在 qemu-user 下直接失败（rc 127）。测试驱动增加可选环境变量 `TM_TEST_RUNNER=qemu-aarch64` 前缀解决；交付产物在 aarch64 主机上不设该变量。
7. **PF7 命中 Debian 源**：官方站无版本化发布物，任务书明确指定 Debian URL；按官方托管例外在 PR 正文登记（同形态先例 `archives/o/oggfwd`）。

### 知识图谱使用情况

- **引用知识条目**: E430（binfmt 无 loader → 静态重链 + qemu 验证，沿用其做法）、E543（`.work`/`.orig` 硬链接，本包无补丁未触发）、E544（动态 OHOS 产物本机跑不起来）
- **新增知识草稿**: E560-draft-D148（压缩包根目录平铺 → `strip_root` 失败；顺带记录无构建系统包的骨架误判）
- **引擎命中情况**: `engine` 对 strip_root / 根目录文件签名无命中；`draft-review` verdict=create，最相近 E378，分数 0.12；关键词检索 `files in the root` / `more than 1 folder in the root` 在 `graph` / `drafts` / `doc` 命中 0 条
- **测试统计**: 上游测试 N=0、N′=0（包内无 tests/、无构建系统）；`test_package` 7 个场景 17 项断言，qemu-aarch64 静态重链副本本地实跑 17/17 通过
- **未覆盖的错误模式**: 无构建系统的多文件源码包在 `conan-init` 中被判成 autotools library（见建议）

### AI 检视结果

- **检视阶段到达**: 提交后由用户手动复查，本报告入仓时尚未开始
- **变更摘要评估**: 待机器人产出后评估
- **检视意见数量**: 待检视完成后统计
- **检视意见处理**: 待检视完成后处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`.ci-result.json` exit_code=0，日志 sha256 已记录）
- **远程 CI (PR 校验)**: 提交后手动触发，结果待复查
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（finish 末尾「知识整理」交接块；conan-verify G1 失败为直接报错，无 HANDOFF）
- **重试次数**: conan-verify 重跑 1 次（补 G1 缺失项）；finish 因误加 `--resume` 参数被拒后直接重跑 1 次
- **关键瓶颈**: 无构建系统包的骨架需整体手写；测试驱动的本地 qemu 验证需要先弄清无 binfmt 的限制
- **耗时较长的步骤**: 本地 `conan create` 两次（各约半分钟，包很小）；其余为人工设计消费者用例与取证

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-08T23:39:54 | skeleton_created | result_partial |
| 2026-10-08T23:39:54 | lang_checked | detected=cpp 与任务 cpp 匹配 |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

- `scripts/ohc/clean_verify.py:86-89` 的 `subprocess.run(["tar","xf",...])` 在 root 下会还原 tarball 内的 uid/gid，遇到属主非法的 orig 包（Debian 重打包常见）必然返回 1 并把 G0 判失败；建议加 `--no-same-owner`（或 `-o`）。G0 本身是非阻塞，但失败信息会误导新人去排查源码。
- `ohc finish` 的 argparse 不接受 `--resume`（报 `unrecognized arguments: --resume`），而 `init-build` / `submit` / `feedback` 都支持；各子命令的续跑语义不一致，建议统一，或在 `finish -h` 与 HANDOFF 里明确「finish 直接重跑即可」。

### 模板改进

- `scripts/ohc/conan_recipe.py:169-173` 构建系统检测无任何构建文件时默认回退 `"autotools"`（`conan_recipe.py:23` 的映射）。v12.21 已有 `conanfile-headeronly.py.tmpl`（`conan_recipe.py:26`），建议在「无构建文件但存在 `.c/.cpp/.f` 源码」时给出新模板 `conanfile-nobuild-tool.py.tmpl`：`package_type=application`、`build()` 用 `self.conf.get("tools.build:compiler_executables", ...)` 直接编译、`bindirs=["bin"]`，并默认不写 `strip_root=True`。
- `conan-init` 对 `test_package` 的 CLI 骨架（`test.c` + 链接 `tm-align::tm-align`）对 `application` 包无意义；建议当 `package_type=application` 时直接套 `templates/test_package-executable`，并提示补「消费者编译 + 运行」用例（rule12）。
- 版本级 `manifest.yaml` 模板里 `{software}` / `{BUILD_SYSTEM}` 占位符未被填充，`tar_format` 默认 `tar.gz`、`status` 默认 `published`，容易被带进 PR；建议 `init-archive` 渲染时用真实值。

### 自动化补全

- `gen_summary` 失败（`'str' object has no attribute 'append'`）出现在 `finish` step8；建议在 `scripts/gen_summary.py` 对该字段做类型归一，避免每次都落告警。
- `feedback` 自动采集：构建系统渲染成 `{BUILD_SYSTEM}`、上游仓库「未知」、测试统计取到 0、适配路径误判为路径 A；本次均手工修正。建议从 `conan-init` 结果与 `test_package/MANIFEST.yml` 回填构建系统与测试统计。
- `finish` 的 submit 就绪预检仍要求 `packaging/`、`test-report.md`、`.staging-verified`，与 ARCHIVE-SPEC v2.0 不符；建议改为只检查 v2.0 规定的文件。

### 知识图谱覆盖

- 新增草稿 E560：Debian `+dfsg` / 重打包 orig 压缩包根目录平铺导致 `get(strip_root=True)` 失败；建议主编 promote。
- 建议补一条「无构建系统的多文件源码包」专题：直接编译的配方骨架、`package_type=application`、双语言（Fortran + C++）压缩包选 C++ 版以避免 gfortran 依赖。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 683A
- **生成时间**: 2026-10-08 23:39:54
- **PR 编号**: 以 PR 页面为准（本文件在建 PR 前入仓）
- **Git Commit**: 见 PR 页面
