# plast 2.3.2 — 真机验证报告

> 本轮在 HarmonyOS 真机上完成 `conan create` 全流程验证：编译、打包、上游单元测试、
> test_package 消费者测试全部通过。下文为真机原始输出的**节选**（原始构建日志约 240 KB，
> 未入库），关键行逐一照抄，未做改写。

- 日期：2026-10-15
- 真机：HarmonyOS aarch64（`HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP ... aarch64 Toybox`）
- 工具链：clang 15.0.4、cmake 4.1.2、conan 2.31.1、git 2.45.2
- profile：`ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd=17）
- 命令：`conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
- **结果：EXITCODE=0**

**复验（同一天，针对最终提交版本）**：由于后续只改动了 `test_package/`、文档与软件级元数据
（配方 revision 未变），`conan create` 会命中缓存跳过编译。为消除疑虑，又执行了一次
**强制全量重建**：

```text
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=plast/*
```

结果与首次一致：`Built target test` / `Package 'af03c1b0320f7f5fc22545d6f17403605281f4ce' created` /
`OK (96 tests)` / 8 行 `[skip]` / `ALL PLAST CONSUMER TESTS PASSED` / `EXITCODE=0`
（构建日志 240 765 字节，未入库）。即下面记录的结论对应**已提交的那一版代码**。

**再复验（CI 修复与配方收敛后）**：在配方加入 `-j1`（E074）并把 `cppunit` 改为
`test_requires` 之后，用同一份工作树重新打包到真机再跑一次完整 `conan create`：

```text
plast/2.3.2: RUN: cmake --build ".../build/Release" -- -j20 -j1
plast/2.3.2: RUN: cmake --build ".../build/Release" --target test -- -j20 -j1
plast/2.3.2 (test package): RUN: cmake --build ".../test_package/build/..." -- -j20 -j1
OK (96 tests)          （8 行 [skip]）
Package '1f0755d18f189c9ed3949f4a6e57b57b8dbddc42' created
ALL PLAST CONSUMER TESTS PASSED
EXITCODE=0
can't fork 出现次数 = 0 ; jobserver 警告出现次数 = 0
```

两处结论：

1. `test_requires` 不影响 `generate()`——`self.dependencies["cppunit"]` 仍在，
   构造图里 `cppunit/1.15.1` 正常解析（`Requirements: simde/0.8.2, cppunit/1.15.1`），
   而消费者侧不再需要它；
2. **产物逐字节不变**：包 ID 因依赖图变化而改变，但三个产物的 SHA256 与上表完全一致
   （`PlastCmd` `2f34e79b…`、`makeplastdb` `4875fe73…`、`libPlastLibrary.a` `79178f3f…`，
   大小 1 235 456 / 174 592 / 3 980 652 B），包内 `include/misc/api/version.hpp`
   仍为 `PLAST_VERSION "2.3.2"`。即配方收敛没有改变任何交付物（本次日志 241 529 字节）。

## 1. 依赖（W0，真机复核）

```text
cppunit/1.15.1#a1e38dc3ed3d631d60a27e7f6eec70ce:f23d5a9b... - Download (ohpcd)
simde/0.8.2#cf73fc62791d361d34d8e83341280ef7:6b129b06...    - Download (ohpcd)
```

两个依赖都从 `ohpcd` 直接取到 OHOS profile 的 binary，未触发源码构建。

## 2. 编译

```text
[ 83%] Built target PlastLibrary-static
[ 98%] Built target makeplastdb
[ 98%] Built target PlastCmd
[100%] Built target PlastLibraryTest
Package 'af03c1b0320f7f5fc22545d6f17403605281f4ce' created
```

SIMDe 路线在 aarch64 上成立：三个 SSE kernel
（`SmallGapHitIteratorSSE8` / `UngapHitIteratorSSE8` / `UngapHitIteratorSSE16`）
通过 `simde/x86/sse3.h` + `SIMDE_ENABLE_NATIVE_ALIASES` 编译为 NEON，**未退化到标量实现**。
未打补丁的源码中 `_mm_*`/`__m128i` 只出现在这 3 个 `.cpp`（按**含任一符号的行数**计：
54 / 22 / 21 行），与之配对的 `.hpp` 中为 0 处——即移植面完全收敛在这 3 个翻译单元。

**构建规模实测**（用于解释 R9 的并行度问题，取自构建树与日志）：

