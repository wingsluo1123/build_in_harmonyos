# sfront 0.99：嵌套 Makefile 入口、预生成解析器的确定性，与 `-cpp` 在 OHOS 上不可用

- **草稿 ID**: `DRAFT-sfront-0.99-nested-make-pregenerated-parser-and-cpp-gcc`
- **来源**: `sfront/0.99` HarmonyOS PC 适配实战
- **分类**: `raw-makefile / nested-make / codegen / pregenerated-parser / cli-tool / consumer-test`
- **状态**: `VERIFIED DRAFT`，路径 B 难度候选，待知识库审核
- **Issue/PR**: 本轮按任务要求不记录

## 适用场景

sfront 是 MPEG-4 Structured Audio（MP4-SA）规范 John Lazzaro 在 2011 年发布的参考
实现：把 SAOL 乐谱或 MP4-SA 位流翻译成一个能合成音频的独立 C 程序。它是纯 C89，
没有 configure / autotools / CMake，只有两个手写 Makefile；而且**真正的构建入口
不是最外层的那个**。

本条目适用于这样的组合：

- 上游只有 raw Makefile，且顶层 Makefile 需要被另一个 Makefile 回调；
- tarball 里同时带着语法/词法生成产物（`parser.tab.c`）和它的文法（`parser.y`）；
- 交叉工具链与上游默认的 `CC=gcc`、`-m32`、GCC 专有开关都不一致；
- 可选的预处理模式（`-cpp`）在上游代码里被硬编码成某个外部程序名 + 固定安装前缀；
- 交付物是命令行 ELF，需要在 AArch64 worker 与 x86 本地盘上都能真正执行。

## 问题与错误签名

### 1. 构建入口不是 `src/Makefile`

`src/Makefile` 里有 `parser.tab.c` 的生成规则和 `SFRONT` 链接目标，看起来就是主
Makefile，但 `src/lib/Makefile` 的 `all` 目标才是完整流程：它先编译 `libmaker`
代码生成器，用 `src/lib/{csrc,asys,csys,nsys,psys}/*.c` 模板重建
`src/{csrclib,asyslib,csyslib,psyslib,nsyslib}.[ch]`，然后 `cd .. ; make` 回落到
`src/Makefile` 链接出 `bin/sfront`。Debian 的 `debian/rules` 也是这条路径。

后果：

- 直接 `make -C src` 会跳过代码生成，用 tarball 里可能过期的 `*lib.c`；
- `CC` / `CFLAGS` 的命令行覆盖靠 `MAKEFLAGS` 传到子 make，漏掉就静默用回 `gcc`；
- 子 make 在 HMDFS 上拿不到 jobserver（`make[1]: warning: jobserver unavailable:
  using -j1`，E074/E525），并行度会被静默降级。

### 2. 上游默认编译开关三条都不能直接用

```make
CC = gcc
OPT = -O2
DBUG = -g
ECHECK = -ansi -Wall
MODEL = -m32
SLOWSCHED = -fno-schedule-insns
CFLAGS = $(MODEL) $(OPT) $(DBUG) $(ECHECK)
```

- `-m32`：AArch64 上没有 32 位 ABI，必须整体覆盖 `CFLAGS`；
- `-fno-schedule-insns`：GCC 专有，clang 15 只打印
  `warning: optimization flag '-fno-schedule-insns' is not supported`，不清理就会
  污染每一条编译行；
- `-ansi`：**实测不需要**。用 clang 默认方言与 `-ansi` 各构建一次，产出的
  `sfront` BuildID 完全一致（`6fb455b989f3264e`），两者都编译出 0 条
  implicit-function-declaration，也没有 `-Wint-to-pointer-cast`。去掉 `-ansi`
  顺带规避 `__STRICT_ANSI__` 让 musl 隐藏 `strdup()`/`strcasecmp()` 声明、
  C89 隐式 int 把 64 位指针截断的老坑（tal 1.9 记录过）。

sfront 的翻译器自己不用 POSIX 扩展函数——`src/symbols.c:538` 写着
`/* strdup not ANSI -- rewritten with different name */`；`strdup` / `strcasecmp` /
`fileno` 只出现在 `*lib.c` 的**字符串字面量**里，那是给生成出来的程序用的模板文本。

