# smalt 0.7.6 适配笔记

## 任务名与上游判定

| 项 | 值 |
|----|----|
| 任务名（用户给出） | `smaltC++` 0.7.6，分支 `feat/smalt-0.7.6` |
| 最终包名 | `smalt` |
| 上游项目 | SMALT — Sequence Mapping and Alignment Tool（Wellcome Trust Sanger Institute） |
| 上游作者/联系 | Hannes Ponstingl `<hp3@sanger.ac.uk>`（configure.ac 的 AC_INIT 与 debian/copyright 的 Upstream-Contact 一致） |
| 上游托管 | SourceForge 项目 `smalt`（AC_INIT 的 homepage 为 smalt.sourceforge.net；debian/watch 指向 sf.net/smalt/smalt-(\d[\d\.]+).tar.gz） |
| 版本 | 0.7.6（NEWS 最新条目 "0.7.6 (21-03-2014)"；tarball 内 config.guess 时间戳 2009-11-20、configure 生成于 2014-03-21） |
| 源码 URL | <https://sourceforge.net/projects/smalt/files/smalt-0.7.6.tar.gz> |
| SHA256 | `89ccdfe471edba3577b43de9ebfdaedb5cd6e26b02bf4000c554253433796b31` |
| 真实 GET 校验 | 72,290,533 字节；`file` 判定 gzip compressed data（非 HTML/错误页）；tar 列出 125 个条目；conan source() 下载后 sha256 校验通过 |
| 构建系统 | autotools（tarball 自带 configure / Makefile.in，无需 autoreconf） |

判定依据（R51/§2.1：`<name>C++` 尾部可能只是语言标注，不能直接当仓库名）：

- 分支名 `feat/smalt-0.7.6` 给出包名 `smalt` 与版本 `0.7.6`（rule10 的 `feat/<库名>-<版本>` 口径）。
- Debian 主仓 `smalt` 的版本序列 0.7.6-4(jessie) → 0.7.6-6 → -8 → -9 → -12(bookworm) → **0.7.6-13(trixie/forky/sid, area=main)**，上游版本恒为 0.7.6，与任务版本精确对上；其 `debian/copyright` 写明 `Upstream-Name: SMALT`、`Upstream-Contact: Hannes Ponstingl <hp3@sanger.ac.uk>`、`Source: SourceForge 项目文件区`，`debian/watch` 为 `https://sf.net/smalt/smalt-(\d[\d\.]+)\.(?:tgz|tbz|txz|tar\.(?:gz|bz2|xz))`。
- tarball 自身自证：`configure.ac` 的 `AC_INIT([smalt],[0.7.6],[hp3@sanger.ac.uk],[smalt],[smalt.sourceforge.net])`；`README` 首行 "SMALT aligns DNA sequencing reads with a reference genome."，并给出 Sanger 文档地址。
- 候选与排除：
  - GitHub `rcallahan/smalt`(C)、`kiwiroy/smalt`(C，注明 mirror from SourceForge)、`hpon/smalt`(C，作者本人) —— 均为同一 SourceForge 项目的镜像/搬运，不是独立上游；选 SourceForge 官方文件区作为源（R39 官方源）。
  - `movingpictures83/SMALT`(标注 C++) —— 是另一篇文献（Postingl and Ning, 2020）的分析流程，无 0.7.6 版本，内容与本任务不符，排除。
  - `Axle-lang/smalt`(Rust 渲染器)、`veeso/smalto`(Gleam 高亮库)、`roquie/smalte`(Nim 配置工具)、`simonlindgren/smalt`(Python 社媒分析)、`jshi213/Smalt`(JS 播放器) —— 同名不同物，语言/用途/版本全不匹配，排除。
- **语言标注修正**：任务名的 `C++` 是标注误差。lang-preflight（R47）实测 `detected_language=c`（48 个源文件中 c:36 / python:12，主体占比 75%），构建系统 autotools，与 `manifest`/统计一致；上游仅 `test/Makefile.am` 里有一段**被注释掉**的 `dummy.cxx` C++ 链接权宜。按 §2.1「c↔cpp 兼容族」处理，lang-preflight exit 0（task=cpp, detected=c），不改变适配口径。

## 编译环境
- 构建系统: autotools（`configure` + `make`，三个子目录 src/test/misc）
- 编译日期: 2026-10-01
- 编译器: OHOS SDK clang 15.0.4（`--target=aarch64-linux-ohos --sysroot=<OHOS SDK>/native/native/sysroot`）
- 目标: ohos-aarch64（本机验证用 conan profile `ohos-local`，与 `ci/conan/profiles/ohos-aarch64` 同源配置，仅工具链路径指向本机 SDK）
- 状态: built（本地 `conan create` 通过 + `test_package` 产物 ABI 层 4/4 PASS；未 `conan upload`，R29 不伪造 published）

## 编译步骤