| 项目 | 实测值 |
|------|--------|
| `src/` 下源文件 | 134 个 `.cpp` + 12 个 `.c` = **146** |
| 编译步骤（日志 `Building CXX/C object`） | **161**（149 CXX + 12 C） |
| 目标文件总数 | 160（`src/` 138 + `test/unit` 20 + `examples` **0**） |
| 链接步骤 | **5**（`libPlastLibrary.a` / `PlastLibraryTest` / `PlastCmd` / `makeplastdb` / `test_plast_api`） |
| `examples/` | 11 个目标存在但**默认不参与 `all`**（0 个 `.o`，需显式 `make examples`）——`ADD_SUBDIRECTORY(examples EXCLUDE_FROM_ALL)` 的排除优先于子目录内的 `add_custom_target(examples ALL ...)` |

## 3. 上游单元测试

```text
OK (96 tests)
```

**口径说明（重要，三个数必须分清）**：

| 数值 | 含义 | 来源 |
|------|------|------|
| **119** | 上游测试源码中 `new TestCaller` 语句总数 | `test/unit/src/` 下 19 个测试文件 |
| **108** | 其中**未被注释禁用**的 | 11 处被 `//` 或 `/* */` 注释禁用 → 108（本项目审查工具的上游实测口径） |
| **96** | 其中**实际参与编译**的用例数 | 另外 12 处位于 `TestMisc.cpp`，该文件**整体 `#if 0`**（编译为空 TU、不产生符号）→ 96，与 `OK (96 tests)` 完全吻合 |
| **88** | 本环境**实际执行断言并通过**的用例数 | 其余 8 个在用例体内检测到 fixture 缺失后直接 `return`（提前返回），CppUnit 仍把它们计为 OK |

`OK (96 tests)` 是 CppUnit 对**已启动**测试方法数的统计（`TestResultCollector::runTests()`）。
因此本报告与 PR 正文一律按 **88/88 实执行通过** 表述，既不写 96/96，也不把 108 当作通过率分母。

该汇总行本身只能由补丁 `0010-test-runner-report-failures.patch` 新增的
`CppUnit::TextOutputter` 打印——上游 `main.cpp` 只注册了 `BriefTestProgressListener`
且恒 `return 0`，既不输出失败详情也不返回非零状态。即这一行是打补丁后运行器的真实输出。

8 个早退用例及其缺失 fixture（上游从已失效的 `plast.gforge.inria.fr` 下载完整语料，
release 归档只带 `bug15696.fa` / `bug15696b.fa` / `query.fa` / `sapiens_1Mo.fa` / `tursiops.fa`
共 5 个文件）：

```text
[skip] testXmlFilterReader      : fixture 'filter1.xml' is not shipped in the release archive
[skip] testFileLineIterator2    : fixture 'uniprot_sprot.fa' is not shipped in the release archive
[skip] testFileLineIterator3    : fixture 'panda.fa' is not shipped in the release archive
[skip] testFastaBigFile         : fixture 'uniprot_sprot.fa' is not shipped in the release archive
[skip] testFilesList            : fixture 'panda.fa' is not shipped in the release archive
[skip] testFastaHugeFile        : fixture 'bugs/15202/hugecomment.fa' is not shipped in the release archive
[skip] testFastaQuickReader2    : fixture 'panda.fa' is not shipped in the release archive
[skip] test_maskdb              : fixture 'aphid_10000.fa' is not shipped in the release archive
```

其余 88 个用例（含 `TestPlastLike`、`TestPlast`、`TestDatabaseIndex`、
`TestSequenceDatabase`、`TestCompositeDatabase` 等重负载用例）全部通过。

## 4. test_package 消费者测试

```text
[ OK ] PlastCmd and makeplastdb are installed in the package bin/ directory
[ OK ] PlastCmd -h prints the PLAST option list
[ OK ] related query finds the subject at 100.00% identity
[ OK ] negative control stays at 0.00% identity
[ OK ] makeplastdb produced a non empty bank.fa.info
[info] PLAST_VERSION=2.3.2 PLAST_BUILD_OS=Linux
[ OK ] installed misc/api/version.hpp reports version 2.3.2
[ OK ] PlastCmd::execute() ran through the library API without exception
[info] library API: 1 alignment(s), best identity 100.00%
[ OK ] library API reported at least one alignment
[ OK ] library API alignment reaches at least 90% identity
PLAST API CONSUMER TEST PASSED
[ OK ] C++ library API consumer test passed
ALL PLAST CONSUMER TESTS PASSED
```

