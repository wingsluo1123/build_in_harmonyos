# thrax 1.3.10 适配笔记

## 版本说明

- 上游版本：OpenGrm Thrax **1.3.10**（OpenFst 之上的 WFST 语法编译器，Apache-2.0）
- 本版本号 **1.3.10**：首次适配，无适配修复后缀（R37）
- 依赖：**openfst/1.8.4.1**（必须，且必须是含 GRM 扩展 `far/pdt/mpdt` 的适配版）

## 编译环境

- 构建系统: autotools（源码自带 `configure` 655KB + `ltmain.sh`，无需 autoreconf）
- 编译器: clang / clang++（`-std=c++17`、`-fno-exceptions` 由 configure.ac 强制）
- 目标: HarmonyOS PC / aarch64、libc++
- 状态: built

## 编译步骤

1. **W0 依赖检查**：`conan download openfst/1.8.4.1 -r=ohpcd --only-recipe` → 已发布；
   核验 4 个头文件（`fst/fst.h`、`fst/extensions/far/far.h`、`pdt/pdt.h`、`mpdt/mpdt.h`）
   与 6 个静态库齐备 —— thrax 的 `configure` 对这 4 个头文件做 `AC_MSG_ERROR` 硬校验
2. `ohc-run.py init-build thrax 1.3.10 --url=<官方 tarball>` + `lang-preflight`
   （task=cpp / detected=cpp，C++ 占比 100%）
3. `./configure --prefix=$DEFAULT_PREFIX --enable-bin`
4. `make -j1`（与 CI 同口径）
5. `make check`（上游无测试目标，空操作，退出码 0）
6. `make install DESTDIR=$TEST_PREFIX`（staging 隔离验证）
7. `conan create`（W3 本地 CI，含 test_package 消费者测试）

## 上游测试清点（R51 三步法，第一步）

清点命令与证据（全树扫描，源码目录 thrax-1.3.10）：

| 清点项 | 结果 |
|--------|------|
| `find . -name '*test*'` 文件名 | `src/bin/regression_test.cc`、`src/bin/rewrite-tester{,-main}.cc`、`src/grammars/bytestringcopy.grm`、`src/include/thrax/rewrite-tester.h` |
| 目录名含 test | 无 |
| automake `TESTS` / `check_PROGRAMS` / `*_TESTS` 声明 | 无 |
| bazel `cc_test` 目标 | 无（`BUILD.bazel` 中 `regression_test` 仅为 `testonly` 的 `cc_library`，不被任何 `cc_test` 引用） |
| `make check` 实际行为 | 空操作（无 TESTS 声明），退出码 0 |

唯一的测试类文件 `src/bin/regression_test.cc`（329 行 gtest 驱动）**不可运行**，具体技术原因：

1. 它只出现在 `src/bin/Makefile.am` 的 `EXTRA_DIST` 中 —— **只随包分发、不参与构建**，
   任何构建系统（autotools/bazel）都不会把它变成可执行文件；
2. 依赖 **abseil**（本制品仓不可用：`abseil/20240116.2`、`20230802.1`、`20220623.1`
   逐个 `conan download` 探测均返回空）；
3. 需要 `--test_file=<corpus>` 数据文件，该语料**未随发布包分发**。