```bash
# 0) W0 依赖预检（R35：用 conan download 而非 conan list）
conan download zlib/1.3.1 -r=ohpcd --only-recipe     # → 配方存在（revision 2026-07-06）
conan download zlib/1.3.1 -r=ohpcd                   # → 制品仓含 OHOS 预编译二进制：
                                                     #   arch=armv8 os=OHOS os.version=6.0
                                                     #   clang 15 / libc++ / cppstd 17 / Release

# 1) 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight smalt 0.7.6 --src $BUILD_SRC_DIR
#   → 语言匹配: task=cpp, detected=c（兼容族），exit 0

# 2) 本地 OHOS 交叉验证（与 CI 同源的 conan 路径）
conan create archives/s/smalt/0.7.6 -pr:h=ohos-local -pr:b=ohos-local --build=missing
#   → source(): 72.3MB 下载 + sha256 校验通过
#   → build(): 11 个补丁全部应用；configure 报
#        checking build system type... arm-apple-darwin24.6.0
#        checking host system type... aarch64-unknown-linux-ohos   ← 补丁 0002 生效
#      make -j1 全绿；交叉编译下层 1 上游测试按设计跳过（目标 ELF 不可在本机执行）
#   → package(): Packaged 10 files（bin/）+ 12 '.py' files（share/）
#   → test_package: ohos_abi_check.py 4/4 PASS（A1-A4，实测 DT_NEEDED == [libc.so]）
#                    ohos_e2e_test.py 13 项按 can_run 门禁跳过，由 worker 实跑

# 3) 上游测试的本机原生实测（非鸿蒙证据，仅用于确定期望值与验证测试逻辑）
#    注：macOS 原生链接需先 `ar d src/libsgm.a libseq.a`（见问题表 #5）
./configure --with-bambamc=no PYTHON=$(which python3) && make -j8
make check            # → PASS×6：splitReads / results_split / ouform_cigar /
                      #            sample / cigar / mthread，rc=0
make -C test diffstr_test
python3 upstream_c_tests.py --test-dir test --workdir <writable>   # → RESULT: passed=6 failed=0
python3 test_package/ohos_e2e_test.py --bindir <install>/bin --workdir <writable>
                      # → RESULT: passed=13 failed=0（F1-F8 + H1-H5）
```