共 **10 项断言**（`test.sh` 6 项 + `test_plast_api.cpp` 4 项），逐条与
`test_package/` 源码中的 `ok "..."` / `check (...)` 一一对应。

## 5. 产物

```text
bin/PlastCmd              1235456  sha256 2f34e79bb362148e913e9f56295271a5700c8ba7b17013a5547bd392d465247f
bin/makeplastdb            174592  sha256 4875fe73f1c99d13a9508ed5d7051731629f8beb5eb2b52e71100d24939dcb24
lib/libPlastLibrary.a     3980652  sha256 79178f3f590883ce1a7bb68fbd5ec4241d0472fa7b1f1fc29c2bf0a11ca62085
include/{algo,alignment,database,designpattern,index,launcher,misc,os,pcre,seed,seg}
test/PlastLibraryTest + test/db
```

ELF 检查（L4 等价）：

```text
Format: elf64-littleaarch64    Arch: aarch64
NEEDED  libc++_shared.so
NEEDED  libc.so
```

只依赖 `libc++_shared.so` 与 `libc.so`，无 RUNPATH/RPATH 残留。

`PlastCmd -h`：

```text
plast 2.3.2
  - Build date: xxxx-xx-xx
  - OS: Linux
  - Compiler: /storage/Users/currentUser/usr/local/bin/clang (15.0.4)
  - Host CPU: 20 cores available
```

## 6. 端到端实跑（真机）

```text
$ PlastCmd -p plastp -i query.fa -d bank.fa -o out.txt -e 1e-5 -a 2
rc=0
qry  sub  100.00  76  0  0  6  81  1  76  1e-42  151.4
```

（tabulated 格式：query、subject、%identity、length、mismatch、gapopen、
qstart、qend、sstart、send、E-value、bit score。）

## 7. 真机阶段发现并修复的问题

按发现顺序，全部已固化为 `patches/`：

| 现象 | 根因 | 补丁 |
|------|------|------|
| `/tmp` 只读导致 `testSystemCommand` 崩溃 | `SystemCommand` 硬编码 `/tmp/<ptr>` | 0007 |
| 多个单测写 `/tmp` 失败 | 单测硬编码 `/tmp` | 0008 |
| `testFastaOutputFrame` **死循环**（12 分钟 CPU 不退出） | `CommonOsImpl.hpp:80` 用 `char c != EOF`；aarch64 `char` 无符号，EOF(-1)→255，末行无换行时永不退出 | 0009 |
| 测试框架吞掉失败详情、恒返回 0 | `main.cpp` 用 `result` 却不输出、`return 0` | 0010 |
| 8 个单测依赖归档中不存在的 fixture | 上游从已失效站点下载完整语料 | 0011（显式 skip 并打印原因） |
| FRAME_4/5/6 翻译结果全错（`EKKKK…` / `KKKK…`）且 `testCompositeDatabase2` **SIGSEGV** | `char getDirection()` 返回 -1；aarch64 上 `char` 无符号 → 255，被当作数组下标参与 `offset + direction*(i+k)` 计算，反向链读越界 | 0012 |
| 包内 `include/misc/api/version.hpp` 报告 `unstable-master` | `install(... DESTINATION include/os/api/)` 路径写错，源码树里的同名占位头把生成头覆盖了 | 0013 |

其中 **0009 与 0012 是同一类 aarch64 `char` 无符号导致的真实缺陷**：

- 0009 让 PLAST 在“最后一行没有换行符且该行超过 `commentMaxSize`”的 FASTA 上死循环；
- 0012 让反向阅读框（`plastx` / `tplastx` / `plastn` 的负链）产生完全错误的翻译结果，
  并在较大库上直接段错误。

两者都不是测试问题，而是**产品代码在 aarch64 上的功能性缺陷**，
`clang` 在编译期其实已经用 `-Wtautological-constant-out-of-range-compare` 警告过 0009
（构建日志中可见 `CommonOsImpl.hpp:80:77: warning: result of comparison of constant -1 with
expression of type 'char' is always true`）。

## 8. 与「下一步」清单的对照

上一轮 `notes.md` 列出的观察点，真机结果：

