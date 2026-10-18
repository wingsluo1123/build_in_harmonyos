## PR 信息

- **三方库名称**：plast
- **上游版本**：2.3.2
- **上游仓库地址**：https://github.com/PLAST-software/plast-library （官方主页 https://plast.inria.fr/ ）
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：`openharmony-compile-agent` 技能；知识条目 **E092**（OHOS 下 `CMAKE_SYSTEM_NAME` 被映射为 `HarmonyOS`，需覆盖为 `Linux`）、**E140**（HarmonyOS CMake 平台检测）、**E002**（`/tmp` 只读）、**E074**（构建并行度必须降级，配合 **P020** 的 HMDFS 不支持 FIFO/hardlink）；`knowledge/operations/build-systems.md`；`适配建议汇总/适配共性问题与首次真机启动避坑指南.md`（SSH/scp 不可用时的传输替代、隔离环境、TMPDIR、runner 日志，以及 §15「symlink/hardlink/mkfifo 创建失败 → make 先降级单线程」）

plast 是 bank-to-bank（库对库）的序列相似性搜索工具，思路与 BLAST 相近但面向「两个序列集合互相比对」，
多线程、内存占用小，提供 `plastp` / `tplastn` / `plastx` / `tplastx` / `plastn` 五种算法；上游以
C++11 静态库 + 自带命令行工具（`PlastCmd`、`makeplastdb`）发布，另有可选 JNI 绑定。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | **108** | 来源：`test/unit/src/`（19 个测试文件），用例以 `new TestCaller<...>` 注册。**源码中共 119 处注册语句，其中 11 处被 `//` 或 `/* */` 注释禁用 → 未被注释禁用的注册语句为 108**（与本项目审查工具的上游实测口径一致；复核方式：`grep -c 'new TestCaller' test/unit/src/Test*.cpp` = 119，剔除 11 处注释禁用项） |
| 集成测试 | 0 | 上游无独立集成测试框架，`test` target 即运行同一套 CppUnit |
| 其他测试 | 0 | `test/benchmark` 为 `EXCLUDE_FROM_ALL`，不参与默认构建 |
| **合计** | **108** | **统计单位：上游测试源码中「未被注释禁用」的用例注册语句**。其中 **12 处位于 `TestMisc.cpp`，而该文件整体被 `#if 0` 包住**（编译为空翻译单元，符号根本不存在），因此**实际参与编译的用例为 96 个**——与运行期 CppUnit 打印的 `OK (96 tests)` 完全吻合。断言规模仅作参考：`CPPUNIT_ASSERT` 家族静态 token 计数 475（含 1 处 `CPPUNIT_ASSERT_THROW`） |

**完整对账（每一层都可复核）**：

```text
119 处 new TestCaller（test/unit/src 下 19 个测试文件）
 ├─  11 处  被 // 或 /* */ 注释禁用
 └─ 108 处  未被注释禁用                     ← 本 PR 声明的「上游用例数」（= 审查工具实测 N）
     ├─  12 处 位于 TestMisc.cpp，该文件整体 #if 0 → 编译为空 TU，符号不存在
     └─  96 处 实际编译并注册（main.cpp 的 18 个 suite）  ← CppUnit 打印 OK (96 tests)
         ├─  88 处 本环境实际执行断言并通过
         └─   8 处 因 release 归档缺 test/db 语料，在用例体内早退（清单见下）
```

> `TestMisc.cpp` 的 12 例已**实测确认不可执行**：在真机构建树里给 `main.cpp` 补一行
> `runner.addTest (TestMisc_suite());`，编译立即失败——
> `error: use of undeclared identifier 'TestMisc_suite'`。原因是 `TestMisc.cpp` 第 17 行
> 起就是 `#if 0`，整文件不产生任何符号（上游 `main.cpp` 里也没有它的 `extern "C"` 声明，
> 与此一致）。即这 12 例在上游当前源码状态下**不可能被任何构建执行**，不是本 PR 跳过的。

逐 suite 对账：