worker（HarmonyOS 真机/CI）上同一配方走的是原生路径：`-pr:h` 与 `-pr:b` 均为
`ci/conan/profiles/ohos-aarch64`，conan 不判定交叉，故不传 `--host`，由打过补丁的
`config.guess` 自行得出 `aarch64-unknown-linux-ohos`；`can_run()` 为真 →
`PYTHON=<sys.executable>` 注入 configure，`make check` 注册 6 个驱动并实跑，
`upstream_c_tests.py` 与 `test_package` 的 13 项设备端检查同样实跑。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`（"This script, last modified 2009-11-20, has failed to recognize the operating system you are using"），configure 第一阶段即中断 | 上游自带 2009 版 config.guess 无 `*:HarmonyOS:*:*` 分支；worker 上 `uname -s` 返回 HarmonyOS（E007/E205）。本机以假 uname（-s HarmonyOS / -m aarch64）复现：补丁前只打印诊断块并失败，补丁后输出 `aarch64-unknown-linux-ohos` | `patches/0001-config.guess.patch`：在首个 case 分支（`*:NetBSD:*:*)`）前插入 HarmonyOS 分支。**注意旧版脚本用 `echo ...; exit ;;`，没有新版的 `GUESS=` 变量**，直接照搬 `scripts/patch-autotools-ohos.pl` 的块会静默不生效；同版脚本也没有 `__ANDROID__`/LIBC 探测块，故不需要（也不引入）`__OHOS__` 宏，PF5/R8 无例外需求 |
| 2 | `config.sub` 拒绝目标三元组：`Invalid configuration 'aarch64-linux-ohos': machine 'aarch64-linux' not recognized`；带 vendor 位的 `aarch64-unknown-linux-ohos` 同样被拒 | 2009 版 config.sub 的 `maybe_os` KERNEL-OS 白名单（`nto-qnx* \| linux-gnu* \| linux-dietlibc \| linux-newlib* \| linux-uclibc* \| ...`）不含 `linux-ohos`，于是 `aarch64-linux` 被整体当成 machine（该版还不认识裸 `aarch64`，必须带 vendor 位）；E072/E122/E268 同类 | `patches/0002-config.sub.patch` 两处：①KERNEL-OS 列表加 `linux-ohos* \| \`；②基本系统类型列表加 `\| -linux-ohos* \`。第②处不可省——否则 OS 会落到末尾 `-linux*) os=$(sed 's\|linux\|linux-gnu\|')` 兜底，被改写成畸形的 `-linux-gnu-ohos`。实测补丁后 `aarch64-unknown-linux-ohos`/`arm-unknown-linux-ohos` 通过，且 `aarch64-unknown-linux-gnu`/`x86_64-pc-linux-gnu`/`arm-apple-darwin24.6.0` 回归无变化 |
| 3 | config.status 在 HMDFS 上创建临时目录会 Permission denied（E002/E011 类） | `configure` 内 config.status 模板用 `(umask 077 && mktemp -d "./confXXXXXX")`；HMDFS 上 0700 目录创建失败（与 rsyslog 8.2404.0、qsopt 2.5.10.3 同型） | `patches/0003-configure.patch`：两处 `umask 077` → `umask 000`；`build()` 另加 `os.umask(0)` 兜底 |
| 4 | out-of-source 构建失败：`test/sequenceReverseComplement_test.c:32:10: fatal error: 'elib.h' file not found` | 上游 `test/Makefile.am` 硬编码 `AM_CFLAGS = -I../src/ -I../test`，VPATH 构建下 `../src` 指向构建目录（只有 .a，没有头文件）；conan `basic_layout` 默认 out-of-source | `layout()` 里 `self.folders.build = "."` 改为源码树内构建（仓内既有惯例：redis/recode/runit/ripmime/rvvm）。实测 VPATH 下 configure 成功但 make 失败，改在树内构建后全绿 |
| 5 | macOS 原生构建链接失败：`ld: archive member 'libseq.a' not a mach-o file in 'libsgm.a'` | 上游 `src/Makefile.am` 写 `libsgm_a_LIBADD = libseq.a`，automake 把整个 libseq.a 作为**归档成员**塞进 libsgm.a（嵌套归档） | 无需补丁：用 OHOS SDK clang/lld 实测最小复现（libb.a 内含 liba.a）→ lld 仅告警 `archive member 'liba.a' is neither ET_REL nor LLVM bitcode` 并成功链接，产物为 `ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1`；conan create 全量构建同样通过。只有 Apple ld64 拒绝，影响的是 macOS 原生便捷构建（本机做上游测试实测时用 `ar d libsgm.a libseq.a` 绕过，不进配方） |
| 6 | `make check` 一个用例都不跑却 rc=0（假通过风险） | `AM_PATH_PYTHON([2.6])` 只探测 `python`/`python2*`；机器上只有 python3 时它把 `PYTHON` 设成 `':'`、`with_testdriver=false`，`test/Makefile` 的 `TESTS` 变空（实测 `am_cv_pathless_PYTHON=none`、`PYTHON=':'`、`WITH_TESTDRIVER_TRUE='#'`）。与 box2d 2.4.1 "ctest 空套件假通过" 同型 | 配方在目标可执行时显式传 `PYTHON=<sys.executable>`（conan 自己的解释器，必然存在）；实测 configure 后 `PYTHON = /opt/homebrew/bin/python3`、`TESTS = $(am__EXEEXT_6)`、`TESTS_ENVIRONMENT = $(PYTHON)`。并在 `build()` 里**硬断言 PASS 行数 == 6**，空跑或漏跑都会让 conan create 失败；交叉编译时改传 `PYTHON=:` 显式不注册（而不是留给环境决定） |
| 7 | 上游 6 个测试驱动在 python3 下直接 SyntaxError（`Missing parentheses in call to 'print'`、`truncated \UXXXXXXXX escape`），helper `testdata.py`/`formats.py` 同样是 py2 | 测试脚本是 2013-2014 年的 Python 2 代码；worker 上没有 python2（Python 2 已 EOL） | `patches/0004-0011` 做机械 py3 移植：`print` 语句 → `print()`；`cmp(a,b)` → `operator.ne(a,b)`（同为"不等则真"）；`Cigar` 补 `__ne__`（py3 不再从 `__cmp__` 派生）；`testdata.py` 解包 .gz 改二进制模式（py3 的 gzip 返回 bytes）；`results_split_test.py` 期望串里的 `\U` 转义修正为 `\\U`。**不改任何断言、期望值或用例逻辑，不删测试**。旁证：Debian 对同一上游版本（smalt 0.7.6-13）携带等价的 `2to3.patch`。实测移植后 `make check` 6/6 PASS（本机原生） |
| 8 | `AC_CHECK_LIB([z],[gzread])` 探测不到 conan 的 zlib | `AutotoolsToolchain` 只注入 CC/CXX/CFLAGS/CPPFLAGS(-DNDEBUG)/LDFLAGS，不含依赖的 `-I`/`-L`（实测生成的 conanautotoolstoolchain.sh 无依赖路径） | 按 E467/E505 **不使用 AutotoolsDeps**（它会把整个依赖闭包塞进 LIBS，令 autoconf 最早的空链接探测在 OHOS/musl 上 rc=77），改为只追加 `CPPFLAGS=-I<zlib>/include`、`LDFLAGS=-L<zlib>/lib`。实测 `HAVE_ZLIB 1`、`HAVE_ZLIB_H 1`，且 zlib 为纯静态包 → 产物 `DT_NEEDED` 只有 `libc.so`（R26） |
| 9 | `conan create` 在 source() 报 `BadZipFile: File is not a zip file`（下载与 sha256 均成功） | 源 URL 以 `/download` 结尾时，conan 落盘文件名就是 `download`，无扩展名 → `get()` 无法识别归档类型，退回 zip 解析 | 改用官方文件区的直链形式 `.../files/smalt-0.7.6.tar.gz`（仓内先例 pcre/8.45）。先以 range GET 实测该 URL 返回 `application/x-gzip` 且首字节 `1f8b 0800 8951 2c53` 与 `/download` 形式完全一致，再由 conan 全量 GET + sha256 校验通过（R39/PF7：官方源、非镜像、非 Debian 重打包） |
| 10 | 需要确认 SIMD 分支不会在 aarch64 上被误开 | `configure.ac` 用 `AC_CHECK_HEADERS([emmintrin.h])` 决定 `WITH_SIMD`/`-msse2` | 用 OHOS SDK clang 实测编译 `#include <emmintrin.h>`：`error: "This header is only meant to be used on x86 and x64 architecture"` → `withsse2=false`、`WITH_SIMD` 关闭，走可移植 C 对齐路径（config.h 实测 `/* #undef HAVE_EMMINTRIN_H */`），无需补丁 |
| 11 | CI 的 L2 smoke test 用 `--version`/`--help` 探活，而 smalt 是子命令风格（`smalt --version` → `ERROR: unknown task switch`，rc=51） | 上游 CLI 设计如此；`smalt version` 才是正确用法 | 实测包内 10 个二进制：`splitmates`/`splitreads`/`trunkreads` 对 `--version` 与 `--help` 均返回 0，故 conan-verify 的 L2（`if failed and not tested`）与 CI 的 L2（非阻塞 warn）都不会判负。设备端测试按上游真实用法断言（H1 用 `smalt version`，F1 用 `smalt help`，F2/F3 断言 rc=51 与错误文案） |
| 12 | CI worker 上 `source()` 反复失败：`IncompleteRead(7098096 bytes read, 65192437 more expected)`，3600 s 预算耗尽于下载重试（构建 #66867/#66928/#67854/#67875 在约 7 MB 处截断；#84948 拿到 28.8 MB 与 10.1 MB 后 `L1_RESULT=fail: conan create timed out`，编译与测试阶段未开始） | 72,290,533 字节的官方 tarball 在 worker 出口被中途截断，而 conan 不支持断点续传、每轮从 0 重下。CI 自带的两道兜底在 worker 上都失效：预下载步骤缺 `curl`（`[Errno 2] No such file or directory: 'curl'`），`build_and_test.sh` 的 `get_mirrors()` 没有 SourceForge 分支。本轮另实测：三条声明 URL 全部 301/302 落到**同一个** `master.dl.sourceforge.net` 均衡器（其余 `*.dl` 边缘主机 cytranet/freefr/netcologne/versaweb/tenet/razaoinfo/udomain/iweb/jaist/nchc/liquidtelecom 已不能解析），故逐 URL 回退并不带来机器多样性，也无法提升吞吐 | `source()` 改为并行 HTTP Range：先用 1 字节 range GET 探测总长（三条 URL 实测均返回 `206 Partial Content` + `content-range: bytes 0-0/72290533`），把 tarball 切成 18 个 4 MB range、8 路并发拉取，且**每个 range 内部按已落盘字节续传**（实测 cut 落点在 7/10.1/28.8 MB 不等，固定 range 也会被反复截断）；逐段校验 `Content-Range` 前缀，拼接后仍按 conandata 声明的 sha256 整体校验，size 或 digest 不符即抛 ConanException；conan 原生 `get()` 保留为回退路径。先例：`archives/g/gcc-snapshot/20260705`（并行 range + sha256 闸门）、`archives/b/barvinok/0.41.9`（Range 续传，同为 SourceForge 截断）。本机实测：对抗性截断（本地服务把每段响应在 1 MB 处断开、同时宣告完整 `Content-Length`）下 9 MB 样本经 6 次段内续传完整重组、sha256 通过、错误 sha256 被拒、临时文件无残留；`conan create`（ohos-local）rc=0，日志 `downloading smalt-0.7.6.tar.gz (72290533 bytes) in 18 parallel HTTP ranges` + `sources downloaded ... sha256 verified` |

