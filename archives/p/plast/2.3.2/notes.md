# plast 2.3.2 — HarmonyOS 适配笔记

## 1. 软件概述

| 项目 | 值 |
|------|-----|
| 名称 / 版本 | plast / 2.3.2（上游 2017-07 发布，此后无更新） |
| 上游主页 | https://plast.inria.fr/ |
| 源码仓库 | https://github.com/PLAST-software/plast-library（`plast.inria.fr/developer-guide` 指向的官方组织） |
| 许可证 | AGPL-3.0-only |
| 语言 / 标准 | C++11（含 3 个 C 翻译单元：内置 PCRE 8.31 与 SEG） |
| 构建系统 | CMake（`cmake_minimum_required 2.6`），单配置生成器 |
| 产物 | `lib/libPlastLibrary.a`、`bin/PlastCmd`、`bin/makeplastdb`、`include/**` |
| 上游测试 | CppUnit 单元测试程序 `PlastLibraryTest`：19 个测试文件共 119 处 `new TestCaller`，剔除 11 处注释禁用后为 **108**，其中 12 处位于整文件 `#if 0` 的 `TestMisc.cpp` → **实际编译并运行 96 个用例**（`OK (96 tests)`，本环境 88 个实执行断言通过）+ 自定义 `test` target |

PLAST 是 bank-to-bank（库对库）的序列相似性搜索工具，常与 BLAST 对比，支持
`plastp`（蛋白）、`plastx`/`tplastx`（翻译核酸）、`plastn`/`tplastn`（核酸）五种算法。
库本身是静态库 + 自带 CLI，另有可选 JNI 绑定供 Java 侧调用。

## 2. 构建系统与源码分析结论

### 2.1 源码结构

```
CMakeLists.txt          # 顶层：平台宏、编译选项、add_subdirectory(src/test/doc/examples/tools)
src/                    # 全部 C++ 源码 + 内置 PCRE 8.31（src/pcre）+ SEG（src/seg）
  algo/                 # 算法核心，hits/ 下是两级 SIMD 迭代器
  launcher/core/        # PlastCmd（CLI 逻辑）、PlastOptionsParser（选项表）
  launcher/jni/         # 可选 JNI 绑定（8 个文件 #include <jni.h>）
  os/impl/              # 平台抽象：Linux*/MacOs*/Windows* 三套实现
tools/                  # PlastCmd.cpp、makeplastdb.cpp
test/unit/src/          # CppUnit 测试（main.cpp 注册 18 个 suite）
test/db/                # FASTA fixture（query.fa / tursiops.fa / sapiens_1Mo.fa ...）
```

### 2.2 平台相关面（决定适配方案的三处）

1. **x86 SIMD 内建指令**
   整个工程的 `_mm_*` / `__m128i` 只出现在 3 个翻译单元：

   | 文件 | `_mm_*`/`__m128i` 出现次数 |
   |------|------|
   | `src/algo/hits/gap/SmallGapHitIteratorSSE8.cpp` | 54 |
   | `src/algo/hits/ungap/UngapHitIteratorSSE8.cpp` | 22 |
   | `src/algo/hits/ungap/UngapHitIteratorSSE16.cpp` | 21 |

   对应的 `.hpp` 头文件**不含**任何 x86 类型，所以只有 `.cpp` 需要处理。
   上游 README 写的是 “Hardware: Intel/AMD 64bit processor providing SSE2+ instructions set”。

   两条可选路线：
   - **（选用）SIMDe**：把 `#include <pmmintrin.h>/<emmintrin.h>` 换成
     `#define SIMDE_ENABLE_NATIVE_ALIASES` + `#include <simde/x86/sse3.h>`，
     `_mm_*` 在 aarch64 上映射到 NEON。**kernel 语义完全不变**，与前缀过滤、
     去重逻辑（`_alignmentResult->doesExist(...)`）保持一致。
     Debian 的 `simde.patch` 与上游 PR PLAST-software/plast-library#8 用的就是这条路。
   - （未选用）退化到标量迭代器：`-factory-hit-ungap UngapHitIterator` +
     `-factory-hit-smallgap SmallGapHitIterator` 是运行期可选项，但二者的判定逻辑
     与 SSE 版本**并不等价**——SSE 版本会额外用 `_alignmentResult->doesExist()` 过滤
     已存在的比对，标量版本会保留这些 hit。因此该方案会改变结果集去重行为，仅在
     SIMDe 不可用时才作为兜底。

   `ohpcd` 制品仓已有 `simde/0.8.2`（header-only，`cmake_target_name=simde::simde`），
   因此选 SIMDe 路线不需要新增待适配依赖。