| suite | 文件 | 参与编译的用例 | 被 `//`/`/* */` 禁用 | 被 `#if 0` 禁用 | `main.cpp` 是否注册 |
|-------|------|---------------|---------------------|----------------|---------------------|
| TestOs | `TestOs.cpp` | 3 | 0 | 0 | ✅ |
| TestDesignPattern | `TestDesignPattern.cpp` | 20 | 0 | 0 | ✅ |
| TestSequenceIterator | `TestSequenceIterator.cpp` | 12 | 0 | 0 | ✅ |
| TestSequenceDatabase | `TestSequenceDatabase.cpp` | 11 | 0 | 0 | ✅ |
| TestSeedModel | `TestSeedModel.cpp` | 5 | 0 | 0 | ✅ |
| TestSeedIterator | `TestSeedIterator.cpp` | 5 | 0 | 0 | ✅ |
| TestDatabaseFiltering | `TestDatabaseFiltering.cpp` | 1 | 0 | 0 | ✅ |
| TestDatabaseIndex | `TestDatabaseIndex.cpp` | 9 | 0 | 0 | ✅ |
| TestDatabaseCompare | `TestDatabaseCompare.cpp` | 3 | 0 | 0 | ✅ |
| TestScoreMatrix | `TestScoreMatrix.cpp` | 8 | 1 | 0 | ✅ |
| TestAlgoInitializer | `TestAlgoInitializer.cpp` | 4 | 0 | 0 | ✅ |
| TestPlastLike | `TestPlastLike.cpp` | 1 | 0 | 0 | ✅ |
| TestPlast | `TestPlast.cpp` | 1 | 1 | 0 | ✅ |
| TestAlignment | `TestAlignment.cpp` | 6 | 5 | 0 | ✅ |
| TestFilter | `TestFilter.cpp` | 1 | 2 | 0 | ✅ |
| TestPlastStrings | `TestPlastStrings.cpp` | 1 | 1 | 0 | ✅ |
| TestSequenceMask | `TestSequenceMask.cpp` | 1 | 1 | 0 | ✅ |
| TestBugs | `TestBugs.cpp` | 4 | 0 | 0 | ✅ |
| **小计（18 个已注册 suite）** | | **96** | **11** | **0** | — |
| TestMisc | `TestMisc.cpp` | **0** | 0 | **12** | ❌（整文件 `#if 0`，上游也无 extern 声明） |
| **合计** | | **96**（+12 不可编译 = 108 未被注释禁用的注册语句） | **11** | **12** | — |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | **108** | **不变**（上游用例一个未删、一个未禁用；补丁 0011 只在缺 fixture 时前置早退，用例集本身未改动） | 其中运行期启动 **96** 例（18 个已注册 suite = 实际参与编译的全部用例）；本环境**实际执行断言并通过 88 例**，8 例因 release 归档缺 fixture 在用例体内早退。另有 12 处注册语句位于 `TestMisc.cpp`，该文件整体 `#if 0`、编译为空 TU，上游与本环境都不可能执行 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 10 | **新增** | `test_package/`：`test.sh` 6 项断言 + `test_plast_api.cpp` 4 项断言，逐条列于下方 |
| **合计** | **118**（108 上游 + 10 新增） | **+10** | **单位不同，仅供参考，不合并为单一通过率**：上游未被注释禁用的 108 处注册语句全部保留（其中 96 处实际编译并启动、88 处实执行断言全部通过）；新增 10/10 通过（100%） |

8 例早退用例及其缺失 fixture（上游从已失效的 `plast.gforge.inria.fr` 下载完整语料，
release 归档只带 `bug15696.fa` / `bug15696b.fa` / `query.fa` / `sapiens_1Mo.fa` / `tursiops.fa` 共 5 个文件）：

| 用例 | 缺失 fixture |
|------|--------------|
| `testXmlFilterReader` | `filter1.xml` |
| `testFileLineIterator2` | `uniprot_sprot.fa` |
| `testFileLineIterator3` | `panda.fa` / `yeast.fa` / `uniprot_sprot.fa` / `chr10.fa` / `CionaIntestinalis.fa` |
| `testFastaBigFile` | `uniprot_sprot.fa` |
| `testFilesList` | `panda.fa` / `yeast.fa` / `uniprot_sprot.fa` / `chr10.fa` |
| `testFastaHugeFile` | `bugs/15202/hugecomment.fa` |
| `testFastaQuickReader2` | `panda.fa` / `Fee5ab_All_non_rRNA.fasta` / `uniprot_sprot.fa` |
| `test_maskdb` | `aphid_10000.fa` |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（逐条说明如下）

4 组修改全部为可移植性修复，**未改变任何断言的语义或期望值**：

1. **`test/CMakeLists.txt`** —— `test` target 改用仓库内 fixture 与真实二进制路径。
   - 修改原因：上游 `test` target 调用 `test/runTest.sh`，该脚本在 `test/db` 不存在时从
     `plast.gforge.inria.fr` 下载数据（该域名已无法解析）；同时它硬编码
     `<build>/bin/PlastLibraryTest`，而 `EXECUTABLE_OUTPUT_PATH` 实际是
     `${PROJECT_BINARY_DIR}/bin/${CMAKE_BUILD_TYPE}`，单配置生成器下路径不匹配。
   - 修改内容：把 `test/db` 复制到构建树；改用 `$<TARGET_FILE:PlastLibraryTest>` 直接运行测试二进制。
     补丁 `0005-test-in-tree-db-fixtures.patch`。