## 源码修改

11 个补丁，全部由 `scripts/ohc-run.py refresh-patch --auto smalt 0.7.6` 从
`.orig`/`.work` 差异生成（R1/R3；生成前已确认 `.orig`/`.work` 为硬链接并逐个断链，
`find .work -type f -links +1 | wc -l` 由 120 降为 0）：

| 补丁 | 目标 | 内容 | 类型 |
|------|------|------|------|
| 0001 | `config.guess` | 新增 `*:HarmonyOS:*:*` 分支，按 `uname -m` 归一化 CPU 后输出 `<cpu>-unknown-linux-ohos`（+10 行） | portability，仅影响 HarmonyOS |
| 0002 | `config.sub` | KERNEL-OS 白名单加 `linux-ohos*`；基本系统类型列表加 `-linux-ohos*`（+2 行） | portability，仅影响 linux-ohos 三元组 |
| 0003 | `configure` | config.status 临时目录 `umask 077` → `umask 000`（2 处） | portability，HMDFS |
| 0004 | `misc/SAM.py` | py2 → py3（print 函数），无逻辑变化 | portability，非平台特定 |
| 0005 | `test/bam_cigar_test.py` | 同上 | 同上 |
| 0006 | `test/formats.py` | print 函数 + 为 `Cigar` 补 `__ne__` | 同上 |
| 0007 | `test/mthread_test.py` | print 函数 + 差异诊断信息更详细（期望值未改） | 同上 |
| 0008 | `test/results_split_test.py` | 期望质量串里的 `\U` → `\\U`（py3 转义），期望值本身未改 | 同上 |
| 0009 | `test/sample_test.py` | `cmp()` → `operator.ne()` + 诊断信息 | 同上 |
| 0010 | `test/splitReads_test.py` | print 函数 | 同上 |
| 0011 | `test/testdata.py` | print 函数 + 解包 .gz 改 `'wb'` 二进制模式 | 同上 |