| # | 观察点 | 结果 |
|---|--------|------|
| 1 | 是否打印 `JNI not found` | ✅ 出现，JNI 按设计不参与构建（功能裁剪已记录） |
| 2 | `-msse3` 是否已不传给 aarch64 | ✅ 未出现该参数；SIMDe 路径生效 |
| 3 | `PlastLibraryTest` 断言 | ✅ `88/88` 实执行用例通过；8 例因 fixture 缺失早退（CppUnit 汇总行为 `OK (96 tests)`，口径见 §3） |
| 4 | `-ldl` / `-lpthread` 是否可链接（原 R1） | ✅ 可链接，无告警；`libc++_shared.so` + `libc.so` 之外无额外 NEEDED |
| 5 | 包内是否有 `include/misc/api/version.hpp`（原 R3） | ❌ 曾缺失/被占位头覆盖 → 已由补丁 0013 修复并断言通过 |
| 6 | CI 上能否并行构建 | ❌ 首次 CI（#93278）在 `-j20` 下 fork 耗尽 → 已按 E074 强制 `-j1` 并复验通过，见 §9 |

## 9. shadow CI 首次构建失败与修复（#93278）

首次 CI 校验失败，类别被判为「编译失败」，但日志里**没有任何编译诊断**：

```text
make: jobserver mkfifo: /storage/Users/currentUser/.cache/tmp/GMfifo35716: Operation not permitted
make[2]: /bin/sh: Resource temporarily unavailable
make[2]: *** [src/CMakeFiles/PlastLibrary-static.dir/build.make:120:
             .../algo/core/impl/BasicAlgoIndexator.cpp.o] Error 127
make[2]: *** Waiting for unfinished jobs....
/bin/sh: can't fork - try again
make[2]: *** [.../algo/core/impl/AlgorithmPlastn.cpp.o] Error 1
/bin/sh: can't fork - try again
make[2]: *** [.../algo/core/impl/AlgoIndexatorNucleotide.cpp.o] Error 1
make[1]: *** [CMakeFiles/Makefile2:271: src/CMakeFiles/PlastLibrary-static.dir/all] Error 2
```

### 根因

`Error 127` / `Error 1` 伴随 `can't fork`，即 **`fork()` 资源耗尽**，不是源码问题（同一份代码在本机真机
`-j20` 下能编过）。链路是：

1. 知识库 **E074** 与原则 **P020** 已记录：HarmonyOS/HMDFS 不允许创建 FIFO，
   本机复核 `mkfifo probe_fifo` → `Operation not permitted`；
2. GNU make 的 jobserver 依赖 FIFO 传递并行令牌，FIFO 建不起来时退化为 pipe
   （`--jobserver-auth=3,4`）；CI worker 上子 make 拿不到有效 jobserver，
   于是递归 make 按「无限并行」运行；
3. PLAST 有 146 个源文件（161 个编译步骤），CMake 生成的是递归 Makefile，`-j20` 在失去节流后
   瞬间把 worker 的进程/线程配额打满 → `fork` 失败。

### 修复与验证

按 E074 的推荐方案强制单线程（仓库既有 10 处 `cmake.build(build_tool_args=["-j1"])` 先例），
`build()` / `cmake.build(target="test")` / test_package 三处都加上：

```python
cmake.build(build_tool_args=["-j1"])
```

Conan 会把该参数追加在自身 `-j<jobs>` 之后，实际命令为
`cmake --build <dir> -- -j20 -j1`。实机先验证 GNU make 的取值规则：

```text
$ make -j20 -j1    → MAKEFLAGS=[ -j1]            （最后一个 -j 生效，且不建 jobserver）
$ make -j1 -j20    → jobserver mkfifo: ... Operation not permitted
                     MAKEFLAGS=[ -j20 --jobserver-auth=3,4]
```

修复后复跑 `conan create`：

```text
plast/2.3.2: RUN: cmake --build ".../build/Release" -- -j20 -j1
OK (96 tests)          （8 行 [skip]）
Package 'af03c1b0320f7f5fc22545d6f17403605281f4ce' created
ALL PLAST CONSUMER TESTS PASSED
EXITCODE=0
ELAPSED=363s
can't fork 出现次数 = 0 ; jobserver 警告出现次数 = 0
```

### 顺带修掉的一处 CI 噪音

首次 CI 的 “Pre-download: extracting source URLs from conandata.yml” 报了 `found 3 source URL(s)`，
其中一条是从 `conandata.yml` **注释文本**里正则抓出来的 `https://plast.inria.fr/developer-guide/)`。
已把该注释改写成不含 URL scheme 的表述，避免污染 CI 日志（不影响实际下载：真源仍是
`github.com/PLAST-software/plast-library` 的 tag 归档，CI 会自动加 gh-proxy 镜像 fallback）。