2. **`test/unit/src/main.cpp`** —— 让 runner 输出失败详情并返回真实状态。
   - 修改原因：上游 runner 只创建了 `TestResultCollector` 却从不输出，并且**恒 `return 0`**——
     任何断言失败都会被静默吞掉，`make test` 永远成功。
   - 修改内容：用 `CppUnit::TextOutputter` 打印失败断言，返回 `result.wasSuccessful() ? 0 : 1`。
     补丁 `0010-test-runner-report-failures.patch`。
     本 PR 引用的 `OK (96 tests)` 一行正是由该补丁产生（上游不打印该行）。
3. **`test/unit/src/cppunit.h` + `TestAlignment.cpp` / `TestDesignPattern.cpp` / `TestPlast.cpp` /
   `TestSequenceIterator.cpp`** —— 临时文件改用 `TMPDIR`。
   - 修改原因：这些用例把临时文件硬编码到 `/tmp`，而 HarmonyOS 的 `/tmp` 是只读文件系统（**E002**）。
   - 修改内容：新增 `plastTmpPath()`（按 `TMPDIR` 生成路径），替换全部 `/tmp` 字面量；
     同时把 `TestAlignment.cpp` 里一处**硬编码的第三方绝对路径** `"/udd/edrezen/tmp/li/result.out"`
     也改成 `plastTmpPath("result.out")`（该路径在 OHOS 上同样不可写，且它决定了
     `test_alignment1` 实际检查的文件位置）。
     补丁 `0008-unit-tests-tmpdir.patch`。
4. **`test/unit/src/cppunit.h` / `TestDesignPattern.cpp` / `TestSequenceDatabase.cpp` /
   `TestSequenceIterator.cpp` / `TestSequenceMask.cpp`** —— 缺失 fixture 时显式早退。
   - 修改原因：8 个用例依赖归档未附带的 `test/db` 语料，缺文件时会抛异常而非明确跳过。
   - 修改内容：新增 `plastFixtureAvailable()` / `plastFixturesAvailable()`，缺失时打印
     `[skip] <用例名>: fixture '<文件>' is not shipped in the release archive` 并返回。
     补丁 `0011-skip-unavailable-fixture-tests.patch`。

补丁树中另有 9 个**产品代码/构建系统**补丁（`0001`~`0004`、`0006`、`0007`、`0009`、`0012`、`0013`），
不属于「上游测试用例修改」，详见「遇到的问题与解决方案」。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无消费者层面测试，适配后补全了测试

- **补全的测试范围**：新增 `test_package/` 消费者测试共 **10 项断言**（其中 9 项相互独立 + 1 项聚合校验，见「验证结果」），覆盖「打包产物是否能被真实消费者使用」这一上游完全没有覆盖的层面。
- **补全原因**：上游的单测全部在源码树内运行，不验证安装后的包布局、CMake 导入目标、`bin/` 可执行文件可用性与公共 API 链接；而这些正是 Conan 包的交付面。
- **新增测试文件清单**：
  1. `test_package/test.sh` —— CLI 端到端 6 项断言：
     `PlastCmd and makeplastdb are installed in the package bin/ directory`、
     `PlastCmd -h prints the PLAST option list`、
     `related query finds the subject at 100.00% identity`（正例，identity ≥ 90%）、
     `negative control stays at 0.00% identity`（同组成的反向序列对照，identity < 90%）、
     `makeplastdb produced a non empty bank.fa.info`、
     `C++ library API consumer test passed`。
  2. `test_package/test_plast_api.cpp` —— C++ 库 API 消费者 4 项断言：
     `installed misc/api/version.hpp reports version 2.3.2`、
     `PlastCmd::execute() ran through the library API without exception`、
     `library API reported at least one alignment`、
     `library API alignment reaches at least 90% identity`。
     该程序用 `launcher::core::PlastOptionsParser` + `launcher::core::PlastCmd`，即 `PlastCmd` 二进制的同一条调用路径。
  3. `test_package/data/{bank.fa,query.fa,query_unrelated.fa}` —— 76~81 aa 的确定性 FASTA fixture（反例由正例序列机械反转生成，避免手工转录错误）。
  4. `test_package/conanfile.py` + `CMakeLists.txt` + `MANIFEST.yml` —— 用 `CMakeDeps` 消费 `plast::plast`，
     显式定位 bash 与包内 `bin/`，scratch 目录回退到可写位置。

## 验证结果