**未修改任何 C 源码**：`src/`、`misc/*.c`、`configure.ac`、`Makefile.am`/`Makefile.in`
全部与 tarball 逐字节一致。补丁中不含任何平台宏（`__OHOS__` 等），符合 R8/PF5 默认禁令，
无需例外说明。0004-0011 属"一组逻辑变更"（py2→py3 移植），因 refresh-patch 采用
per-file 生成而拆成 8 个文件，评审时可作为一组阅读。

## 依赖版本

| 依赖 | 版本 | 用途 | 制品仓状态（W0/R35/R36 实测） |
|------|------|------|------------------------------|
| zlib | `zlib/1.3.1` | `HAVE_ZLIB`：gzipped FASTA/FASTQ 输入（`filio.c`），`smalt_LDADD += -lz`；**上游测试驱动直接喂 `.fa.gz` 参考序列，故非可选** | `conan download zlib/1.3.1 -r=ohpcd --only-recipe` → 配方存在；`conan download zlib/1.3.1 -r=ohpcd` → 含 OHOS 预编译二进制（arch=armv8, os=OHOS 6.0, clang 15, libc++, cppstd 17, Release）；包内只有 `libz.a`（静态） |
| 系统 | musl libc / libm.a / libpthread.a | 上游链接行 `-lm -lpthread` | OHOS sysroot 实测：`usr/lib/aarch64-linux-ohos/` 下 `libm.a`、`libpthread.a` 为空壳兼容档案，`libz.so` 存在但被 conan 的 `-L` 优先级让位给静态 `libz.a`；产物 `DT_NEEDED` 实测恰为 `[libc.so]` |
| bambamc | 未启用 | 可选 BAM 输入/输出后端 | 制品仓有 `bambamc/0.0.50` 配方（本仓 `archives/b/bambamc/0.0.50`，manifest status=built）。本配方按上游 README 记录的 `--with-bambamc=no` 构建，原因见"注意事项 #1" |
| samtools | 未启用 | 仅 `bam_cigar_test.py` 需要 | 制品仓有 `samtools/1.21`；因该驱动还依赖 BAM 输出（需 bambamc），本次不引入 |
| tool_requires | 无 | tarball 自带 configure/Makefile.in，无需 automake/libtool 自举 | — |

## 验证结果

```bash
# 本机 OHOS 交叉验证（与 CI 同源路径）
conan create archives/s/smalt/0.7.6 -pr:h=ohos-local -pr:b=ohos-local --build=missing
#   rc=0；11 个补丁全部应用；host system type = aarch64-unknown-linux-ohos
#   package(): Packaged 10 files + 12 '.py' files
#   test_package: PASS A1/A2/A3/A4 → RESULT: passed=4 failed=0
#                 13 项设备端检查按 can_run 门禁跳过（交叉编译，本机不可执行目标 ELF）

# 产物实测（llvm-readelf / file）
file <pkg>/bin/smalt
#   ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked,
#   interpreter /lib/ld-musl-aarch64.so.1, with debug_info, not stripped
llvm-readelf -d <pkg>/bin/smalt | grep NEEDED     # → 只有 [libc.so]
llvm-readelf -hl <pkg>/bin/smalt | grep -E 'GNU_STACK|GNU_RELRO'
#   GNU_STACK RW（NX）、GNU_RELRO + BIND_NOW（full RELRO）、FLAGS_1 NOW PIE → L4 友好

# 上游测试与设备端套件的本机原生实测（非鸿蒙证据，用于确定期望值/验证测试逻辑）
make check                                         # → PASS×6, rc=0（sample 38s、mthread 54s，合计约 100s）
python3 upstream_c_tests.py ...                    # → RESULT: passed=6 failed=0（C1-C6）
python3 test_package/ohos_e2e_test.py ...           # → RESULT: passed=13 failed=0（F1-F8 + H1-H5）
python3 test_package/ohos_abi_check.py --bindir <OHOS 包>/bin   # → RESULT: passed=4 failed=0
# 反向对照：同一 ABI 检查指向 macOS 原生产物 → FAIL A1（magic '\xcf\xfa\xed\xfe' 非 ELF），
#           证明 A1-A4 不是恒真断言
```

### 上游测试清点与实测（R51 三步法）

完整清点（16 个候选项的逐项计入/排除理由）见 `test_package/MANIFEST.yml` 的
`upstream_test_audit`。摘要：

- **计数口径（全仓统一，本任务唯一口径）**：独立可判定成败的测试项。上游侧一项 =
  一个随发行包分发的测试程序/脚本（automake `TESTS` 的一个条目，或一个 C 测试程序）；
  适配侧一项 = `test_package` 里一个单独输出 PASS/FAIL 的检查项。两侧都不按断言条数
  或子调用次数展开（子调用只作明细说明）。
- 上游 8 项 = 6 个 Python 集成驱动（`splitReads_test.py`、`results_split_test.py`、
  `ouform_cigar_test.py`、`sample_test.py`、`cigar_test.py`、`mthread_test.py`）
  + 2 个 C 测试程序（`sequenceReverseComplement_test`、`diffstr_test`）。
- 资产状态：A 类（6 个驱动有正式 runner 与逐条断言）+ B 类（2 个 C 程序随包分发但
  automake 不自动运行、自身无断言，由 `upstream_c_tests.py` 以 6 次带断言子调用
  C1-C6 判定）+ C 类语料（`test/data` 19 文件 / 69 MB，被驱动直接消费）。