### 3. 预生成解析器 + `-bison` recipe = 构建结果不确定

```make
parser.tab.c:	parsehelp.c parser.y tree.h
	-bison -d parser.y
```

官方 tarball 自带 bison 2.3 生成的 `parser.tab.c` / `parser.tab.h`，但
`conan get()` 用 `shutil.unpack_archive` 解压，**不保留 mtime**，所有文件都是当前
时间。于是 make 是否认为随包解析器过期，取决于解压顺序；recipe 前导的 `-` 又让 make
忽略失败，于是「机器上恰好有 bison」就会用 bison 3.8.2 重新生成一份，构建产物随机器
漂移。

处置：配方显式 `touch parser.tab.c parser.tab.h`，把随包产物变成唯一权威，构建不再
隐式依赖 bison。交叉核对过：`bison 3.8.2 -d parser.y` 无任何 error/warning，且用重新
生成的解析器与随包版本翻译同一示例，输出只有内嵌 sfront argv 与输出文件名之差。

如果某个项目随包的解析器**确实过期**（而不只是 mtime 不对），正确做法是
`tool_requires = "bison/3.8.2"` 并显式跑 `make parser.tab.c`，而不是靠 touch 掩盖。

### 4. `-cpp` 在 OHOS 上不可用

`src/sfmain.c:cppsystemcall()`：

```c
case GCC_COMPILER:
  prefix = "gcc -nostdinc -x c++ -E -o ";
  lastinclude = " -I " SAOLLIBDIR " ";
  sprintf(command, "%s%s%s%s%s", prefix, tptr->filename, cppincludes, lastinclude, tptr->val);
  ...
  if (system(command) || !(fd = fopen(tptr->filename, "r")))
      printf("\nError: Pre-processing for file %s was not successful.\n", ...);
```

而 `src/tree.h:667` 是 `#define SAOLLIBDIR "/usr/share/sfront"`。也就是说 `-cpp`
把预处理器**硬编码成外部程序 `gcc`**，并把 SAOL 头文件搜索路径**硬编码成
`/usr/share/sfront`**。OHOS 工具链没有 `gcc`，包的安装前缀也不是那个路径，于是
`-cpp` 报 `Pre-processing for file X was not successful` / `Misformed token or string`。

直接后果：26 个上游示例里**唯一** `#include <Slib/ssm.hs>` / `<Slib/std.hs>` 的
`examples/rtime/linbuzz` 在 OHOS 上无法翻译，其余 25 个与 `-cin` / `-gcc` 模式都不
受影响。这是上游对外部工具名与固定安装前缀的硬依赖，属于如实记录的平台限制，不是
适配裁剪。

顺带一个容易误判的点：`src/sfmain.c:148` 用 `system(NULL)` 探测 shell，缺失时打印
`No shell available for system() command.`。这在 OHOS 上不是问题（设备有 `/bin/sh`），
但会让人误以为 sfront 依赖 shell。

### 5. 位流往返不能在文本层比较

upstream 的 `mp4test` 目标是「编码成 MP4-SA 位流 → 解码回来 → 与直接路径的音频比对」。
如果在 C 文本层比对就会误判：

- `-bit` 解出来的程序把 SAOL 标识符重命名为自动名（`sawtwo_starthalfperiod` →
  `a7_*`、`BUS_trem_bus` → `BUS_a7`），连 `-symtab` 也保留不了原名；
- 浮点字面量从 ASCII 路径的 `1.95F` 变成位流路径的 `1.950000e+00F`（值相同、写法
  不同）。

有意义的等价性判据在**音频样本层**：min 的 `-orc` 与 `-bit` 两条路径渲染出的 WAV
逐字节相同（353,726 字节）；bach 的乐器求和顺序会变，从第 16593 字节起出现差异，
2976792 个采样里 2868555 个（96.4%）不同、最大偏差 13755/32767，所以 bach 只做
「解回等价程序」的结构断言。

### 6. `-static` 可用，`-static-pie` 不可用

OHOS SDK 没有 `rcrt1.o`：

```text
ld.lld-15: error: cannot open rcrt1.o: No such file or directory
```

`-static` 正常（2.7 MB 静态可执行文件）。静态链接的收益是交付物自包含：AArch64 worker
原生可跑，x86 本地盘经 `qemu-aarch64` 也能直接运行，不需要 `QEMU_LD_PREFIX` 或
guest rootfs。