2. **平台宏 `__LINUX__`**
   `CMakeLists.txt` 只在 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 时追加 `-D__LINUX__`；
   而 `src/misc/api/types.hpp`、`src/os/impl/DefaultOsFactory.cpp`、
   `Linux{File,Memory,MemoryFile,Thread,Time}.cpp` 全部由该宏控制。
   OHOS 下 conan 把 `CMAKE_SYSTEM_NAME` 映射成 `HarmonyOS`（见 E092/E140），
   不处理会出现两个后果：

   - `types.hpp` 走 `__intN_t`/`__attribute__((__mode__))` 分支，与 `<stdint.h>` 冲突；
   - `DefaultFactory` 构造函数里 `_thread/_time/_file/_memory/_fileMem` **全部不被赋值**，
     运行期直接空指针崩溃。

   处理方式采用本仓库既有约定（E092）：`tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`。
   这样既让 `-D__LINUX__` 生效，也绕开 CMake 没有 HarmonyOS platform module 的问题，
   无需再改 CMakeLists 的平台判断分支。

3. **JDK / JNI**
   顶层 `find_package (JNI REQUIRED)`，且 `src/CMakeLists.txt` 用
   `file(GLOB_RECURSE LibraryFiles ./*)` 把 `src/launcher/jni/*.cpp` 全部收进静态库。
   OHOS 上没有 JDK，`ohpcd` 也没有 `openjdk`/`jdk` 配方
   （`conan download openjdk/17.0.9|21.0.2|11.0.20 -r=ohpcd --only-recipe`
   全部返回 `system acceleration policy not enabled`）。
   因此把 JNI 改成可选：找不到 JDK 时排除 `launcher/jni` 并打印提示，
   **Java 绑定在 OHOS 上不参与构建**（C++ 库与两个 CLI 工具功能完整）。
   若将来有 JDK，`find_package(JNI)` 命中后会自动恢复编译 JNI，无需再改配方。

### 2.3 编译选项

上游非 debug 分支硬编码 `-O3 -funroll-loops -fomit-frame-pointer -msse3`。
`-msse3` 在 aarch64 上会让 clang 直接报错（不是警告），必须按目标架构条件化；
启用 SIMDe 后也**不应**再传任何 x86 ISA 标志，否则会强制走原生 x86 路径。

### 2.4 其它已识别但不阻塞的点