- 排除项：`bam_cigar_test.py`（需 samtools 可执行文件且用 `-f bam`，需 bambamc）、
  `ioform_test.py`/`xali_test.py`（需 bambamc）、`testdata.py`/`formats.py`/`misc/SAM.py`
  （helper 模块）、`test/data`（语料）、21 个 `nodist_`/`WITH_TESTALL` 测试源
  （发行 tarball 不含，`WITH_TESTALL` 条件 `test -e ./test/seqSetIO_test.c` 为假）。
- 实测结论：8/8 全部可运行且通过（本机原生构建，py3 移植补丁生效后）；
  鸿蒙 worker 上由 CI 实跑同一套命令，本笔记不以 macOS 结果冒充鸿蒙结果。

### 鸿蒙特有测试设计（rule12，N = 9）

| 项 | 针对的鸿蒙适配点 | 断言 |
|----|------------------|------|
| A1 | aarch64 目标 + PIE | 10 个二进制全部 ELF64 LSB、`e_machine=EM_AARCH64(183)`、`e_type=ET_DYN` |
| A2 | OHOS musl 工具链/sysroot 真的生效 | `PT_INTERP == /lib/ld-musl-aarch64.so.1`（glibc 产物会是 `ld-linux-aarch64.so.1`） |
| A3 | R26 系统同名库不落地 + 静态 zlib | `DT_NEEDED` 无 libz/libm/libpthread/libc++，且含 `libc.so`；实测恰为 `[libc.so]` |
| A4 | 包会被搬移/装进版本化前缀 | 无 `DT_RPATH`/`DT_RUNPATH` |
| H1 | `.codesign` 执行约束：只跑真实安装产物 | 以 `<pkg>/bin/smalt` 原路径执行 `version`，rc=0 且输出 `Version: 0.7.6`；全程不 cp/mv/ln |
| H2 | 静态链入的 zlib 在 musl 上可用 | 从 `.fa.gz` 参考建索引再映射，5 条记录与未压缩索引结果完全一致 |
| H3 | `threads.c` 的 pthread + 未命名 POSIX 信号量在 musl 上的行为 | `map -n 4` 与 `-n 1` 的记录集合按查询名排序后完全一致（上游明确 -n 不保序） |
| H4 | HMDFS/沙箱文件系统 + E002（`/tmp` 只读） | `.smi`/`.sma` 落在调用方指定的可写目录（非 `/tmp`）、非空，且能被第二个进程重新使用 |
| H5 | musl 的 `rand()`/`srand48()` 与 glibc 实现不同（`randef.h`/`sort.c` 用其做并列最优选择与随机化快排枢轴） | 固定 `-r 42` 连跑 3 次，3 份 SAM 记录逐字节一致 |

**H3 的前置事实（信号量可用性）**：仓内 `archives/a/abyss` 记过"鸿蒙系统不支持 POSIX
信号量（sem_t）"，那指的是**命名**信号量（`sem_open` 依赖 `/dev/shm`）。smalt 的命名
信号量路径整段包在 `#ifdef macosx_semaphores` 里，而构建从不误开该宏
（`grep -rn macosx_semaphores` 在 `*.am`/`*.in`/`configure*`/`config.h*` 中零命中）；
默认走 `sem_init(&fifop->sema, 0, 0)` 的**未命名**信号量，musl 以 futex 实现、不需要
`/dev/shm`。对交叉编译产物实测 `llvm-nm --undefined-only <pkg>/bin/smalt` 只有
`sem_init`/`sem_post`/`sem_wait` 与 `pthread_create`/`pthread_join`/`pthread_mutex_*`，
**没有** `sem_open`/`sem_unlink`/`sem_close`，即编进产物的正是未命名信号量路径。
H3 在 worker 上对这条路径做端到端确认（`map -n 4` 与 `-n 1` 结果一致）。

