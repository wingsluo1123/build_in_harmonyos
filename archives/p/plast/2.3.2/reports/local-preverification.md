# plast 2.3.2 — 本机前置验证报告

> 本轮**未取得真机空闲窗口**，因此按「一库一分支并行适配工作流」§3.4 只做本机轻量验证：
> 源码/哈希、补丁可用性、配方可被 Conan 加载、依赖可解析、测试脚本与数据静态检查。
> 任何 `conan create` / shadow CI 结论都不在本报告中出现。

- 日期：2026-10-15
- 主机：Windows（本机），conan 2.29.1（Anaconda），remote `ohpcd` = https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/
- 目标 profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / Release）

## 1. 源码 URL 与 sha256

| 检查 | 命令 | 结果 |
|------|------|------|
| 下载 #1 | `curl -L -o plast-2.3.2.tar.gz https://codeload.github.com/PLAST-software/plast-library/tar.gz/refs/tags/v2.3.2` | 7 150 500 bytes |
| sha256 #1 | `Get-FileHash -Algorithm SHA256` | `9068b4904fa638c57e427eedd1682cd74eba0e1478f9256ecf1768bc538f08d6` |
| 完整性 | `tar -xzf` 全量解包 | OK，423 个文件 |
| 下载 #2（完整重下） | 同上 | 7 150 500 bytes，sha256 **完全一致** |
| 与 conandata.yml 比对 | — | ✅ 一致 |

> 期间的第一次“不一致”已定位为**传输被截断**（6 286 023 bytes，`tar` 报
> `Truncated tar archive detected`，仅 395 个文件），非归档不确定；完整重下后哈希稳定。
> 上游历史下载站 `plast.gforge.inria.fr` 的 DNS 已不存在，故使用 `plast.inria.fr`
> developer-guide 指向的官方 GitHub 组织 `PLAST-software` 的 tag 归档（R39 合规）。

## 2. 补丁可用性

对 **原始未修改源码**（`plast-library-2.3.2` 全新解包）按 conandata.yml 声明顺序执行：

**全部 13 个补丁**逐条 `git apply --check -v`，随后按同一顺序 `git apply` 落盘
（复现命令：把 pristine `plast-library-2.3.2` 复制到空目录 → `git init` + 基线提交 →
按下表顺序对每个补丁执行 `git apply --check -v` 与 `git apply`）：

```text
applied OK  0001-cmake-minimum-required.patch
applied OK  0002-cmake-optional-jni.patch
applied OK  0003-cmake-portable-cpu-flags.patch
applied OK  0004-simde-portable-simd-kernels.patch
applied OK  0005-test-in-tree-db-fixtures.patch
applied OK  0006-cxx17-drop-register.patch
applied OK  0007-systemcommand-tmpdir.patch
applied OK  0008-unit-tests-tmpdir.patch
applied OK  0009-fgetc-eof-unsigned-char.patch
applied OK  0010-test-runner-report-failures.patch
applied OK  0011-skip-unavailable-fixture-tests.patch
applied OK  0012-reading-frame-unsigned-char.patch
applied OK  0013-install-generated-version-header.patch
```

累计 diff（对基线提交执行 `git diff --stat`，即 13 个补丁叠加后的净效果）：