- **编译状态**：通过（OHOS 设备原生构建，aarch64-unknown-linux-ohos，clang 15.0.4；`conan create` → `EXITCODE=0`）
- **上游测试用例通过率**：上游未被注释禁用的 **108 处注册语句全部保留**（未删除、未新增禁用）；其中 **96 处实际编译并注册**（18 个已注册 suite；另 12 处在整文件 `#if 0` 的 `TestMisc.cpp` 中，上游自身也不可能编译），这 96 例中 **88/88 实执行用例通过（100%）**，另 8 例因 release 归档未附带其 `test/db` fixture 在用例体内早退（清单见上）。CppUnit 汇总行 `OK (96 tests)` 统计的是**已启动**的测试方法数（`TestResultCollector::runTests()`），早退用例同样被计为 OK，**本 PR 不据此宣称 96/96**
- **新增测试用例通过率**：**10/10（100%）**，`conan create` 输出 `ALL PLAST CONSUMER TESTS PASSED`。其中 **9 项是相互独立的断言**（`test.sh` 5 项 + `test_plast_api.cpp` 4 项），另 1 项是聚合校验（`test.sh` 末尾 `ok "C++ library API consumer test passed"`，它只是那 4 项 C++ 断言的退出状态汇总）
- **统计边界**：上游四个口径必须分清——**119** 处源码注册语句 / **108** 处未被注释禁用 / **96** 处实际编译并启动 / **88** 处本环境实执行通过（本 PR 的通过率分母用的是 88 与 10）；新增分母为 10 项 `test_package` 断言。两者单位不同，分行呈现，不合并为单一通过率。**未覆盖边界**：`plastx` / `tplastx` / `plastn` 三个核酸算法未做 CLI 级端到端实跑（其反向阅读框路径已由 `testReadingFrameIterator` 与 `testCompositeDatabase2` 覆盖）；JNI/Java 绑定未纳入本轮；8 例 fixture 缺失用例未执行；`TestMisc.cpp` 的 12 处注册语句位于整文件 `#if 0` 内（编译为空 TU，上游与本环境均不执行，未改动用例集）。
- **构建环境**：HarmonyOS aarch64（HongMeng Kernel 1.12.0, Toybox）/ clang 15.0.4 / cmake 4.1.2 / conan 2.31.1 / git 2.45.2；profile `os=OHOS 6.0, arch=armv8, compiler=clang 15, libcxx=libc++, cppstd=17`
- **执行路径**：本轮直接使用 `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`，**未走 `ohos-test-runner.sh` 隔离 job**，故无 runner `RUN_DIR`；等价路径为：包目录 `/storage/Users/currentUser/.conan2/p/b/plast078913f4e5cd8/p`，日志 `/storage/Users/currentUser/tmp/plast-create.log` 与强制重建日志 `plast-create-full.log`（240 765 B）
- **CI build 号**：**构建 #93740（校验通过 ✅）**——`L0 门禁（结构完整性）通过`、`L1 门禁（测试执行验证）通过`、`Conan test_package 通过`，七个步骤全绿。此前有 5 次失败（#93278 / #93345 / #93397 / #93409 / #93525），**全部**中断在 worker 侧进程创建（fork / `posix_spawn`）资源耗尽上，与本库源码无关（跨 4 个 worker：CI-026 / CI-013 / CI-010 / CI-035）。其中**第一次 #93278 是本包范围内的真问题**：`make: jobserver mkfifo: ... Operation not permitted` → `/bin/sh: can't fork - try again` → `Error 127`，**全程无一条编译诊断**，根因 **E074 + P020**（HMDFS 无 FIFO → make jobserver 失效 → 递归 make 无限并行），已按 E074 在 `build()` / `target="test"` / test_package 三处固定 `-j1` 修复，#93345 随即证明编译阶段**全程通过**（`libPlastLibrary.a` 链接成功、测试目标编到 `[96%]`，`jobserver`/`can't fork` 全部消失）。其余 4 次失败时**没有任何并行**——编译的是 CMake 自带的 3 行 `testCCompiler.c`、甚至只是 `source` 一个环境脚本——且 #93397 与 #93525 的 **L0/KC/JC/G0 同样全绿**，详见问题 11、13 与 `reports/device-verification.md` §9

### 产物验证

| 检查项 | 结果 | 说明 |
|---|---|---|
| 编译无错误 | PASS | CMake，状态 `built`（尚未 `conan upload`） |
| 产物存在性 | PASS | `bin/PlastCmd`(1 235 456 B)、`bin/makeplastdb`(174 592 B)、`lib/libPlastLibrary.a`(3 980 652 B)、`include/**`、`test/` |
| 库类型 | PASS | **static**：`package_type = static-library`，`lib/libPlastLibrary.a`；两个 CLI 为可执行文件 |
| ELF 格式 | PASS | `elf64-littleaarch64`，`EM_AARCH64` |
| 动态依赖 | PASS | 仅 `libc++_shared.so` + `libc.so`（`PlastCmd`/`makeplastdb` 均同）；`cppunit` 为静态链接进测试程序，不进入 CLI 的 NEEDED |
| test_package | PASS | 10/10 断言通过（真实执行打包后的二进制 + 真实调用库 API） |
| 端到端实跑 | PASS | `PlastCmd -p plastp -i query.fa -d bank.fa -o out.txt -e 1e-5 -a 2` → `qry sub 100.00 76 0 0 6 81 1 76 1e-42 151.4` |
| SHA256 | PASS | 见下表 |