## 9.1 shadow CI 第二次构建（#93345）：`-j1` 生效，末步 `posix_spawn` EAGAIN

推入 `-j1` 修复后重跑，构件 #93345（head `e72cc95c`，worker `OpenHarmonyPCDeveloper-CI-026`，
耗时 6m32s）。**编译阶段已完全通过**：日志显示 `[ 83%] Linking CXX static library
../lib/Release/libPlastLibrary.a` 成功、测试目标各翻译单元逐个编过直到
`[ 96%] Linking CXX executable ../../bin/Release/PlastLibraryTest`，此前的
`jobserver mkfifo` / `can't fork` 全部消失——即 **E074 的 `-j1` 修复有效**。

失败点是最后一条链接命令：

```text
[ 96%] Linking CXX executable ../../bin/Release/PlastLibraryTest
clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
make[2]: *** [test/unit/CMakeFiles/PlastLibraryTest.dir/build.make:407:
             bin/Release/PlastLibraryTest] Error 1
ERROR: plast/2.3.2: Error in build() method, line 125
	cmake.build(build_tool_args=["-j1"])
	ConanException: Error 2 while executing
```

`EAGAIN` 来自 `clang` 派生 `ld.lld` 时的进程创建，属 **worker 侧进程配额瞬时耗尽**，
不是本库源码或配方缺陷。三条证据：

1. **同机存在并发构建**：该 CI worker 即真机 `112.17.30.188`（`nproc=20`、`HOME` 与
   CI 日志中的 `/storage/Users/currentUser` 一致）。在其 conan 缓存
   `~/.conan2/p/b/` 中，#93345 运行区间（18:54–19:01）内**同时出现另一个包的构建目录
   `xeus-1420e30f3aeca`（19:01）与 `xeus-142621f7c7518`（19:08）**，说明同一台
   worker 并行执行多个包的 CI 构建，共享同一份进程/线程配额。
2. **同一链接命令单跑稳定通过**：从 CMake 生成的
   `test/unit/CMakeFiles/PlastLibraryTest.dir/link.txt`（1 448 B，即失败时执行的同一条命令）
   取出完整命令，在同一台机器上**连续执行 10 次，全部成功**，产物 2 025 984 B，单次 <1 s；
   另做 40 次进程创建压力循环，失败 0 次。
3. **本包并发已降到 1**：`-j1` 之后编译期 161 次编译步骤的进程创建均成功，只有最后一次失败，
   符合"瞬时资源竞争"而非"确定性缺陷"的特征。

处置：保留 `-j1`，重跑 shadow CI 取最终结论（`notes.md` §4 R10）。

## 9.2 shadow CI 第三、四次构建：更早的阶段就 `can't fork`

**#93397**（head `299c047d`，worker **CI-013**）失败于 **CMake 的编译器探测**：

```text
-- Detecting C compiler ABI info - failed
-- Check for working C compiler: /data/service/hnp/bin/clang - broken
CMake Error at .../CMakeTestCCompiler.cmake:67 (message):
  The C compiler "/data/service/hnp/bin/clang" is not able to compile a simple test program.
    Run Build Command(s): .../make -f Makefile cmTC_0ff24/fast
    make[1]: /bin/sh: Resource temporarily unavailable
    make[1]: *** [CMakeFiles/cmTC_0ff24.dir/build.make:81:
                  CMakeFiles/cmTC_0ff24.dir/testCCompiler.c.o] Error 127
    make: *** [Makefile:134: cmTC_0ff24/fast] Error 2
```

**#93409**（head `fa4b0e2173`，worker **CI-010**，由 push 自动触发）失败得更早——
在 **Conan 生成的构建环境脚本**里：

```text
plast/2.3.2: Apply patch (portability): 0001 … 0013        ← 13 个补丁全部按序应用成功
plast/2.3.2: Running CMake.configure()
/system/bin/sh: .../generators/conanbuildenv-release-armv8.sh[13]: can't fork - try again
ERROR: plast/2.3.2: Error in build() method, line 116
	cmake.configure()
```

两次的关键点相同：

- #93397 编译的是 CMake 自己生成的 **3 行 `testCCompiler.c`**；#93409 连 `cmake` 都还没启动，
  失败发生在 `source conanbuildenv-*.sh` 这一步——**与本库源码、配方、补丁都无关**；