| 现象 | 说明 | 处理 |
|------|------|------|
| `cmake_minimum_required (VERSION 2.6)` 且写在 `project()` 之后 | CMake 4 已移除 <3.5 兼容；`project()` 先于 `cmake_minimum_required()` 也是弃用用法 | 补丁 0001 |
| `test/runTest.sh` 从 `plast.gforge.inria.fr` 下载测试数据 | 该域名已无法解析；`test/db/` 内已自带 fixture | 补丁 0005 |
| `test` target 用 `<build>/bin/PlastLibraryTest` | 实际可执行文件在 `${PROJECT_BINARY_DIR}/bin/${CMAKE_BUILD_TYPE}`，单配置生成器下不匹配 | 补丁 0005，改用 `$<TARGET_FILE:...>` |
| `install(FILES .../version.hpp DESTINATION include/os/api/)` | 生成的 `misc/api/version.hpp` 被装到了 `include/os/api/`，源码树里的 `unstable-master` 占位头反而进了包 | 真机确认后由补丁 0013 修复（见 §4 R3） |
| `examples` 子目录虽写成 `add_custom_target(examples ALL ...)`，但顶层用的是 `ADD_SUBDIRECTORY(examples EXCLUDE_FROM_ALL)` | **真机构建树实测：11 个 example 目标存在但一个都没编译**（`build/Release/examples` 下只有 CMakeFiles 元数据、0 个 `.o`；全程 5 次链接里没有 example），即默认 `all` 并不包含它们（需显式 `make examples`）——`EXCLUDE_FROM_ALL` 的排除优先于子目录内的 `ALL` | 不改；仅记录本行结论（此前"会被默认构建"的判断有误，已按实测更正） |
| `src/pcre` 内置 PCRE 8.31 | 随 `GLOB_RECURSE` 一起编译，无外部依赖 | 不改（Debian 才需要换 PCRE2） |
| `ZlibFile.cpp` 整体被 `#if 0` 包住 | 因此**不需要** zlib 依赖 | 不声明 zlib |
| `src/algo/hits/hsp/HspGeneratorCmd.cpp` 里有 x86 内联汇编 `__asm__ ("popcnt %1, %0" ...)` | 已确认**处于注释块内**，实际走的是可移植 Hamming weight popcount | 不需要补丁 |
| `src/algo/stats/impl/StatisticsPlastn.cpp:415` 的 `register double innerSum;` | OHOS profile `cppstd=17`，C++17 已移除 `register` 存储类说明符，clang 会直接报错 | 补丁 0006 |
| `test/unit/CMakeLists.txt` 用裸 `FIND_PATH/FIND_LIBRARY` 找 CppUnit | 把 conan 的 include 目录预置到 `CPPUNIT_INCLUDE_DIR` 即可；`FIND_LIBRARY` 会通过 `<include>/../lib` 提示找到 `libcppunit.a` | 配方 `generate()` |
| `PLAST_*` 版本宏来自 `configure_file` | `PLAST_VERSION` == `"2.3.2"` | test_package 用作断言 |
| `makeplastdb` 生成 `<bank>.fa.info` | CLI 的 `DatabaseLookupType::quickReaderType()` 只识别 `.fa/.pal/.nal/.pin/.nin`，`.info` 会落回按 FASTA 处理，故**不串联** `PlastCmd -d <bank>.info` | test.sh 只校验 `.info` 生成成功 |

## 3. W0 依赖检查结果（本机执行）

```text
conan download "simde/0.8.2"    -r=ohpcd --only-recipe   → OK  (cf73fc62791d361d34d8e83341280ef7, 2026-09-10)
conan download "cppunit/1.15.1" -r=ohpcd --only-recipe   → OK  (a1e38dc3ed3d631d60a27e7f6eec70ce, 2026-07-23)
conan download "openjdk/17.0.9" -r=ohpcd --only-recipe   → ERR system acceleration policy not enabled
conan download "openjdk/21.0.2" -r=ohpcd --only-recipe   → ERR system acceleration policy not enabled
conan download "jdk/17"         -r=ohpcd --only-recipe   → ERR system acceleration policy not enabled
```

结论：

- 正式依赖（simde、cppunit）**均已发布**，无需先拆依赖库 PR；
- JDK 类配方不存在 → JNI 只能做成可选（不阻塞主体适配）；
- `cppunit/1.15.1` 在上游归档中状态为 `published`，且已带 HarmonyOS 的
  `config.guess`/`config.sub` 补丁，说明该依赖本身在 OHOS 上已验证过。

## 4. 风险与已知限制