| 产物 | SHA256 |
|---|---|
| `bin/PlastCmd` | `2f34e79bb362148e913e9f56295271a5700c8ba7b17013a5547bd392d465247f` |
| `bin/makeplastdb` | `4875fe73f1c99d13a9508ed5d7051731629f8beb5eb2b52e71100d24939dcb24` |
| `lib/libPlastLibrary.a` | `79178f3f590883ce1a7bb68fbd5ec4241d0472fa7b1f1fc29c2bf0a11ca62085` |

### W3 本地门禁

| 门禁 | 结果 | 说明 |
|---|---|---|
| L0（结构完整性） | 本机/真机侧核对通过 | 目录 `archives/p/plast/2.3.2/` 与 `conanfile.py` 版本一致；`conandata.yml` 的 `patches` 为 list 且 13 个文件均存在、顺序正确；依赖 `simde/0.8.2`、`cppunit/1.15.1` 已发布（`conan download --only-recipe` 验证）；`commands.json`（R38）存在且合法；分支名 `feat/plast-2.3.2` 含 `plast-2.3.2`（L0n） |
| L1（test_package） | pass | 真机 `conan create` 日志含 `Running test()` 与 10 项 `[ OK ]`；`build()` 内运行上游 CppUnit 套件 |
| L2（smoke test） | pass | `PlastCmd -h` rc=0，输出 `plast 2.3.2` 与完整选项表 |
| L4（NX/PIE/RELRO） | pass | `Type: SharedObject` + `FLAGS_1: NOW PIE`（PIE）；`PT_GNU_STACK` flags=`PF_R|PF_W`（**无 PF_X**，NX 生效）；`PT_GNU_RELRO` 存在且 `FLAGS: BIND_NOW`（Full RELRO） |
| L5（产物基线） | pass | bin/lib/include 产物与 SHA256 如上 |
| JC / KC（junk / knowledge check） | 未执行 | 未在 CI worker 运行 |
| shadow CI / build 号 | **pass：构建 #93740**（L0 + L1 + `Conan test_package` 全部通过，7 个步骤全绿） | 该 head 之前有 5 次失败（#93278 / #93345 / #93397 / #93409 / #93525），全部中断在 worker 侧进程创建资源耗尽上：**#93278** 实为本包范围内的 make 并行度问题（无编译诊断），已按 **E074** 固定 `-j1`；**#93345** `-j1` 生效、编译全程通过，末步链接 `PlastLibraryTest` 时 `posix_spawn` 返回 `EAGAIN`；**#93397**（CI-013）与 **#93525**（CI-035）在 CMake 编译器探测阶段首个 `fork()` 即 `EAGAIN`，两次**同次构建 L0/KC/JC/G0 全绿（`Errors: 0`）**；**#93409**（CI-010）在 `source conan` 环境脚本时 `can't fork`。后四次均与本库源码无关（见问题 11、13） |

---

## 遇到的问题与解决方案

