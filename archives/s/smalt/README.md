# smalt

`smalt`（SMALT — Sequence Mapping and Alignment Tool）把 DNA 测序读段比对到参考基因组上：
先对参考序列按固定步长采样 k 词（默认 k=13、步长 2）建立哈希索引，对每条读段用索引里的
种子命中找出候选参考片段，再用 Smith-Waterman 动态规划做局部比对。支持 Illumina、Roche-454、
Ion Torrent、PacBio、ABI-Sanger 等多种平台的读段，支持单端与双端，输入可以是（gzip 压缩的）
FASTA/FASTQ，输出可以是 SAM 或 SMALT 自己的表格格式（不支持 SOLiD 颜色空间）。

上游作者 Hannes Ponstingl（Wellcome Trust Sanger Institute），GPL-3 许可，项目托管在
SourceForge 的 [smalt](https://sourceforge.net/projects/smalt/)。Debian 主仓的 `smalt`
0.7.6-4 → 0.7.6-13（jessie 到 trixie/forky/sid，area=main）都以同一上游 0.7.6 为源，
其 `debian/copyright` 的 `Upstream-Name` 即 SMALT、`Upstream-Contact` 即作者本人。

## 功能概述

- `smalt index [-k <wordlen>] [-s <stepsize>] <index_name> <reference>`：建哈希索引，产出
  `<index_name>.smi`（索引）与 `<index_name>.sma`（压缩参考序列库）
- `smalt map [-f <format>] [-o <out>] [-n <threads>] [-r <seed>] [-x] ... <index> <reads_A> [<reads_B>]`：
  映射单端或双端读段，输出 SAM（`-f sam`）、SMALT 表格（`-f smalt`）等；`-n` 多线程，
  `-r` 固定随机种子（并列最优比对的选择用到 `rand()`/`srand48()`）
- `smalt sample`：为双端读段估计插入片段长度分布
- `smalt check`：校验 FASTA/FASTQ 输入格式
- `smalt version` / `smalt help`：版本与用法（注意是子命令风格，`--version`/`--help` 会返回 51）
- 随包安装的 `misc/` 工具：`simread`（模拟读段）、`simqual`（模拟质量值）、`fetchseq`
  （按索引取参考子序列）、`splitreads`/`splitmates`（拆分读段/配对）、`mixreads`、
  `readstats`（读长统计）、`trunkreads`（截断读段）、`basqcol`（质量值统计）

## 依赖关系

- 编译依赖：`zlib/1.3.1`（静态变体）。zlib 不是可选项——上游测试驱动直接把 `.fa.gz`
  参考序列喂给 `smalt index`，且 `filio.c` 靠 `HAVE_ZLIB` 读写 gzip 压缩的 FASTA/FASTQ
- 链接 `-lm`、`-lpthread`：OHOS sysroot 里 `libm.a`/`libpthread.a` 是空壳兼容档案，
  相关入口点都在 libc 本身
- 运行依赖：无第三方共享库，10 个二进制的 `DT_NEEDED` 实测只有 `libc.so`
- 可选未启用：`bambamc`（BAM 输入/输出后端）、`samtools`（仅一个测试驱动需要）

## OHOS 适配要点

- **构建脚本的三元组支持（2 个补丁）**：tarball 自带 2009-11-20 版 `config.guess`/
  `config.sub`。worker 上 `uname -s` 返回 HarmonyOS，旧 `config.guess` 无对应分支，
  直接 "unable to guess system type" 退出；旧 `config.sub` 的 KERNEL-OS 白名单不含
  `linux-ohos`，把 `aarch64-linux-ohos` 当成 machine `aarch64-linux` 拒绝，而且即使补了
  白名单，末尾的 `-linux*)` 兜底还会用 sed 把它改写成畸形的 `-linux-gnu-ohos`。
  按仓库既有做法修补这两个脚本本身（E007/E072/E122/E205/E268），**不**用
  `--build/--host` 伪造三元组；补丁不含平台宏（R8/PF5）
- **HMDFS（1 个补丁）**：`configure` 里 config.status 用 `umask 077` 建临时目录，
  HMDFS 上会 Permission denied，改 `umask 000`（E002/E011，同 rsyslog 8.2404.0）
- **源码树内构建**：`test/Makefile.am` 硬编码 `-I../src/ -I../test`，out-of-source
  构建下测试程序找不到 `elib.h`，配方用 `self.folders.build = "."`
- **嵌套归档**：`libsgm_a_LIBADD = libseq.a` 让 `libseq.a` 成为 `libsgm.a` 的归档成员。
  OHOS lld 只告警 `archive member is neither ET_REL nor LLVM bitcode` 并正常链接；
  Apple ld64 会直接失败（只影响 macOS 原生便捷构建）
- **无 SIMD 分支**：`AC_CHECK_HEADERS([emmintrin.h])` 在 aarch64 上失败（OHOS SDK clang
  实测报 "only meant to be used on x86 and x64"），`WITH_SIMD` 关闭，走可移植 C 对齐路径
- **依赖注入**：按 E467/E505 不用 `AutotoolsDeps`（它把整个闭包塞进 `LIBS`，会让 autoconf
  最早的空链接探测在 OHOS/musl 上 rc=77），只注入 `-I`/`-L`
- **R26 系统同名库**：zlib 为静态变体，产物不向 OHOS `/lib` 投放任何同名 `.so`
- **信号量**：多线程走未命名 POSIX 信号量（`sem_init`/`sem_wait`/`sem_post`，musl 用 futex
  实现、不需要 `/dev/shm`）；命名信号量路径在 `#ifdef macosx_semaphores` 内，构建不启用。
  产物实测无 `sem_open`/`sem_unlink` 未定义符号
- **上游测试**：`make check` 注册 6 个 Python 集成驱动（CIGAR 比对、跨参考拆分、
  插入片段采样、多线程一致性等），另有 2 个随包分发的 C 测试程序
  （`sequenceReverseComplement_test`、`diffstr_test`，自身无断言）。这 8 项全部保留并实跑；
  驱动是 Python 2 代码，需机械移植到 py3（8 个补丁，不改断言与期望值，Debian 对同一
  上游版本携带等价 `2to3.patch`）。`AM_PATH_PYTHON([2.6])` 只探测 `python`/`python2*`，
  机器上只有 python3 时会把 `TESTS` 置空造成 `make check` 假通过，故配方显式传
  `PYTHON` 并硬断言 PASS 用例数
- **测试**：`test_package` 另补 17 个独立检查项 = 功能 8（F1-F8：CLI 面、index+map
  端到端与 5 条 SAM 记录的 flag/POS/CIGAR/NM/AS 逐项校验、未比对读段、伴随工具
  `readstats`/`fetchseq`）+ 鸿蒙特有 9（A1-A4 产物 ABI：aarch64 PIE ELF、musl 解释器、
  `DT_NEEDED` 只有 `libc.so`、无 RPATH/RUNPATH；H1-H5 设备端运行期：已签名安装产物就地
  执行、静态 zlib 解压 gzip 参考、多线程确定性、HMDFS 上索引文件可写且可被第二个进程
  复用、musl `rand()`/`srand48()` 固定种子下逐字节可复现）

## 参考资料

- 上游项目：<https://sourceforge.net/projects/smalt/>
- 上游文档：Sanger Institute 的 SMALT 软件页
- Debian 包：`smalt` 0.7.6-13（main，trixie/forky/sid），`debian/patches/2to3.patch`
- 版本级适配笔记：[0.7.6/notes.md](0.7.6/notes.md)、测试审计：
  [0.7.6/test_package/MANIFEST.yml](0.7.6/test_package/MANIFEST.yml)