| # | 风险 | 级别 | 说明 / 处置 |
|---|------|------|------|
| R1 | `plast-libraries` 固定链接 `dl pthread` | ✅ 已排除 | 真机 `conan create` 链接通过，无告警；产物 `NEEDED` 仅 `libc++_shared.so` + `libc.so`。无需条件化补丁。 |
| R2 | 包内包含 `test/db/`（`tursiops.fa` 11.9 MB + `sapiens_1Mo.fa` 1 MB）与 `PlastLibraryTest` | 低 | 上游 `install()` 行为，未裁剪；包体积偏大。如需精简应在独立 PR 中讨论，避免本轮改动上游测试资产。 |
| R3 | `install(... version.hpp DESTINATION include/os/api/)` 路径笔误 | ✅ 已修复 | 真机证实包内 `include/misc/api/version.hpp` 是源码树里的 `unstable-master` 占位头（`PLAST_VERSION=unstable-master`），已由补丁 0013 修正为安装到 `include/misc/api/`，test_package 断言现在得到 `2.3.2`。 |
| R4 | `examples` 是否会被默认构建 | ✅ 已排除（实测更正） | 真机构建树显示默认 `all` **不编译** 11 个示例（0 个 `.o`、5 次链接里无 example），需显式 `make examples`；即不存在"额外 11 个可执行文件的构建负担"。详见 §2.4。 |
| R5 | `testThread1` 是重负载性能测试 | ✅ 已排除 | 真机整轮单测（含该用例）与 `conan create` 全流程可接受，无需额外超时。 |
| R6 | Java/JNI 绑定未适配 | 中 | 明确的**功能裁剪**：OHOS 无 JDK，`src/launcher/jni` 不参与构建。C++ API、`PlastCmd`、`makeplastdb` 全部保留。真机日志确认打印了 `JNI not found: building PLAST without the Java binding`。 |
| R7 | 上游 2017 年后不再更新 | 低 | 无上游回归支持；补丁全部是 portability 性质，语义改动为零。 |
| R8 | 8 个上游用例依赖 release 归档未附带的 `test/db` 语料 | 中 | 上游从已失效的 `plast.gforge.inria.fr` 下载完整语料；补丁 0011 让这些用例显式 skip 并打印缺失文件名，清单见 `reports/device-verification.md` §3。属**有证据的测试裁剪**，非遗漏。 |
| R9 | **CI 构建并行度**：`-j20` 在 CI worker 上 fork 耗尽，表现为「无编译诊断的编译失败」 | ✅ 已修复 | 首次 shadow CI（构建 #93278）报 `make: jobserver mkfifo: ... Operation not permitted` → `/bin/sh: can't fork - try again` → `Error 127`/`Error 1`。根因 **E074 + P020**：HMDFS 不支持 FIFO，GNU make jobserver 退化为 pipe，递归 make 在拿不到有效 jobserver 时按无限并行运行，PLAST 146 个源文件在 20 路并发下瞬间打满进程配额。处置：`build()` / `target="test"` / test_package 三处 `cmake.build(build_tool_args=["-j1"])`（对齐仓库既有 10 处先例）。实机复验 `EXITCODE=0`、363s、`can't fork` 0 次，详见 `reports/device-verification.md` §9。 |
| R10 | **CI 第 2–5 次构建（#93345 / #93397 / #93409 / #93525）均在「能否创建进程」这一层失败，且跨 4 个 worker** | ⚠️ 判定为 **worker 侧进程创建资源耗尽**，非本库缺陷 | #93345（CI-026）：`-j1` 生效、编译全程通过（83% 静态库链接成功、96% 测试目标编译完成），末步链接 `PlastLibraryTest` 报 `clang-15: ... posix_spawn failed: Resource temporarily unavailable`。#93397（CI-013）与 #93525（CI-035）：CMake 编译器探测阶段编译其自带的 3 行 `testCCompiler.c` 时 `make[1]: /bin/sh: Resource temporarily unavailable` → `Error 127`，**两次签名完全一致**（同一 `CMakeTestCCompiler.cmake:67`），#93525 全程仅 29 s；两次构建均 **L0/KC/JC/G0 全绿（`Errors: 0`）**。#93409（CI-010，push 自动触发）：连 `cmake` 都未启动，`conanbuildenv-release-armv8.sh[13]: can't fork - try again`（日志同时显示 13 个补丁全部按序应用成功）。五次失败分布在**编译 / 链接 / 编译器探测 / 环境脚本**四个阶段、后三次**零并行**、**四个 worker**，任何配方或并行度改动都无法同时解释。旁证：该 worker 的 conan 缓存中 #93345 运行区间内同时存在另一个包 `xeus` 的构建目录（19:01 / 19:08）；CI 构建墙同期最近 50 条记录 **24 条失败、17 条同时在跑**。反证：同一链接命令（CMake `link.txt`，1 448 B）在同机连续执行 10 次全部成功；真机完整 `conan create` 三次全部 `EXITCODE=0`。处置：保留 `-j1`、重跑。**最终结果：同一 head 在负载回落后重跑通过——构建 #93740，L0/L1/`test_package` 全绿**，证明这 4 次失败与代码无关。 |

## 5. 补丁清单