| # | 现象 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | `find_package(JNI REQUIRED)` 使配置阶段直接失败 | OHOS 生态无 JDK 配方（`conan download openjdk/*` 全部返回 `system acceleration policy not enabled`），且 `src/CMakeLists.txt` 用 `file(GLOB_RECURSE)` 收集全部源码，JNI 头缺失会拖垮整库 | 补丁 0002：`find_package(JNI)` 改为非必需，无 JDK 时排除 `src/launcher/jni` 并打印提示；有 JDK 时自动恢复编译 |
| 2 | aarch64 上 clang 报错 `-msse3` 不受支持 | 上游非 debug 分支硬编码 `-O3 -funroll-loops -fomit-frame-pointer -msse3` | 补丁 0003：`-msse3` 仅在 x86 目标传递 |
| 3 | 上游要求 Intel/AMD 64bit + SSE2+，aarch64 无法编译三个 SIMD kernel | `SmallGapHitIteratorSSE8.cpp` / `UngapHitIteratorSSE8.cpp` / `UngapHitIteratorSSE16.cpp` 使用 `_mm_*` 内建 | 补丁 0004：改用 `SIMDE_ENABLE_NATIVE_ALIASES` + `<simde/x86/sse3.h>`，同一份 kernel 编译为 NEON，**语义不变**。未采用「运行期切到标量迭代器」是因为两者判定逻辑不等价——SSE 版本会额外用 `_alignmentResult->doesExist()` 过滤已存在的比对 |
| 4 | 运行期 `DefaultFactory` 五个工厂指针未初始化（空指针） | PLAST 整个 OS 抽象层由自定义宏 `__LINUX__` 选择，该宏只在 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 分支注入；OHOS 下 conan 映射为 `HarmonyOS` | 按 **E092** 在配方 `generate()` 中覆盖 `CMAKE_SYSTEM_NAME=Linux` |
| 5 | `StatisticsPlastn.cpp` 编译失败 | OHOS profile 固定 `cppstd=17`，C++17 已移除 `register` 存储类说明符 | 补丁 0006：删除该关键字 |
| 6 | `testSystemCommand` 崩溃、多个单测写 `/tmp` 失败 | OHOS `/tmp` 只读（**E002**），而 `SystemCommand` 与单测都硬编码 `/tmp` | 补丁 0007（`SystemCommand` 临时文件改 `TMPDIR`）+ 补丁 0008（单测临时文件改 `TMPDIR`） |
| 7 | `testFastaOutputFrame` **挂死**（12 分钟 CPU 不退出） | `CommonOsImpl.hpp:80` 用 `char c != EOF` 做哨兵；aarch64 `char` 默认无符号，`(char)-1 == 255`，EOF 永不匹配。触发条件是「表头 115 字符 > `commentMaxSize=100`」且「文件末行无换行」 | 补丁 0009：哨兵变量改为 `int` 并显式 `(unsigned char)` 取初值。**clang 编译期已用 `-Wtautological-constant-out-of-range-compare` 警告过该行** |
| 8 | 反向阅读框 FRAME_4/5/6 翻译结果全错（`EKKKK…`/`KKKK…`），`testCompositeDatabase2` 段错误 | `ReadingFrameSequenceIterator.hpp` 的 `char getDirection()` 返回 -1；aarch64 上变 255，被提升为 `int` 后当作数组下标参与 `offset + direction*(i+k)`，反向链索引越界 | 补丁 0012：返回类型与局部变量改为 `int`。小输入静默错、大输入崩溃，是同一根因的两种表现 |
| 9 | 包内 `include/misc/api/version.hpp` 报告 `unstable-master` | `install(FILES ... DESTINATION include/os/api/)` 路径笔误，源码树里的同名占位头反而随 `install(DIRECTORY src/)` 进包并覆盖生成头 | 补丁 0013：改为安装到 `include/misc/api/`；`test_package` 已把该断言固化为回归保护 |
| 10 | 测试框架吞掉失败、`make test` 恒成功 | 上游 runner 恒 `return 0` 且不打印失败详情 | 补丁 0010（见「上游测试用例修改说明」第 2 条） |
| 11 | **CI 构建 #93278 判为「编译失败」，但日志中没有任何编译诊断**：`make: jobserver mkfifo: ... Operation not permitted` → `/bin/sh: can't fork - try again` → `BasicAlgoIndexator.cpp.o Error 127` / `AlgorithmPlastn.cpp.o Error 1` | **E074 + P020**：HarmonyOS/HMDFS 不允许创建 FIFO（真机复核 `mkfifo` → `Operation not permitted`），GNU make 的 jobserver 只能退化为 pipe（`--jobserver-auth=3,4`）；CI worker 上子 make 拿不到有效 jobserver 时按「无限并行」运行，PLAST 146 个源文件（161 个编译步骤）在 `-j20` 下瞬间耗尽 fork 配额。**该缺陷只在 CI worker 的 HMDFS 上稳定复现，本机真机 `-j20` 不触发** | 配方 `build()`、`cmake.build(target="test")` 与 `test_package` 三处统一 `cmake.build(build_tool_args=["-j1"])`（对齐仓库既有 10 处先例）。实机先验证 GNU make 取值规则：`make -j20 -j1` → `MAKEFLAGS=[ -j1]` 且不再建立 jobserver。修复后复跑 `conan create`：`EXITCODE=0`、363 s、`can't fork` 0 次、`OK (96 tests)`、包 `af03c1b0320f7f5fc22545d6f17403605281f4ce` 创建成功 |
| 12 | 首次 CI 日志出现 `found 3 source URL(s)`，其中一条是 `https://plast.inria.fr/developer-guide/)` | CI 的 “Pre-download” 步骤用正则从 `conandata.yml` 全文中抓取 URL，把注释里带括号的文档链接也当成了下载源 | 改写该注释为不含 URL scheme 的表述；真源仍为 `github.com/PLAST-software/plast-library` 的 tag 归档，CI 侧自动加 gh-proxy 镜像 fallback |
| 13 | `-j1` 修复后 CI **连续四次**仍在**进程创建**上失败（换了 3 个 worker）：**#93345**（CI-026）编译全程通过、末步链接 `PlastLibraryTest` 报 `clang-15: ... posix_spawn failed: Resource temporarily unavailable`；**#93397**（CI-013）CMake 编译器探测阶段 `make[1]: /bin/sh: Resource temporarily unavailable` → 编 3 行 `testCCompiler.c` 就 `Error 127`；**#93409**（CI-010）连 `cmake` 都没起来，`conanbuildenv-release-armv8.sh[13]: can't fork - try again`（13 个补丁已全部按序应用成功）；**#93525**（CI-035）与 #93397 签名完全一致（同为 `CMakeTestCCompiler.cmake:67` + 3 行探针 + `Error 127`，全程 29 s） | **worker 侧进程创建（fork/posix_spawn）资源耗尽**，非本库缺陷。最强证据：后四次失败时**都没有任何并行**，编译的是 CMake 自带的 3 行探针、甚至只是 `source` 一个环境脚本；#93397 与 #93525 同次构建 **L0/KC/JC/G0 全部 pass**（`Errors: 0`）。旁证：#93345 期间同一 worker 的 conan 缓存里还有另一个包 `xeus` 的构建目录（19:01 / 19:08）；CI 构建墙同期显示最近 50 条记录 **24 条失败、17 条同时在跑** | 配方层面无可靠绕行手段（五次失败分布在编译/链接/编译器探测/环境脚本四个阶段、跨 4 个 worker CI-026/CI-013/CI-010/CI-035，任何配方或并行度改动都不可能同时解释它们）。证据固化：从 CMake 的 `link.txt` 取出失败时的同一条链接命令，同机**连续执行 10 次全部成功**（产物 2 025 984 B，单次 <1 s）；40 次进程创建压力循环失败 0 次；真机完整 `conan create` 三次全部 `EXITCODE=0`。**最终结果：同一 head 在负载回落后重跑即通过——构建 #93740，L0/L1/`test_package` 全绿**（见「验证结果」与 W3 门禁表）。详见 `reports/device-verification.md` §9 / §9.1 / §9.2 |
| 14 | 人工审查（`pc-pr-review`）rule4 判定**「少报」：上游实测 N=108 > 声明 N=96** | 本 PR 早期把上游用例数写成「`main.cpp` 注册的 96 例」，只覆盖了被 runner `addTest` 的 18 个 suite；而上游测试源码中**有效注册的 `new TestCaller` 实为 108 例**（另有 11 处被注释/`#if 0` 禁用，共 119 处）。差额 12 处来自 `TestMisc.cpp`——**该文件整体被 `#if 0` 包住**（编译为空 TU、不产生符号），因此不进入运行期的 `OK (96 tests)` 统计；真机实测给 `main.cpp` 补注册行会直接编译失败 `use of undeclared identifier `TestMisc_suite`` | 已按实测重写「测试用例对比」：上游用例数改为 **108**，并补一张 19 个 suite 的逐文件对账表（96 已注册 + 12 `TestMisc` = 108；108 + 11 禁用 = 119），同时保留四个口径的区分——**119 源码注册语句 / 108 未被注释禁用 / 96 实际编译并启动 / 88 本环境实执行通过**。适配后用例数相应为 118（108 上游 + 10 新增），确认上游用例**一个未删、一个未禁用** |