```text
 CMakeLists.txt                                     | 17 +++++--
 src/CMakeLists.txt                                 | 18 +++++++-
 src/algo/hits/gap/SmallGapHitIteratorSSE8.cpp      | 14 ++----
 src/algo/hits/ungap/UngapHitIteratorSSE16.cpp      | 14 ++----
 src/algo/hits/ungap/UngapHitIteratorSSE8.cpp       | 14 ++----
 src/algo/stats/impl/StatisticsPlastn.cpp           |  3 +-
 src/database/impl/ReadingFrameSequenceIterator.cpp |  2 +-
 src/database/impl/ReadingFrameSequenceIterator.hpp |  8 +++-
 src/designpattern/impl/SystemCommand.cpp           | 10 +++-
 src/os/impl/CommonOsImpl.hpp                       |  9 +++-
 test/CMakeLists.txt                                | 14 +++++-
 test/unit/src/TestAlignment.cpp                    | 21 +++++----
 test/unit/src/TestDesignPattern.cpp                | 14 +++++-
 test/unit/src/TestPlast.cpp                        | 17 ++++---
 test/unit/src/TestSequenceDatabase.cpp             |  5 ++
 test/unit/src/TestSequenceIterator.cpp             | 12 ++++-
 test/unit/src/TestSequenceMask.cpp                 |  2 +
 test/unit/src/cppunit.h                            | 54 ++++++++++++++++++++++
 test/unit/src/main.cpp                             | 10 +++-
 19 files changed, 198 insertions(+), 60 deletions(-)
```

补丁内容静态复核：

- 打补丁后 `src/**/*.cpp` 中不再存在 `pmmintrin.h` / `emmintrin.h` 引用；
- 三个 SIMD 翻译单元均已改为 `#define SIMDE_ENABLE_NATIVE_ALIASES` + `#include <simde/x86/sse3.h>`；
- `CMakeLists.txt` 的 `IF(${CMAKE_SYSTEM_NAME} MATCHES "Linux")` 分支未被破坏
  （`-D__LINUX__` 仍会在 `CMAKE_SYSTEM_NAME=Linux` 时注入，配方按 E092 覆盖该变量）；
- 补丁文件为 UTF-8 无 BOM、LF 换行（`CR` 计数 = 0），可用 `git apply -p1` 与 `patch -p1` 消费。

**pristine 源码上的量化复核**（在未打补丁的 `plast-library-2.3.2` 上逐条实测，用于支撑
`notes.md` §2 的判断）：

| 结论 | 复核方式 | 实测 |
|------|----------|------|
| x86 SIMD 面收敛在 3 个翻译单元 | 统计**含 `_mm_` 或 `__m128i` 的行数** | `SmallGapHitIteratorSSE8.cpp` **54**、`UngapHitIteratorSSE8.cpp` **22**、`UngapHitIteratorSSE16.cpp` **21**；其余 `src/` 文件 0 处 |
| 配对的 `.hpp` 不含 x86 类型 | 同上，对 3 个 `.hpp` | 0 / 0 / 0 → 只需改 `.cpp` |
| 平台宏确实只由 `CMAKE_SYSTEM_NAME` 决定 | 读根 `CMakeLists.txt` | 第 53–55 行：`IF(${CMAKE_SYSTEM_NAME} MATCHES "Linux")` → `-D__LINUX__`；Darwin(49)/Windows(57) 为并列分支 |
| 缺 `__LINUX__` 会让工厂指针不初始化 | 读 `src/os/impl/DefaultOsFactory.cpp` | `_thread/_time/_file/_memory/_fileMem` 仅在 `#ifdef __LINUX__`(51–56) / `__WINDOWS__`(59–64) / `__DARWIN__`(67–72) 内赋值，无 `#else` 兜底 |
| `types.hpp` 依赖 `__LINUX__` 选择整型定义 | 读 `src/misc/api/types.hpp` | 第 41–45 行：`__LINUX__`/`__DARWIN__` 分支用 `__attribute__((__mode__))` 定义 `__intN_t`/`__u_intN_t` |
| 全库源码用通配收集 | 读 `src/CMakeLists.txt` | 第 28 行 `file (GLOB_RECURSE LibraryFiles ./*)`（含 `src/pcre`、`src/launcher/jni`） |
| 内置 PCRE 版本 | 读 `src/pcre/pcre.h` | `PCRE_MAJOR 8` / `PCRE_MINOR 31` |
| JNI 绑定规模 | 统计 `#include <jni.h>` | 8 个文件（`Helper.hpp`、`Wrapper.hpp` 与 6 个 `org_inria_*` 头） |
| `ZlibFile.cpp` 整文件被禁用 | 读 `src/os/impl/ZlibFile.cpp` | 第 17 行 `#if 0`，第 135 行 `#endif` → 不需要 zlib |
| x86 内联汇编不在生效路径 | 读 `src/algo/hits/hsp/HspGeneratorCmd.cpp:68` | `__asm__ ("popcnt %1, %0" ...)` 位于 `/* ... */` 注释块内 |
| `test/unit` 用裸查找定位 CppUnit | 读 `test/unit/CMakeLists.txt` | 第 4 行 `FIND_PATH (CPPUNIT_INCLUDE_DIR ...)`、第 9 行 `FIND_LIBRARY (CPPUNIT_LIBRARY ...)` |
| `benchmark`/`examples` 不参与默认构建 | 读 `CMakeLists.txt` / `examples/CMakeLists.txt`，并在真机构建树核对产物 | `ADD_SUBDIRECTORY(benchmark EXCLUDE_FROM_ALL)`、`ADD_SUBDIRECTORY(examples EXCLUDE_FROM_ALL)`；真机 `build/Release/examples` 下 0 个 `.o` |

