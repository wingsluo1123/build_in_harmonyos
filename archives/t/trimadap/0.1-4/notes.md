# trimadap 0.1-4 适配笔记

## 编译环境

- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-10-15
- 平台: HarmonyOS / aarch64（OHOS，原生构建，非交叉编译）
- 编译器: clang 15.0.4 (`/data/service/hnp/bin/clang`, target `aarch64-unknown-linux-ohos`)
- 状态: built

## 上游来源核验（版本号 0.1-4 的确定依据）

- 上游仓库: https://github.com/lh3/trimadap （无 tag，`trimadap-mt.c` 内 `#define VERSION "r11"`）
- 版本号 `0.1-4` 来自 FreeBSD ports `biology/trimadap`：`DISTVERSION= 0.1-4`，
  `DISTVERSIONSUFFIX= -gec5a764`，即对应上游提交 `ec5a764`
- 已核验该提交存在: `ec5a764e1834363ae0c4b52f52bdb114ff7af265`（2022-03-17,
  commit message `added license`），与 FreeBSD 发行包名 `trimadap-0.1-4-gec5a764` 一致
- 源码 tarball: https://github.com/lh3/trimadap/archive/ec5a764e1834363ae0c4b52f52bdb114ff7af265.tar.gz
- SHA-256: `40f1c0d0266d7c06f37392e6c73af7ef78a140ef74c740bf0e86bbf1e3654d05`
- 许可: MIT（`LICENSE.txt`，Copyright (c) 2014-2017 Broad Institute, Inc.）

## 依赖（W0 预检）

- `zlib/1.3.1`：已发布到制品仓（`conan download zlib/1.3.1 -r=ohpcd --only-recipe` 成功），
  无需先行适配依赖，无依赖库附加分场景
- 其余链接项 `-lm -pthread` 由系统提供
- trimadap 为命令行工具（产物 `bin/trimadap-mt`），按 R38 需要 `commands.json`

## 语言预检（R47）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight trimadap 0.1-4 --src <src>
# ✅ 语言匹配: task=cpp, detected=c
# language_evidence:
#   build_system:  make
#   manifest:      顶层 Makefile（无更强 manifest）
#   source_stats:  源文件 3 个（c:3），主体占比 100%
```

## 编译步骤

1. `ohc-run.py init-build trimadap 0.1-4 --url=<commit tarball>`（下载 → .orig/.work → 归档骨架）
2. 语言预检（R47）通过
3. 修改源码解决 aarch64 不可编译问题（见下），`make CC=clang CFLAGS="-g -Wall -O2 -Wno-unused-function"`
4. 端到端运行上游 `test.fa` 校验修剪结果
5. `refresh-patch --auto` 生成 2 个补丁（源码改动全部固化为补丁，归档不携带手工产物）
6. `conanfile.py` 按 seqtk（同为 lh3 plain-Makefile 工具 + zlib）已验证形态编写

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ksw.c` 在 aarch64 上无法编译（`'emmintrin.h' file not found`） | 上游 ksw.c 只有 SSE2 实现且无条件 `#include <emmintrin.h>`（x86 专属头），无任何非 x86 分支 | `patches/0001-ksw.c.patch`：用 `#if defined(__SSE2__)` 整块条件化 SSE2 实现（x86 路径与结果不变），非 x86 提供等价标量内核 |
| 2 | 标量内核必须复刻饱和算术 | SSE2 用 `_mm_adds_epu8` 后 `_mm_subs_epu8` 两步饱和；写成单个 `clamp(h + S - shift)` 在 `h+S>255` 时结果不同 | 标量内核按 SSE2 的运算顺序逐步饱和（KSW_ADDS_U8 / KSW_SUBS_U8 / KSW_ADDS_I16 / KSW_SUBS_U16） |
| 3 | `kthread.c` 报 `unknown type name 'int64_t'` | kthread.c 只包含 `<pthread.h>/<stdlib.h>/<limits.h>`，glibc 会间接带出 `int64_t`，OHOS 的 libc 不会 | `patches/0002-kthread.c.patch`：显式 `#include <stdint.h>` |
| 4 | `ksw.c` 注释里的 `KSW_ADDS_*/` 提前闭合块注释导致大量语法错误 | C 注释中的 `*/` 序列 | 改写注释措辞，避免 `*/` 出现在注释正文 |