---

## 补充说明

### 适配要点

- **x86 SIMD → SIMDe**：见上表第 3 条。三个 kernel 的文件名与类名保持不变，改动仅限头文件替换，便于向上游提交。
- **E092 平台映射的副作用**：`PLAST_BUILD_OS` 与 `PlastCmd -h` 的 `OS:` 会显示 `Linux`。这是刻意覆盖 `CMAKE_SYSTEM_NAME` 以激活 `__LINUX__` 分支的直接结果，属预期行为，不是验证不实。
- **JNI/Java 绑定未纳入本轮**：C++ 静态库、`PlastCmd`、`makeplastdb` 功能完整；配方保留了 JDK 存在时自动启用的能力。
- **版本与状态**：首次适配上游 2.3.2，按 R37 保持版本号 `2.3.2` 未加后缀；归档状态 `built`（真机全流程通过，尚未 `conan upload`）。
- **并行构建固定 `-j1`**：PLAST 源文件多（146 个源文件 / 161 个编译步骤）且 CMake 生成递归 Makefile，在 HMDFS 上会因 jobserver 失效而 fork 耗尽，故三处 `cmake.build()` 均显式 `build_tool_args=["-j1"]`（**E074**，对齐仓库既有 10 处先例）。构建耗时约 6 分钟，可接受；实机日志中 `can't fork` 与 `jobserver` 警告均为 0 次。
- **`cppunit` 为 `test_requires`**：CppUnit 只被 `build()` 内构建并运行的上游 `PlastLibraryTest` 使用，装进包的产物都不链接它，因此声明为测试依赖（对齐本仓 `archives/t/taglib` 的做法），消费者依赖图里不再出现 `cppunit`。改后重跑真机 `conan create`：`EXITCODE=0`，且三个产物 SHA256 **逐字节不变**。
- **产物可复现性**：`-j1` 与 `test_requires` 两次配方收敛后，`PlastCmd` / `makeplastdb` / `libPlastLibrary.a` 的 SHA256 与首次验证完全一致（见上表）。

### 路径 B（贡献创新）证据