### 2.1 通过静态扫描发现的真实阻塞点

| 发现 | 位置 | 判定 | 处置 |
|------|------|------|------|
| `register double innerSum;` | `src/algo/stats/impl/StatisticsPlastn.cpp:415`（**C++ 源文件、非注释**） | **阻塞**：OHOS profile 为 `compiler.cppstd=17`，CMakeToolchain 会传 `-std=c++17`，而 C++17 已移除 `register` 存储类说明符，clang 报 `error: ISO C++17 does not allow 'register' storage class specifier` | 补丁 0006：删掉 `register`（该关键字本就是无效果的优化提示，语义不变） |
| `__asm__ ("popcnt %1, %0" : "=r" (x) : "0" (x));` | `src/algo/hits/hsp/HspGeneratorCmd.cpp:68` | **非阻塞**：位于 `/* ... */` 注释块内，生效代码是可移植的 Hamming weight popcount | 不需要补丁 |
| `register int len;` | `src/seg/api/seg.h:50` | **非阻塞**：该头文件只被 `seg.c` / `genwin.c` 包含，按 C 编译（C17 仍允许 `register`） | 不需要补丁 |

其它已扫描确认**不存在**的 C++17 风险项：`std::auto_ptr`、`std::unary_function`/`binary_function`、
`std::random_shuffle`、`std::bind1st`/`bind2nd`、`std::ptr_fun`/`mem_fun`、动态异常规格 `throw(T)`、
`<ext/...>`/`<tr1/...>` 头、内联汇编（除上述注释）。

## 3. 配方 / 测试脚本静态检查

| 检查 | 命令 | 结果 |
|------|------|------|
| Python 语法 | `python -c "ast.parse(...)"` | `conanfile.py`、`test_package/conanfile.py` AST OK |
| YAML 语法 | `python -c "yaml.safe_load(...)"` | `conandata.yml`、`manifest.yaml`、`test_package/MANIFEST.yml` OK |
| JSON 语法 | `python -c "json.load(...)"` | `archives/p/plast/commands.json` OK（name=plast, type=tool, versions=[2.3.2]） |
| Shell 语法 | `bash -n test_package/test.sh` | OK |
| L0h（R33） | grep `self.run(...${...})` | 无裸 shell 变量依赖 |
| L0g | grep `-r=` / `--remote` | 无硬编码 remote |
| R32 | `conan graph info -s os=Windows ...` | `validate()` 正确判为 Invalid configuration |
| 换行 | 字节级 CR 计数 | 所有新增文件 CR = 0 |

### 3.1 Conan 2 加载 / 依赖解析（关键）