A1-A4 为纯 Python ELF 解析，不依赖外部工具，交叉编译时也能对**真实产物**执行；
H1-H5 必须在鸿蒙真机/worker 上跑，由 `can_run()` + `user.build:flex_bison_native`
双重门禁控制（同 ylva 1.7 / libidl2 0.8.14 / secpwgen 1.3 先例）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/smalt` | ~260 KB（本机原生构建实测；OHOS PIE 产物同量级） | 主程序：`index` / `map` / `sample` / `check` / `version` / `help` |
| `bin/{simread,fetchseq,splitreads,mixreads,readstats,splitmates,trunkreads,basqcol,simqual}` | 各数十~百 KB | 上游 `misc/` 的读段模拟/抽取/统计工具，随 `make install` 一并安装 |
| `share/*.py`（12 个） | ~60 KB | 上游 `make install` 安装的测试驱动与 `SAM.py`（`test/data` 的 69 MB 语料**不**安装：`DIST_SUBDIRS` 只影响 dist，不进 install） |
| 软件级 `commands.json` | — | R38/L0k：CLI 工具声明（`type: tool`，`versions["0.7.6"].ref = smalt/0.7.6`，`binary: false` 待制品仓发布后改 true） |

## 注意事项

1. **BAM 输入/输出未启用**（`--with-bambamc=no`）。上游 0.7.6 没有为主程序接通 C++
   链接：`configure.ac` 的 `AC_PROG_CXX` 被注释、`src/Makefile.am` 的 `smalt_LDADD`
   不含 C++ 运行时、`test/Makefile.am` 里用于触发 C++ 链接的 `dummy.cxx` 也整段被注释。
   直接 `--with-bambamc=yes` 会走 `PKG_CHECK_MODULES([BAMBAMC])` 并把 `-lbambamc`
   加进纯 C 链接行。启用它需要先补 C++ 链接路径（AC_PROG_CXX + 链接期用 CXX 或补
   `-lc++`），属后续项；本配方采用上游 README 自己记录的 C-only 配置，核心能力
   （FASTA/FASTQ 含 gzip 输入 → SAM/SMALT 输出、单双端、多线程、`sample` 插长估计）完整。
2. `smalt` 是子命令风格：`smalt --version` / `--help` 返回 51 并打印
   `ERROR: unknown task switch`，正确用法是 `smalt version` / `smalt help`。
   CI 的 L2 smoke（非阻塞 warn）与 conan-verify 的 L2 因为包内 `splitmates`/
   `splitreads`/`trunkreads` 对 `--version` 返回 0 而不会判负（实测）。
3. 多线程映射不保证读段顺序（上游 `-n` 文档明示），所以 H3 与 mthread_test 的比较
   都必须与顺序无关。
4. `smalt` 用 `rand()`/`srand48()`，未给 `-r` 时以 `time(0)` 播种；需要可复现结果时
   必须显式 `-r <seed>`（H5 固定 42）。
5. 21 个 `nodist_`/`WITH_TESTALL` 测试源不随发行包分发，官方发行配置下从不注册，
   本次无法运行（上游发行策略，非本适配裁剪）。
6. `test/data` 语料共 69 MB，只在构建目录内被上游驱动消费，**不**进 Conan 包，也
   **不**进 test_package（后者用 `case_gen.py` 自带的 1200 bp 合成参考，自包含且秒级）。
7. `conan-verify` 的 G0 会打印"⚠️ 已知风险 E490 未在配方中处理"，这是**工具误报**：
   `scripts/ohc/conan_verify.py` 的 `_check_risk_addressed()` 只识别 E007/E011/E092/E090
   四个条目，其余一律返回 False。本配方实际已按 E490 处理——`_restore_autotools_modes()`
   在 configure 之前对 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`/
   `depcomp`/`compile`/`ltmain.sh` 补回 owner/group/other 执行位（`os.chmod` + `stat.S_IX*`）。
   G0 判定仍为 PASS（非阻塞），该检测缺口已写进 SKILL_FEEDBACK。

## 路径 B（知识库拓展）评估

- `config.guess`/`config.sub` 的 HarmonyOS 三元组问题：engine/知识库**已覆盖**
  （E007 patch-autotools-script、E072 invalid triplet、E122 add-linux-ohos-to-validation、
  E205 patch-script、E268 patch-autotools-ohos.pl 误判、E490 helper 脚本权限），
  本次按既有知识解决 → **路径 A**。
- 两处"既有知识的形态盲区"如实记录，建议由主编决定是否补进既有条目（本次不自行新开条目）：
  1. **2009 版 config.sub 需要改两处**：E122 只讲 KERNEL-OS 校验列表，且给的 sed 模板
     针对新版 `linux-uclibc*- )` 形态；2009 版是 `linux-uclibc* | \` 续行形态（模板不匹配），
     并且末尾还有 `-linux*) os=sed s|linux|linux-gnu|` 兜底会把 `-linux-ohos` 改写成
     `-linux-gnu-ohos`，必须同时把 `-linux-ohos*` 加进基本系统类型列表。
     另：2009 版 config.guess 用 `echo + exit`，没有新版 `GUESS=` 变量，
     `scripts/patch-autotools-ohos.pl` 的块照搬会静默失效（该脚本的 2.1/2.2 步
     也依赖 `android-linux)` 与 `gnu* | android*` 文本，2009 版都不存在）。
  2. **测试入口静默空转的又一新形态**：`AM_PATH_PYTHON([2.6])` 在只有 python3 的机器上
     把 `PYTHON` 设为 `':'` 并使 `TESTS` 变空，`make check` 0 用例 rc=0。与
     `DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass`（ctest 空套件假通过）同类，
     建议 merge-into 该草稿，通用判据是"必须断言实际执行的用例数，而不能只看 rc"。
- 结论：本次**不新增路径 B 候选**（问题均被既有知识覆盖或属既有条目的形态补充）。

## 参考资料

- 上游项目：<https://sourceforge.net/projects/smalt/>（文档：Sanger Institute SMALT 页面）
- Debian：`smalt` 0.7.6-13（main，trixie/forky/sid），`debian/copyright`、`debian/watch`、
  `debian/rules`、`debian/patches/{series,2to3.patch}`
- 仓内先例：`archives/y/ylva/1.7`（application + 分层测试 + 任务名 `<name>C++` 判定）、
  `archives/s/scamp/2.15.0`（autotools + `make check` 过滤 + umask/HMDFS）、
  `archives/i/imageworsener/1.3.5`（E467/E505 的 `-I`/`-L`-only 依赖注入）、
  `archives/r/rsyslog/8.2404.0`（config.guess/config.sub + umask 补丁）
- 知识条目：E002/E007/E011/E072/E122/E205/E268/E467/E490/E505、R8/R26/R29/R33/R35/R36/R38/R39/R47/R51

## 归档状态

- 归档状态: built —— 本地 `conan create`（profile ohos-local）+ `conan-verify`
  （G0/G1/G2/G3/G4 与 L2/L4/L5 全 PASS）+ `finish` 的 W3 本地 CI 模拟
  （L0_RESULT=pass、L1_RESULT=pass: upstream tests + test_package executed、
  L1e 破坏性反向验证通过、L5_RESULT=pass）均通过；未执行 `conan upload`，
  按 R29 不标 published，制品仓发布由合入 main 后的 release 流水线完成。
---

**编译结束**: 2026-10-01 04:15
**最终状态**: built

## 上游测试申报数修正（2026-10-02，PC 鸿蒙化审查 rule4）

审查判定 rule4 FAIL：少报（上游实测 N=11 > 声明 N=8）。核实后**审查方正确**，已按「先全量发现、
后排除、就高不就低」修正申报口径：

- `test/` 内随发行 tarball 分发的测试程序/脚本共 **11 个**（9 个 .py + 2 个 .c，实测 `ls` 逐一核对）。
  初版把 bam_cigar_test.py、ioform_test.py、xali_test.py 三个驱动按「本构建配置下不注册」排除在
  申报总数之外（只计入 8），属主动少算，已改为 counted: true 并新增 runnable: false 标记。
- 修正后：上游申报 **11** 项 = 单元 2（C 程序）+ 集成 9（Python 驱动）；其中**可运行 8 项、
  通过率 100%**（make check 6/6 + upstream_c_tests.py 6 次带断言子调用覆盖 2 个 C 程序），
  **不可运行 3 项**并附具体技术原因：三者都依赖 BAM 输入输出后端（ioform/xali 仅在 WITH_BAMBAMC
  为真时注册；bam_cigar 仅在 WITH_SAMTOOLS_EXEC 为真时注册且调用 `smalt map -f bam`、`-f bam:x`），
  而本配方按上游 README 记录的 C-only 配置 `--with-bambamc=no` 构建 —— 上游 0.7.6 未为主程序接通
  C++ 链接（`AC_PROG_CXX` 被注释、`smalt_LDADD` 无 C++ 运行时、`dummy.cxx` 权宜整段被注释）。
  三个文件在包内源码树原样保留：未删除、未改写断言、未标记跳过。
- 适配后合计由 25 修正为 **28** = 上游 11（不变）+ 功能补全 8（F1-F8）+ 鸿蒙特有 9（A1-A4、H1-H5）。
- 同步更新：`test_package/MANIFEST.yml`（upstream_test_total、计数汇总、三项 counted/runnable 与 reason、
  新增 upstream_test_declared/runnable/not_runnable 与原因字段）、版本级 `manifest.yaml`
  （upstream_test_total、assertion_count、audit 与 reason）、PR 正文两张表与「验证结果」段。
  本文上文「上游测试清点与实测（R51 三步法）」小节中出现的 8 项口径以本节为准。

## 路径 B 结论更新（2026-10-02，取代上文「不新增路径 B 候选」一句）

上文第 1 项（pre-2010 config.guess/config.sub 形态盲区）已完成完整撞库与实测取证，**沉淀为路径 B 知识草稿**：`knowledge/drafts/DRAFT-smalt-0.7.6-pre2010-config-guess-sub-ohos-triplet.kv` 与同名 `.md`（成对）。本 PR 因此按**路径 B（知识库扩展）**申报，标题前缀改为【知识库扩展】。

- 撞库证据：`engine` 命中 E160；index.tsv 关键词检索命中 E007/E072/E099/E122/E149/E153/E160/E205/E245/E253/E268/E279/E387/E490；而对 `GUESS=`、`2009-11-20`、`last modified 2009`、`linux-gnu-ohos` 四个关键词 grep `knowledge/doc/` **0 命中** —— 两个核心事实（旧版 echo+exit 收尾形态、只补一处会以 rc=0 静默产出畸形三元组）在正式知识库中均无覆盖。
- 工具复核：`draft-review` 质量预检 signature/root_cause/rec 全通过；最相似正式条目 E007 score=0.34（E160 0.27、E205 0.24），三态建议 review-similar（灰区，纳入决策权在主编）；`graph validate` 通过（仅存量 C13/C14 告警，与本草稿无关）。
- 上文第 2 项（AM_PATH_PYTHON 只探测 python/python2* 导致 TESTS 变空、`make check` 以 `All 0 tests passed` 假绿）**不单独申报**：同类已由 E694（AM_PATH_CPPUNIT 探测失配假绿）、E6403（check_PROGRAMS 无 TESTS）、E544/E321（ctest 零用例）与 `DRAFT-cracklib-2.9.8-dist-missing-check-scripts`（AM_PATH_PYTHON 版本截断）覆盖，按「不重复」铁律只在配方侧落实防御（显式传 PYTHON + 硬断言 PASS 行数 == 6），实测证据保留在本笔记与 `reports/test-report.md`。