- 此刻**没有任何并行**（单条 `make` → `sh` → `clang`，或单个 `sh`），
  因此 `-j1`、make jobserver、HMDFS 都解释不了；
- 发生在两个**此前未出问题的 worker** 上（CI-013 / CI-010）；
- #93397 同一次构建里 L0/KC/JC/G0 全绿：`[ok] L0: All quality gate checks passed (Errors: 0)`、
  `G0_RESULT=pass ; KC_RESULT=pass ; JC_RESULT=pass`；
- #93409 的日志显示 13 个补丁**全部按序应用成功**（含更正后的
  "0011 skip the eight unit tests …"），说明配方与补丁在 CI 侧同样是完好的。

**五次构建合起来构成完整证据链**——同一种资源问题在四个不同阶段、**四个不同 worker** 上出现：

| 构建 | worker | 失败阶段 | 报错 |
|------|--------|----------|------|
| #93278 | CI-026 | 编译（`-j20`） | `jobserver mkfifo: Operation not permitted` → `can't fork - try again` → `Error 127` |
| #93345 | CI-026 | 链接 `PlastLibraryTest` | `clang-15: … posix_spawn failed: Resource temporarily unavailable` |
| #93397 | CI-013 | CMake 编译器探测 | `make[1]: /bin/sh: Resource temporarily unavailable`（编 3 行 `testCCompiler.c`） |
| #93409 | CI-010 | source conan 环境脚本 | `conanbuildenv-release-armv8.sh[13]: can't fork - try again` |
| #93525 | CI-035 | CMake 编译器探测（同 #93397） | `make[1]: /bin/sh: Resource temporarily unavailable` → `cmTC_86726/…/testCCompiler.c.o Error 127`，全程 **29 s** |

#93525 是 head `22224671` 的结果，失败签名与 #93397 **完全一致**（同一个
`CMakeTestCCompiler.cmake:67`、同样编 3 行探针、同样 `Error 127`），说明这不是偶发抖动，
而是当前 CI 舰队在负载下的稳定行为；该次构建同样是 **L0/KC/JC/G0 全绿**
（`[ok] L0: All quality gate checks passed`、`G0_RESULT=pass`、`KC_RESULT=pass`、
`JC_RESULT=pass`），且 13 个补丁全部按序应用成功，随后才在编译器探测上 `can't fork`。

CI 构建墙同期数据也一致：最近 50 条记录里 **24 条失败**、**17 条同时在跑**，
高失败率并非本库独有。

## 9.3 最终结果：构建 #93740 校验通过 ✅

在同一个 head 上等到负载回落后重跑，CI 给出：

```text
## CI 校验通过
| PR #16017 | #93740 | OpenHarmonyPCDeveloper-CI-001 |
### 验证详情
- Conan test_package: 通过
- L0 门禁 (结构完整性): 通过
- L1 门禁 (测试执行验证): 通过
| conan-build-test | ✅ |
```

七个步骤全绿（`worker_preparation` / `worker-prep` / `git-clone` / `checkout-pr` /
`conan-setup` / `conan-build-test` / `cleanup`）。这印证了 §9.1/§9.2 的判断：
**前 5 次失败中只有 #93278 是本包范围内的真问题（已由 `-j1` 修复），
其余 4 次是 worker 侧进程创建资源竞争，负载回落后同一份代码即通过。**

## 10. 仍未验证

- ~~shadow CI 的 L0-L5 门禁结论~~ → **已取得**：构建 **#93740 校验通过**
  （L0 结构完整性 + L1 测试执行验证 + `Conan test_package` 全通过）。
  此前 5 次失败中只有 #93278 是本包范围内的真问题（已由 `-j1` 修复），
  其余 4 次为 worker 侧进程创建资源耗尽（见 §9.1/§9.2），负载回落后同一 head 即通过；
- `plastx` / `tplastx` / `plastn` 三个核酸算法的端到端实跑（本轮只跑了 `plastp`；
  但覆盖其核心的反向阅读框已由 `testReadingFrameIterator` 与 `testCompositeDatabase2` 验证）；
- 8 个 skip 用例：需要上游完整的 `test/db` 语料（该来源已失效）；
- `TestMisc` 的 12 个用例：上游 `main.cpp` 从未注册该 suite，本环境同样不执行
  （保持上游行为，未改动用例集）；
- `conan upload` 到 release 流水线（本 PR 只做到 shadow CI 通过，归档状态仍为 `built`）。