**结论：上游可运行测试数 = 0**，故按 R51 追加鸿蒙消费者测试（第二步/第三步见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 不识别 HarmonyOS 平台 | `config.guess` 无 HarmonyOS 分支（`config.sub` 原生支持 ohos） | 补丁 0001：把 `HarmonyOS` 并入 `Linux\|GNU\|GNU/*` 分支并归一为 Linux 三元组 → `aarch64-unknown-linux-gnu` |
| 2 | 链接失败：`libtool: error: cannot find the library '//lib/libfst.la' or unhandled argument '//lib/libfst.la'` | openfst 包内 `.la` 记录构建机前缀 `//lib`，其 `dependency_libs` 为死链（知识库 E236 同型） | 在构建目录内生成只含 `libfst*.a` 的私有目录 `fst-static/`，并把它的 `-L` 放在 LDFLAGS 最前 → libtool 解析到 `.a`，完全绕开 `.la`；不改动 Conan 缓存 |
| 3 | 运行期 `Unknown FST type "vector"` + `Error loading shared library vector-fst.so`；`example.grm`（含 import）编译 `Signal 11 (core dumped)` | `REGISTER_FST` 生成的注册对象只经**静态初始化器**可达，且在 `libfst.a:fst-types.o` 内是**文件局部符号**；归档按需抽取时该成员整体不被拉入 → FST 类型注册表为空 | 补丁 0002/0003：命令行工具的 `LDADD` 把 `-lfst` 包进 `--whole-archive` |
| 4 | 补丁写成 `-Wl,--whole-archive -lfst -Wl,--no-whole-archive`（两个独立 `-Wl`）仍失败 | **libtool 会把两个独立 `-Wl` 参数重排，远离 `-lfst`** | 定稿为**单个** `-Wl` 参数：`-Wl,--whole-archive,-lfst,--no-whole-archive`（微实验 T1 实证：单参数写法产物 1 710 528 B、注册器 1 个；拆开写法复现空注册表） |
| 5 | 消费者测试第 3 步 `example.grm:13: Unable to open grm source file: byte.grm` | thrax 的 `import` 相对**当前工作目录**解析，不是语法文件所在目录；且 `import 'x.grm'` 取同目录同名 `x.far` | 测试脚本 `cd` 进语法副本目录，用相对文件名并按 byte → numbers → example 依赖顺序编译 |
| 6 | 直接运行构建树二进制报 `libthrax.so.139` 加载失败 | 二进制 RUNPATH 指向构建前缀，与链接修复无关 | 运行期设 `LD_LIBRARY_PATH`（包内 `lib/`） |

### 根因定位证据链（问题 3）

用最小复现探针（同一 toolchain、三种链接口径）判定：

| 变体 | 链接口径 | FST 注册实例数 | 读 `.far` |
|------|---------|---------------|-----------|
| A | `-lfstscript -lfstfar -lfst`（上游写法） | 0 | `Unknown FST type vector`，exit 1 |
| B | `-lfst` 包 whole-archive | 1 | `READ_OK start=0` |
| C | 三个库全部 whole-archive | 1 | 可读（产物 10.9 MB） |

真 thrax 复现与核验：修复前 `byte.grm` 可编译、`example.grm`（import）`Signal 11`；
修复后三个可执行文件的 `VectorFst_StdArc_registerer` 计数均为 1、注册器总数 24。
库侧核验：`libthrax.so.139.0.0` 的 106 个注册器**全部**是 thrax 自身的 function 注册器
（`VectorFst_StdArc_registerer` 计数 0），即 FST 注册对象由**可执行文件**提供 —— 修复
落点正确地在 `src/bin`（命令行工具）而非 `src/lib`。

## 源码修改（补丁说明）

三个补丁全部为 `portability` 类型，**不含任何平台宏**（无 `#ifdef __OHOS__`）：

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-config.guess.patch` | `config.guess` | HarmonyOS 并入 Linux 分支并归一为 Linux 三元组 |
| `0002-src-bin-Makefile.am.patch` | `src/bin/Makefile.am` | 两处 `LDADD`：`-lfst` → `-Wl,--whole-archive,-lfst,--no-whole-archive`（含根因注释） |
| `0003-src-bin-Makefile.in.patch` | `src/bin/Makefile.in` | 与 0002 同内容 —— 构建实际使用 `configure` 从 `.in` 生成的 Makefile，`.in` 是生效的那一份 |

> 未改 `src/lib/Makefile.am`：`libthrax_la_LIBADD` 上游为空，`libthrax.so` 本就不承担
> 链接 openfst 的职责（其未定义 fst 符号由消费者可执行文件提供，见上文库侧核验）。

## 依赖版本

- 构建期/运行期依赖：`openfst/1.8.4.1`（静态库，含 GRM 扩展）
- 运行时系统库：`libc++_shared.so`、`libc.so`（`readelf -d` NEEDED 仅此两项）
- 未启用 readline：`--enable-readline` 上游默认 no，保持默认（避免引入 ncurses 共享库风险，R4）

## 验证结果

### 1) 构建与安装

```bash
./configure --prefix=$DEFAULT_PREFIX --enable-bin   # CONFIGURE_EXIT=0，4 个头文件检查 yes
make -j1                                            # MAKE_EXIT=0（lib 59/59 + 3 个可执行文件）
make check                                          # 空操作，退出码 0
make install DESTDIR=$TEST_PREFIX                   # 安装成功
```

### 2) 上游测试实跑（R51 第二步）

上游无可运行测试（清点见上），`make check` 空操作退出码 0 = N/N′ = 0/0，
**不构成可运行测试证据**，故按下节追加鸿蒙消费者测试。

### 3) 鸿蒙消费者测试（R51 第三步，`test_package/check_thrax.sh`，实测通过）

```
PASS thrax consumer test: compile + import + rewrite + random generation
```

链路与断言（全部基于包内自带素材 `share/thrax/grammars/`）：

| 步骤 | 命令 | 断言 |
|------|------|------|
| 1 | `thraxcompiler --input_grammar=byte.grm --output_far=byte.far` | `byte.far` 非空 |
| 2 | `thraxcompiler --input_grammar=numbers.grm --output_far=numbers.far` | `numbers.far` 非空（依赖 byte.far） |
| 3 | `thraxcompiler --input_grammar=example.grm --output_far=example.far` | `example.far` 非空（import byte+numbers） |
| 4 | `thraxrewrite-tester --far=example.far --rules=TOKENIZER` | 三行输入改写输出逐字匹配：`Well , I ca n't eat muffins in an agitated manner .` / `Lieutenant eighteen forty ,` / `Mr. Ernest Worthing , B. four , The Albany .`，且不含 `Unknown FST type` |
| 5 | `thraxrandom-generator --far=example.far --rule=TOKENIZER --noutput=2` | 输出非空、无 `Unable to`/`FATAL`/`Unknown FST type` |