> 参考先例：同仓库 `archives/f/fermi-lite/0.1/patches/0001-ksw.c.patch` 对**同源同文件**
> 的 `ksw.c` 采用同一策略（`__SSE2__` 条件化 + 标量回退）。两版 ksw.c 差异极小
> （trimadap 版多 `#include <string.h>`、两处 `score2` 比较修正、`ksw_align` 用 `copy`
> 缓冲避免改写入参、尾部多 `#ifdef _KSW_MAIN` 主程序），本补丁按 trimadap 版本重写，
> 并额外保持了 SSE2 的**两步饱和**语义（先加后减各自饱和）。

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| `0001-ksw.c.patch` | `ksw.c` | `#include <emmintrin.h>` 与 SSE2 实现（`ksw_qinit`/`ksw_u8`/`ksw_i16`）整块包进 `#if defined(__SSE2__) … #else … #endif`，`#else` 分支给出等价标量实现（线性 profile 布局、F 项行内直接传播） |
| `0002-kthread.c.patch` | `kthread.c` | 增加 `#include <stdint.h>` |

- 两处修改对 x86/x64 平台完全透明：`__SSE2__` 分支保留上游代码原样
- 补丁不含 `__OHOS__` 宏（R8 口径）；平台分支依据的是 ISA 能力宏 `__SSE2__`
- `.orig` 应用补丁后的结果与 `.work` 逐字节一致（已验证 `patch -p1` + `cmp`）

## 上游测试清点（R51）

上游**没有测试套件**，清点证据：

```bash
$ grep -n "^[a-z]" Makefile      # Makefile 仅 10 行，只有 all / trimadap-mt / clean 目标
all:trimadap-mt
trimadap-mt:trimadap-mt.c ksw.c kthread.c kseq.h ksw.h
	$(CC) $(CFLAGS) -pthread ksw.c kthread.c trimadap-mt.c -o $@ -lz -lm
clean:
$ make -n check                  # → make: *** No rule to make target 'check'
$ ls                             # 无 tests/ 目录、无 ctest/pytest 注册
LICENSE.txt Makefile README.md illumina.txt kseq.h ksw.c ksw.h kthread.c test.fa trimadap-mt.c
```

- 仓库根目录无 `tests/`，无 `configure`/`CMakeLists.txt`，无任何测试注册（ctest/pytest 均不适用）
- 上游自带唯一测试数据为 `test.fa`（6 条 read，覆盖 3'/5' 端接头），打包生态把它当
  冒烟数据使用：Homebrew 的 `brew test trimadap` 断言
  `assert_match(/^1 +ATCTCGTATGCCGTCTTCTGCTTG$/, shell_output("#{bin}/trimadap #{doc}/test.fa 2>&1"))`
  —— 即第 4 个默认接头 `ATCTCGTATGCCGTCTTCTGCTTG` 的命中数为 **1**
- 因此本适配在 `test_package/` 中补全真实功能测试（见下），并在 MANIFEST.yml 中如实申报

## 验证结果

### 端到端（aarch64 标量路径）

```bash
$ ./trimadap-mt -v
r11

$ ./trimadap-mt test.fa        # stderr 计数行
2               AATGATACGGCGACCACCGAGATCTACACTCTTTCCCTACACGACGCTCTTCCGATCT
4               AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC
1               AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGTAGATCTCGGTGGTCGCCGTATCATT
1               ATCTCGTATGCCGTCTTCTGCTTG
```

- 跨架构 oracle：Homebrew（x86 SSE2 构建）期望第 4 个接头命中数为 1，本适配 aarch64
  标量路径实测 **1**，一致