本库在真机上暴露并修复了**两个上游产品代码的功能性缺陷**（不是测试问题、也不是平台编译修补）：

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | `testFastaOutputFrame` **12 分钟 CPU 不退出**（进程挂死、无报错） | `CommonOsImpl.hpp:80` 用 `char c != EOF` 做哨兵；aarch64 `char` 默认无符号，`(char)-1 == 255`，EOF 永不匹配，末行无换行时读循环死转 | 补丁 0009（哨兵改 `int`，初值显式 `(unsigned char)`） |
| 2 | 反向阅读框 FRAME_4/5/6 翻译结果**全错**（`EKKKK…`/`KKKK…`），并在较大库上 `SIGSEGV` | `char getDirection()` 返回 -1 → 255，被提升为 `int` 后当作数组下标参与 `offset + direction*(i+k)`，反向链读越界 | 补丁 0012（返回类型与局部变量改 `int`） |

同时沉淀了 3 份知识草稿（随本 PR 提交，不改动 `knowledge/graph/index.tsv`）。
**已与 `main` 上既有条目逐条比对，不主张重复的"新模式"**，各稿的增量如下：

| 草稿 | 既有条目 | 本稿增量 |
|------|----------|----------|
| `E999-draft-aarch64-unsigned-char-negative-index.{kv,md}` | `E419`（plain char 符号性影响取值） | **新增失败模式**：窄化发生在 `return` 语句内（编译器不告警）→ 255 被当作**数组下标** → 小输入静默错误、大输入段错误；并明确**禁止只 clamp 索引**（崩溃消失但结果依旧错误）。`similar_to: E419` |
| `E999-draft-aarch64-unsigned-char-eof-sentinel.{kv,md}` | `E419`、既有草稿 `DRAFT-8543-plain-char-eof-sentinel-infinite-loop`（同一模式） | 本库触发条件（表头 115 字符 > `commentMaxSize=100` 且末行无换行）、**编译器 `-Wtautological-constant-out-of-range-compare` 线索在既有构建日志中已出现却未被处理**、`int c = (unsigned char) tmp[...]` 取初值写法。`similar_to: E419` |
| `E999-draft-cxx17-register-storage-class.{kv,md}` | `E293`（error signature 已含 `ISO C++17 does not allow 'register' storage class specifier`） | 本库实例 + `grep` 预扫描命令 + 「删除后语义不变」依据 + 禁止 `#define register` / `-Wno-register` 掩盖的边界。`similar_to: E293` |

判断依据（对齐既有先例 `archives/x/x86_64-elf-grub/2.12/notes.md`）：两份**上游功能性缺陷**均已定位到具体文件行、
给出最小复现与修复边界，且指向的不是单个库的编译修补，而是 aarch64 移植中可复现的一类问题
（`char` 符号性 + 工具链默认标准）；三份草稿均包含症状、根因、修复边界、禁止做法与可复核日志。
故适配路径记为 **路径 A（基础适配）+ 路径 B（贡献创新）**。

### 已知限制

1. **JNI/Java 绑定未纳入本轮**：OHOS 生态无 JDK 配方，`src/launcher/jni` 不参与构建；C++ 静态库、`PlastCmd`、`makeplastdb` 功能完整。配方保留了自动启用能力，将来有 JDK 时无需改配方。
2. **8 个上游用例早退**：仅因 release 归档未附带其 `test/db` 语料，非平台限制；补齐语料后可恢复执行。
3. **包体积**：上游 `install()` 会把 `test/db`（含 `tursiops.fa` 11.9 MB）与 `PlastLibraryTest` 一并装包，本轮保留上游行为，未裁剪测试资产。
4. `plastx` / `tplastx` / `plastn` 三个核酸算法本轮只做了单元测试级覆盖，未做 CLI 级端到端实跑。
5. **shadow CI**：**已通过——构建 #93740**（L0 结构完整性、L1 测试执行验证、`Conan test_package` 全部通过）。获得该结果前经历 5 次失败（#93278 / #93345 / #93397 / #93409 / #93525），其中只有 #93278 是本包范围内的真问题（CI worker 的 HMDFS 不支持 FIFO 导致 make jobserver 失效、递归 make fork 耗尽，**E074 + P020**，已按 E074 固定 `-j1` 并真机复验）；其余 4 次失败时**没有任何并行**（编译 CMake 自带的 3 行 `testCCompiler.c`、或仅 `source` 一个环境脚本），跨 4 个 worker，属 worker 侧进程创建资源耗尽，详见问题 11、13 与 `reports/device-verification.md` §9。

### 改动范围

- `archives/p/plast/**`（含新增的软件级 `manifest.yaml` 与 `README.md`、`commands.json`）
- `knowledge/drafts/` 下 3 组与 plast 直接相关的草稿
- `.gitignore` 中新增一条 `!archives/p/plast/2.3.2/reports/` 白名单（仓库既有惯例：`reports/` 被全局忽略，
  需逐包放行；参考 `protomol` / `pen` / `lz4` 等 500+ 个 `reports/*.md` 先例）

未修改任何基础设施脚本（`SKILL.md` / `references/` / `templates/` / `scripts/` / `ci/` / `index.tsv` / `SUMMARY.md`）。
