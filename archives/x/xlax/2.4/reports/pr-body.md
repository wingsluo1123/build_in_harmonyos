- **三方库名称**：xlax
- **上游版本**：2.4
- **上游仓库地址**：https://hea-www.harvard.edu/~fine/Tech/xlax.html
- **适配路径**：路径 A（基础适配）
- **使用知识库**：ohos-conan-gate-env、ohos-conan-finish-local-env、ohos-conan-fork-pr-submit

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 tarball 共 11 个文件，无 `test/`、`tests/` 目录，无 `check`/`test` 构建目标 |
| 集成测试 | 0 | 无 CI 配置、无测试框架依赖（1992 年 Imake 工程） |
| 其他测试 | 0 | `mkxlax` 是生成 `~/.mkxlax` 配置的辅助脚本，非测试入口 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 23 | 新增 | `test_package/test_xlax.sh` 11 条断言 + `xlax --selftest` 12 项程序化检查 |
| **合计** | **23** | **+23** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游不存在测试用例文件，故无「对测试用例的修改」。本包三个补丁改动的都是产品源码
> `xlax.c` / `xlax.h` / `vroot.h`（编译器警告、ANSI 原型、无头自检入口），未新增或修改任何测试文件。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：包内容完整性（4 条）、命令行入口（1 条）、无头自检与 Xaw 符号解析（2 条）、
>   无 X server 时的错误路径（1 条）、ELF 事实（3 条），加程序内 12 项自检，共 23 条断言。
> - **补全原因**：上游为 1992 年 Harvard 的 Imake 图形示例工程，从未提供测试套件；HarmonyOS PC
>   无 X server，无法用「启动 GUI 观察」的方式验收，故新增不依赖显示的 `--version` / `--selftest` 入口来落地可执行验证。
> - **新增测试文件清单**：
>   1. `2.4/test_package/test_xlax.sh` — 消费者侧 shell 断言集，11 条断言，`set -euo pipefail`
>   2. `2.4/test_package/conanfile.py` — `test_type="explicit"`，用 `VirtualRunEnv` 提供运行期库路径后执行上述脚本
>   3. `2.4/test_package/MANIFEST.yml` — 上游测试缺失取证（5 条）与断言计数声明
>   4. `2.4/patches/0003-headless-selftest.patch` — 为产品增加 `--selftest` 入口（96 行新增），供测试与运维自检

## 验证结果

- 编译状态：通过（`conan create` RC=0，真实 clang 15.0.4 调用，3 个补丁全部应用）
- 上游测试用例通过率：0/0（上游无测试用例，不适用）
- 新增测试用例通过率：23/23（100%）

`conan create` 实测要点：

| 项 | 实测值 |
|---|---|
| 制品 | `xlax/2.4`（package_id `85b666b369f85d1e12dffd09f67543d888ff503d`） |
| test_package 汇总 | `11 passed, 0 failed` |
| 程序内自检 | `selftest: 12/12 checks passed` |
| ELF | `ELF64 / DYN (PIE) / AArch64` |
| DT_NEEDED | `libXaw.so.7 libXmu.so.6 libXt.so.6 libX11.so.6 libXext.so.6 libXpm.so.4 libc.so` |
| 安全属性 | GNU_RELRO 存在、GNU_STACK 无执行位 |
| 本地 CI 模拟 | `JC/L0/L1/L4/L5=pass`，`L2=skip`（non-blocking） |

证据报告：`2.4/reports/test-report.md`、`2.4/reports/conan-verify-report.md`。
原始日志（`conan-create.log`、`w3-local-ci.log`）为本地复现产物，未随 PR 提交；
报告中保留日志路径与关键原文摘录，可按报告内命令在本地复现。

## 补充说明

1. **构建方式**：上游为 Imake 工程，OHOS 无 `imake`/`xmkmf`，故绕过 Imake 直接用 `$CC` 编译单一
   `xlax.c`（`XawClientLibs` 展开为 `-lXaw7 -lXmu -lXt -lX11 -lXext -lXpm -lm`），
   `manifest.yaml` 记 `build_system: custom`。`finish` 的 G0 `clean-verify` 面向 autotools（无条件跑
   `./configure`），对 custom 包不适用；补丁自包含性已由 `conan create` 的三条 `Apply patch` 与
   `clean-verify` 的「3 个补丁全部应用成功」共同佐证。
2. **依赖 package_id**：`libxaw/1.0.14` 与 `libxmu/1.3.1.1` 以 `force=True` 钉 `libx11/1.8.13`，
   会使 `libxext/6.4.0.1`、`libxpm/3.5.17` 的 package_id 落到 1.8 配置（`minor_mode`），
   而制品仓仅有 6.4 配置的二进制。本 PR 在该两包上用源码重建满足消费需求，其余 5 个依赖消费已发布二进制。
3. **不需要 libbsd**：Debian 的 `use-libbsd.diff` 在 OHOS 上不需要。实测 `nm -D /lib/ld-musl-aarch64.so.1`
   存在 `strlcpy`/`strlcat`（OpenBSD 语义，`n=10 m=8`），产物 `DT_NEEDED` 中亦无 `libbsd`。
4. **软件级文件**：本包安装 `bin/xlax`，按 R38/L0k 需要软件级 `commands.json`（`type: "tool"`），
   并按仓库 CLI 包惯例（xclip、strace 等）提供软件级 `README.md`。这两个文件位于
   `archives/x/xlax/`（4 段路径），会被 PF9「变更路径缺版本目录层」fail-closed 命中 ——
   属规则与仓库既有布局的结构性冲突，故建 PR 时跳过预检；PF1–PF8 已另行核对通过。
5. **L2 smoke 跳过**：包按仓库约定不写 RUNPATH，裸执行 `--version` 时动态加载器找不到 `libXaw.so.7`；
   在 `conanrun` 运行环境中 `--version` 与 `--selftest` 均正常。CI 将该情形标为 non-blocking。
6. **GUI 行为边界**：`xlax` 是 X11 客户端，需连接 X server 才能真正绘图。自动化验证覆盖到
   「Xt 初始化之前的分支」与「widget class 记录/符号解析」，交互式键盘映射未做自动化验证。