### 7. 同一软件可以有两种上游发布物

- 官方站点 `https://john-lazzaro.github.io/sa/sfront0.99.tar.gz`：10,110,266 字节，
  顶层目录 `sfront/`，601 个条目，含**完整 26 个示例 / 20 个 SASL 乐谱**；
- Debian orig tarball：2,244,168 字节，是 `newdist` 流程产出的 lite 版，只含 16 个
  示例 / 12 个 SASL 乐谱。

`diff -r` 两者的 `src/` 与 `lib/` 结果为空——只有 HTML 手册里的作者主页链接
（`www.cs.berkeley.edu/~lazzaro` → `john-lazzaro.github.io`，出现在 39 个
`book/*/index.html` 与 3 个 `copyright/*.html`）以及示例集合本身不同。所以选官方源
既满足「源码 URL 必须是官方源」（R39），又能拿到完整示例语料；Debian 的 `dsc` 有 PGP
签名且记录了 orig tarball 的 sha256，正好可以当独立来源交叉验证。

## 根因拆解

1. **构建系统边界**：老项目的「主 Makefile」可能只是被回调的一层。判断依据是看哪个
   目标会 `cd ..` 再 `make`；本例是 `src/lib/Makefile`。
2. **工具链默认值边界**：`CC`、`MODEL`、`ECHECK`、`SLOWSCHED` 都是手写默认值，不会
   适配交叉编译。整体覆盖 `CFLAGS` 比逐个改 Makefile 更干净。
3. **代码生成确定性边界**：mtime 丢失 + 宽松 recipe（`-` 前缀）+ 机器上工具是否安装，
   三者叠加会让构建不可复现。要么显式声明工具依赖，要么显式固定随包产物。
4. **外部工具耦合边界**：把 `gcc` 和 `/usr/share/sfront` 写死在源码里的功能，换平台
   就一定失效；正确做法是记录限制，而不是删掉依赖它的示例来「让测试变绿」。
5. **等价性判据边界**：跨表示（文本 ↔ 位流）的等价要在语义层断言。音视频软件的等价判据
   是采样，不是字节。
6. **可执行交付边界**：静态链接让「同一份交付物」既能在真机原生跑、也能在 x86 上经
   qemu 跑，测试证据才可迁移。

## 推荐实现

### 1. 构建入口与变量覆盖

```python
compilers = self.conf.get("tools.build:compiler_executables",
                          default={}, check_type=dict)
cc = compilers.get("c", "clang")
cflags = "-O2 -Wall -Werror=implicit-function-declaration -static"
self.run("touch parser.tab.c parser.tab.h", cwd=os.path.join(self.source_folder, "src"))
self.run(shlex.join(["make", "-j1", f"CC={cc}", f"CFLAGS={cflags}",
                     "SLOWSCHED=", "LINKLIB=-lm"]),
         cwd=os.path.join(self.source_folder, "src", "lib"), env="conanbuild")
```

注意 `SLOWSCHED=` 传的是**空值**，不是省略——上游 Makefile 会把 `$(SLOWSCHED)` 追加
到每条 `CFLAGS` 后面。

### 2. 交付物布局

| 路径 | 内容 |
|------|------|
| `bin/sfront` | 静态 AArch64 可执行文件 + 软件级 `commands.json`（R38/L0k） |
| `share/sfront/lib/` | 上游 SAOL 标准库（`Slib/*.hs`、`reson/*.hs`） |
| `share/sfront/examples/` | 上游示例语料（本软件唯一的可执行规格） |
| `share/doc/<pkg>/html/` | HTML 手册与随包书籍 |
| `licenses/` | 包内所有许可证原文 |

不要收录发行版打包者新写的 manpage：它不属于上游 tarball。

### 3. 消费者测试怎么写才有意义

68 条断言分七组：交付物架构（`e_machine == EM_AARCH64`）、命令行面、**全部可翻译的
上游示例**、位流往返、错误诊断、鸿蒙特有端到端、载荷完整性。

鸿蒙特有用例的关键是**三段都必须真跑**：