| 补丁 | 文件 | 作用 |
|------|------|------|
| 0001 | `CMakeLists.txt` | `cmake_minimum_required` 2.6 → 3.10，并前移到 `project()` 之前 |
| 0002 | `CMakeLists.txt`, `src/CMakeLists.txt` | `find_package(JNI)` 改为非必需；无 JDK 时排除 `launcher/jni` |
| 0003 | `CMakeLists.txt` | `-msse3` 仅在 x86 目标上传递 |
| 0004 | `src/CMakeLists.txt`, 3 个 SSE `.cpp` | 三个 SIMD kernel 改用 SIMDe 头（语义不变）+ 注入 `SIMDE_INCLUDE_DIR` |
| 0005 | `test/CMakeLists.txt` | 上游 `test` target 使用仓库内 fixture 与 `$<TARGET_FILE:PlastLibraryTest>` |
| 0006 | `src/algo/stats/impl/StatisticsPlastn.cpp` | 去掉 C++17 已移除的 `register` 存储类说明符（OHOS profile `cppstd=17`） |
| 0007 | `src/designpattern/impl/SystemCommand.cpp` | `SystemCommand` 临时文件改用 `TMPDIR`（OHOS 上 `/tmp` 只读） |
| 0008 | `test/unit/src/{cppunit.h,TestAlignment,TestDesignPattern,TestPlast,TestSequenceIterator}.cpp` | 单测临时文件改用 `TMPDIR`，不再硬编码 `/tmp` |
| 0009 | `src/os/impl/CommonOsImpl.hpp` | `fgetc` 结果用 `int` 承载：`char` 在 aarch64 上无符号，EOF 哨兵失效导致死循环 |
| 0010 | `test/unit/src/main.cpp` | 测试 runner 打印失败详情并返回非零状态（原先失败被静默吞掉、恒 `return 0`） |
| 0011 | `test/unit/src/{cppunit.h,TestDesignPattern,TestSequenceDatabase,TestSequenceIterator,TestSequenceMask}.cpp` | 8 个依赖归档未附带 fixture 的用例显式 skip 并打印原因 |
| 0012 | `src/database/impl/ReadingFrameSequenceIterator.{hpp,cpp}` | 阅读框方向值用 `int`：`char` 的 -1 在 aarch64 变 255，反向链索引越界（结果错误 + 段错误） |
| 0013 | `src/CMakeLists.txt` | 生成的 `misc/api/version.hpp` 安装到规范路径，避免包内 version 宏停留在 `unstable-master` |

全部补丁为本机 `git apply` 逐个验证通过（见 `reports/local-preverification.md`），
并已在真机 `conan create` 全流程中生效（见 `reports/device-verification.md`）。
生成方式：把官方源码解包为 pristine 基线（`git init` + 首次提交），逐条修改后用
`git diff` 导出 unified diff，再用**全新解包**的源码按顺序 `git apply` 复验；
等价于 `refresh-patch --auto` 的 per-file difflib 流程（本机无法运行 ohc-run.py）。

### 知识草稿

本库适配过程中沉淀了 3 份草稿（仅与本库直接相关），随 PR 提交到 `knowledge/drafts/`：

```text
knowledge/drafts/E999-draft-cxx17-register-storage-class.{kv,md}
knowledge/drafts/E999-draft-aarch64-unsigned-char-eof-sentinel.{kv,md}
knowledge/drafts/E999-draft-aarch64-unsigned-char-negative-index.{kv,md}
```

**与 `main` 上既有条目的关系（已逐条比对，不主张重复的新模式）**：

| 草稿 | 既有条目 | 本稿的增量 |
|------|----------|-----------|
| `cxx17-register-storage-class` | **E293**（其 error signature 已含 `ISO C++17 does not allow 'register' storage class specifier`） | 本库实例 + `grep` 预扫描命令 + 「删除后语义不变」依据 + 禁止 `#define register`/`-Wno-register` 的边界；`similar_to` 已指向 **E293** |
| `aarch64-unsigned-char-eof-sentinel` | **E419**（plain char 符号性）与既有草稿 **`DRAFT-8543-plain-char-eof-sentinel-infinite-loop`**（同一模式） | 本库触发条件（表头 115 字符 > `commentMaxSize=100` 且末行无换行）、`-Wtautological-constant-out-of-range-compare` 线索在既有构建日志中已出现却未被处理、`int c = (unsigned char) tmp[...]` 取初值写法；`similar_to` 已指向 **E419** |
| `aarch64-unsigned-char-negative-index` | **E419**（同根，但描述的是取值语义变化） | **新增失败模式**：窄化发生在 `return` 语句内（编译器不告警）→ -1 变 255 → 被当作数组下标 → 小输入静默错、大输入 SIGSEGV；并明确**禁止只 clamp 索引**（崩溃消失但结果依旧错误）。`similar_to` 已指向 **E419** |