- 6 条 read 的掩码边界与 read 中接头的已知位置一一对应（例：read 1 = 82 bp 插入片段
  + 18 bp `AGATCGGAAGAGCACACG`，输出为插入片段 + 18 个 `X`）
- 多线程一致性：`-p 4` 与单线程 stdout 逐字节相同（`cmp` 通过），验证 kthread 路径

### test_package（消费者视角，真实执行被测二进制）

两层，均真实执行打包出的 `trimadap-mt`：

**① 完整消费者端到端用例 `test_consumer.c`（鸿蒙/PC 特有覆盖）**

模拟真实部署形态：下机 gzip FASTQ → trimadap 作为流式接头过滤器（`-p 4` 多线程）
→ 下游消费者独立解析产出 FASTQ 校验；再走 `-t 8` 剪切流水线。该用例同时覆盖 OHOS
平台相关路径——gzip 输入经 **OHOS zlib**（`gzFile`）、多线程经 **OHOS pthread /
kthread.c**、接头比对在 aarch64 上走**本适配新增的标量内核**（SSE2 属 x86 路径）。

输入 64 条读段（固定种子，长度与期望掩码可精确推导）：82bp 插入片段 + 18bp 精确
3' 接头；100bp 无接头对照；30bp 5' 通用接头 + 70bp 插入片段；70bp 插入片段 +
12bp 3' 接头前缀。实测：

```bash
$ ./test_consumer <trimadap-mt> <workdir>
trimadap 消费者端到端用例（64 条读段，gzip 输入）
  ok   : 生成 gzip 压缩 FASTQ 输入（经 OHOS zlib）
  ok   : 流程① trimadap -p 4（多线程 gzip 流式）退出码为 0
  ok   : 流程① 产出记录数与输入一致（下游消费者独立解析）
  ok   : 流程① 输出长度与输入一致
  ok   : 流程① 非掩码区与输入逐字节一致
  ok   : 流程① 掩码区连续且贴合读段某一端
  ok   : 流程① 3' 精确接头后缀被整段掩码（18 bp，16 条读段）
  ok   : 流程① 无接头对照读段完全不变（16 条读段）
  ok   : 流程① 5' 通用接头被整段掩码（30 bp，16 条读段）
  ok   : 流程① 3' 接头前缀被掩码（12 bp，16 条读段）
  ok   : 流程② trimadap -t 8（剪切模式）退出码为 0
  ok   : 流程② 产出记录数与输入一致
  ok   : 流程② 每条读段精确等于已知插入片段（下游可直接使用）

trimadap consumer e2e: 13 passed, 0 failed
```

**② CLI 行为断言 `test_trimadap.sh`**：13 条（上游样本数据端到端 + Homebrew 跨架构
oracle + 构造型用例 + `-t`/`-3`/`-p` 行为）。

```bash
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify trimadap 0.1-4
# G2 conan create 通过（含 test_package 两层测试实际运行）
```

> 说明：`test_package/conanfile.py` 用 `layout()` 把生成器与编译产物落在 `build/`，
> 避免 conanrun/conanbuild 环境脚本污染归档目录（与 accel-config 配方同口径）。

## 注意事项

- 标量内核为逐单元 DP，无 SSE2 的 16/8 路并行，aarch64 上单线程吞吐低于 x86；
  同一输入的修剪结果与 x86 oracle 一致，属预期性能差异而非功能差异
- 上游 `-t` 选项默认 1000000，即默认**不真正剪切**，只把接头碱基掩码为 `X`；
  `-t N` 时才切除 `X` 段（两端各保留至少 N bp）
- `ksw_align` 的 SSE2 条带实现与标量实现均为上游算法的等价表述；trimadap 自身文档
  即声明该启发式修剪"fast but inaccurate"，本适配未改变判定规则
---

**编译结束**: 2026-10-15 13:23
**最终状态**: built