1. 用交付的 aarch64 翻译器把上游乐谱翻成 C；
2. 用 OHOS 工具链把生成的 C 编成 AArch64 可执行文件；
3. 运行它，校验产出的 WAV 的 RIFF/fmt/data 结构、采样率、声道数、帧数与非静音。

再加一条 upstream `mp4test` 的音频级等价（位流路径 vs `-orc` 路径逐字节相同 WAV）。

按 `uname -m` 选择原生执行或 `qemu-aarch64`；**找不到模拟器必须判失败，不能静默跳过**。

## 验证证据

| 阶段 | 结果 | 证据 |
|------|------|------|
| W0 依赖检查 | 通过 | 无 Conan 依赖，不用 tool_requires |
| R47 语言预检 | 通过 | `detected_language=c`（`src/` 下 93 个 .c，主体 100%），与任务语言 cpp 兼容 |
| W3 本地 `conan create` | 通过 | rc=0，`-pr:h/-pr:b=ohos-aarch64-wsl` |
| test_package | 通过 | `SFRONT_TEST_SUMMARY pass=68 fail=0 total=68` |
| 上游示例覆盖 | 通过 | 26 个示例中 25 个翻译成功，唯一不可翻译项原因已记录 |
| 位流往返 | 通过 | min 892 字节、bach 6302 字节位流，首字节 0x80；`-symtab` 892→1003 仍可解码 |
| 鸿蒙端到端 | 通过 | min 176841 帧 44.1 kHz 单声道；torvalds 41464 帧 8 kHz 立体声（覆盖全部 41461 帧输入）；min 位流往返音频逐字节相同 |

## 为什么是 B 类候选

这不是「写一个 Conan 配方」的难度。它的困难点分布在四个互相牵连的边界上：

1. 构建系统边界——入口 Makefile 不是最外层那个，跳过代码生成会静默产出错误的翻译器；
2. 可复现性边界——mtime 丢失 + 宽松 recipe + 工具是否安装，让构建结果随机器漂移；
3. 平台耦合边界——`-cpp` 把 `gcc` 和 `/usr/share/sfront` 写死在源码里，26 个示例中有 1
   个因此不可翻译，必须如实记录而不是删测试；
4. 验证方法边界——跨文本/位流表示的等价性只能在采样层断言，文本层比对会得出「翻译器
   坏了」的错误结论。

最终状态有 68/68 断言、零重试的 `conan create`，以及每条结论对应的具体证据，是否正式
认定仍由知识库维护者审核。

## 非适用边界

- 上游随包解析器**确实过期**时不能用 touch 掩盖，应 `tool_requires` 一个 bison 并显式重生成；
- 工具链确实提供 `rcrt1.o` 的场景可以直接用 `-static-pie`，不必退到 `-static`；
- 不硬编码外部工具名/安装前缀的项目，`-cpp` 类模式可能本来就能用，不要照搬本条的
  「不可用」结论；
- 需要把「同一份交付物」在真机与模拟器上都跑通的场景，静态链接才值得；只跑真机时不必
  强行静态。

## 禁止模式

- 不要 `make -C src` 直连顶层 Makefile；
- 不要靠 touch 或解压顺序让随包 `parser.tab.c` 蒙混过关，也不要在没声明
  `tool_requires` 的情况下靠系统 bison 重新生成；
- 不要在 OHOS 上使用或假装支持 `-cpp`；
- 不要用 `-static-pie`（OHOS SDK 缺 `rcrt1.o`）；
- 不要用文本 `cmp`/`diff` 比较 `-orc` 与 `-bit` 的生成程序。

## 关联知识与交付

- 与 E074 / E525（HMDFS 上 make 无 FIFO jobserver，必须串行）相关，本例把「嵌套 make
  静默降级为 -j1」补成了显式决策依据。
- 与 tal 1.9 的 `-ansi` / `__STRICT_ANSI__` 记录相关，本例给出「去掉 `-ansi` 前后
  BuildID 相同」的实测证据，确认 sfront 不受该坑影响。
- 与 R38 / `commands.json` 相关，本例把 CLI 元数据与静态可执行交付一起闭环。
- 交付文件：`archives/s/sfront/0.99/**` 与软件级 `archives/s/sfront/commands.json`；
  本草稿仅落在 `knowledge/drafts/`，不修改正式知识图谱、正式文档和索引。