第 3 步即 FST 类型注册表的回归护栏：缺注册对象时该步报 `Unknown FST type` 或段错误。

### 4) 包布局

| 路径 | 内容 |
|------|------|
| `bin/` | `thraxcompiler`、`thraxrewrite-tester`、`thraxrandom-generator`（3 个 ELF 工具）+ `thraxmakedep`（上游 shell 脚本，由 `EXTRA_DIST` 安装） |
| `lib/` | `libthrax.so.139.0.0` + `libthrax.so.139`/`libthrax.so` 软链 + `libthrax.la`（`AC_DISABLE_STATIC`，本包只发布共享库） |
| `include/thrax/` | 头文件树（含 `algo/` 等子目录） |
| `share/thrax/grammars/` | 上游语法素材：`byte.grm`、`numbers.grm`、`example.grm`、`tokenizer.grm`、`replace.grm`、`assert.grm`、`pdt.grm`、`mpdt.grm`、`paradigms_and_features.grm`、`bytestringcopy.grm`、`ernest.txt`、`README` |
| `share/thrax/utils/` | `thrax-mode.el`、`thraxgrm.vim` |

## 注意事项

- 下游引用请用精确版本 `self.requires("openfst/1.8.4.1")`：**必须**是含 GRM 扩展的适配版，
  否则 thrax `configure` 的 4 个头文件硬校验会直接失败
- 消费者若要自己链接 `libthrax.so`，需同时链接 openfst 静态库并同样使用
  `--whole-archive` 口径（`libthrax.so` 不内嵌 FST 注册对象，见上文库侧核验）
- 命令行工具运行需包内 `lib/` 在 `LD_LIBRARY_PATH` 中（配方已通过 `runenv_info` 注入 PATH/LD_LIBRARY_PATH）
- `example.grm` 的 `assert.grm` 同族素材故意断言失败，消费者测试未使用

---

**编译结束**: 2026-10-11 13:43
**最终状态**: built

## CI 修复记录（2026-10-13）

CI（#85286/#85326）`conan-build-test` 失败：`config.status: error: could not setup
config files machinery`，`./confXXXX/subs1.awk: Permission denied`。本地 W3 通过但
CI 失败——设备 console 创建者==写入者，CI SSH 会话 uid 与 HMDFS FUSE 属主映射
（owner→20001006）错位，`mktemp -d` 恒 0700 目录对 CI 进程不可写（E011 家族，
DRAFT-6507 cln 同型实证）。

修复（patches/0004）：把 configure 主分支 `(umask 077 && mktemp -d "./confXXXXXX")`
替换为 `tmp=./conf$$-$RANDOM; (umask 000 && mkdir "$tmp")`（DRAFT-6507 CI 实证
形式，umask 放宽单独无效——GNU mktemp -d 不吃 umask，本机 umask 000 实测仍
2771/other 无 w；fallback 的 `umask 077 && mkdir` 同步放宽为 000）。build() 另加
进程级 `os.umask(0o000)` 兜底其余裸 mkdir（对 mktemp 无效，仅防御）。补丁已在
tarball 原版 configure 上 `git apply` 干净应用实测。