```text
$ cd archives/p/plast/2.3.2
$ conan graph info . -s os=Linux -s arch=x86_64 -s compiler=gcc -s compiler.version=11 \
                    -s compiler.libcxx=libstdc++11 -s build_type=Release

======== Computing dependency graph ========
Graph root
    conanfile.py (plast/2.3.2): .../archives/p/plast/2.3.2/conanfile.py
Requirements
    cppunit/1.15.1#a1e38dc3ed3d631d60a27e7f6eec70ce - Cache
    simde/0.8.2#cf73fc62791d361d34d8e83341280ef7 - Cache
======== Computing necessary packages ========
Requirements
    cppunit/1.15.1#a1e38dc3...:48da328f... - Missing     # 本机只有 OHOS profile 的 binary
    simde/0.8.2#cf73fc62...:d332de66...    - Missing     # （header-only，真机会本地构建）
```

首次运行暴露并已修复一个真实配方缺陷：
`package_type = "library"` 需要声明 `shared` 选项，Conan 2 直接报
`Package type is 'library', but no 'shared' option declared`；
上游只构建静态目标（`PlastLibrary-dynamic` 在 `src/CMakeLists.txt` 中被注释掉），
因此已改为 `package_type = "static-library"`。

## 4. W0 依赖发布检查（本机执行，R35：用 download 而非 list）

```text
conan download "simde/0.8.2"    -r=ohpcd --only-recipe  ->  cf73fc62791d361d34d8e83341280ef7 (2026-09-10)
conan download "cppunit/1.15.1" -r=ohpcd --only-recipe  ->  a1e38dc3ed3d631d60a27e7f6eec70ce (2026-07-23)
conan download "openjdk/17.0.9" -r=ohpcd --only-recipe  ->  ERROR system acceleration policy not enabled
conan download "openjdk/21.0.2" -r=ohpcd --only-recipe  ->  ERROR system acceleration policy not enabled
conan download "openjdk/11.0.20"-r=ohpcd --only-recipe  ->  ERROR system acceleration policy not enabled
conan download "jdk/17"         -r=ohpcd --only-recipe  ->  ERROR system acceleration policy not enabled
```

结论：构建依赖已发布，无需拆依赖库 PR；JDK 不存在 → JNI 必须可选（补丁 0002）。

## 5. test_package 测试数据自检

`test_package/data/` 三份 fixture 由同一条 ubiquitin 序列机械生成，避免手工转录错误：

| 文件 | 内容 | 长度 | 作用 |
|------|------|------|------|
| `bank.fa` | `sp\|TESTUBIQ\|UBIQ_HUMAN` + ubiquitin | 76 aa | 参考库 |
| `query.fa` | `PKKKK` + ubiquitin | 81 aa | 正例（应 >= 90% identity） |
| `query_unrelated.fa` | ubiquitin 的反向序列 | 76 aa | 反例（同组成、应 < 90% identity） |

`test.sh` 与 `test_plast_api.cpp` 都以 `-e 1e-5` 运行同一对参数，断言：
正例至少 1 条比对且 identity >= 90.00；反例 identity < 90.00；结果文件中出现 `UBIQ_HUMAN`。

## 6. 本机**未**验证的内容（明确边界）

| 未验证项 | 原因 | 需要谁来验证 |
|----------|------|--------------|
| `cmake` configure / build | 本机无 cmake，且无 OHOS/aarch64 工具链；Windows 上 MinGW 走的是 `__WINDOWS__` 分支，与目标路径无关 | 真机 / shadow CI |
| aarch64 上 SIMDe→NEON 编译 | 同上 | 真机 / shadow CI |
| `PlastLibraryTest` 断言（静态计数 475 处 `CPPUNIT_ASSERT*`；上游有效注册 108 个用例，其中 18 个已注册 suite 覆盖 96 个） | 同上 | 真机 / shadow CI（结果见 `reports/device-verification.md` §3） |
| 包内是否含 `include/misc/api/version.hpp`（风险 R3） | 需要真实 `cmake --install` | 真机 / shadow CI（test_package 已把它做成硬断言） |
| 链接 `-ldl` / `-lpthread` 是否可用（风险 R1） | 需要 OHOS 工具链 | 真机 / shadow CI |

以上各项已写入 `notes.md` §6「下一步（真机 / shadow CI）」的观察清单。