三份草稿均包含症状、根因、修复边界、禁止做法与可复核日志。
知识贡献之外，本库在真机上定位并修复了 **2 个上游产品代码的功能性缺陷**
（补丁 0009 EOF 哨兵失效导致死循环、补丁 0012 反向阅读框索引越界导致结果错误 + 段错误），
二者同根（aarch64 `char` 默认无符号）但错误特征、触发阶段与定位手段不同；
连同 E074 的 CI 并行度修复（R9/R10），适配路径记为
**路径 A（基础适配）+ 路径 B（贡献创新）**。草稿随本库 PR 提交，
不改动正式 `knowledge/graph/index.tsv`。

PR 正文（积分赛事模板）见 `reports/pr-body.md`。

## 6. 下一步（shadow CI / 发布）

真机 `conan create` 已通过（`EXITCODE=0`，详见 `reports/device-verification.md`）。

shadow CI 共触发 6 次，**最终第 6 次通过**：

| 构建 | head | worker | 结果 | 结论 |
|------|------|--------|------|------|
| #93278 | `f43b0905` | CI-026 | 失败：编译（`-j20`）fork 耗尽 | 根因 E074 + P020，已由 `-j1` 修复（R9） |
| #93345 | `e72cc95c` | CI-026 | 失败：链接 `PlastLibraryTest` | `-j1` 生效、编译全程通过（96%），`posix_spawn` EAGAIN（R10） |
| #93397 | `299c047d` | CI-013 | 失败：CMake 编译器探测 | 编译 3 行 `testCCompiler.c` 即 `can't fork`；同次 **L0/KC/JC/G0 全绿**（R10） |
| #93409 | `fa4b0e2173` | CI-010 | 失败：source conan 环境脚本 | 连 `cmake` 都未启动，13 个补丁已全部应用成功（R10） |
| #93525 | `22224671` | CI-035 | 失败：CMake 编译器探测（同 #93397） | 签名与 #93397 完全一致、全程 29 s；同次 **L0/KC/JC/G0 全绿**（R10） |
| **#93740** | `5cb9b093` | CI-001 | ✅ **校验通过** | `L0 门禁通过` + `L1 门禁通过` + `Conan test_package 通过`，7 步全绿 |

即：前 5 次中只有 #93278 是本包范围内的真问题（已修），其余 4 次是 worker 侧进程创建资源
竞争，负载回落后同一份代码直接通过。

剩余步骤：

```bash
# 1) 单包 shadow CI（不要无参数扫描全仓）——已通过（#93740）
CI_PACKAGES="archives/p/plast/2.3.2" zsh ci/conan/build_and_test.sh
# 或
/path/to/run-ohos-shadow-ci.sh archives/p/plast/2.3.2
```

提交前对照检查单（工作流 §4）：

- build 日志只发现目标包，`Build Summary` 为 `Total: 1`；
- L0 全绿（L0m 目录结构、L0i 依赖已发布、L0k `commands.json`）——**#93740 已确认通过**；
- L1：`test_package` 已执行，上游单测在 `build()` 内运行——**#93740 已确认通过**；
  用例口径四个数要分清：源码注册语句 **119**、未被注释禁用 **108**、实际编译并启动 **96**
  （CppUnit 汇总行 `OK (96 tests)` 是启动计数）、本环境实际执行断言并通过 **88**
  （8 例因归档缺 fixture 早退）；
- L2：`PlastCmd -h` 可执行（本次已验证）；
- L4/L5：`readelf` NX/PIE/RELRO 与产物基线（本次已确认 aarch64 + 仅 `libc++_shared.so`/`libc.so`）。

仍待人工决定的事项：

1. 8 个 skip 用例是否需要在 PR 说明中进一步标注（清单见 `reports/device-verification.md` §3）；
2. `plastx` / `tplastx` / `plastn` 三个核酸算法的端到端实跑（本轮只手动跑了 `plastp`，
   其反向阅读框路径已由单测覆盖）；
3. JNI/Java 绑定是否作为后续独立适配项排期；
4. `TestMisc` 的 12 个用例上游 `main.cpp` 从未注册——保持上游行为未改动，
   是否需要在后续版本向上游反馈由维护者决定；
5. `conan upload` 到 release 流水线（本轮归档状态保持 `built`）。
