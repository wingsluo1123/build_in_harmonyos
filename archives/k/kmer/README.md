# kmer

k-mer 分析与基因组组装工具箱（Celera Genomics / JCVI，GPL-2.0-or-later）：k-mer 计数与统计（`meryl`）、
contig 连接与分区（`leaff`）、cDNA/EST 比对（`sim4db`、`seagen`）、多序列 polish 工具族（`sim4dbutils/*`）、
`snapper2`、`tapper`，以及支撑它们的静态库（`libkmer`、`libmeryl`、`libseq`、`libbio`、`libsim4`、`libutil`）。

- 上游项目：http://kmer.sourceforge.net/
- 源码：`https://deb.debian.org/debian/pool/main/k/kmer/kmer_0~20150903+r2013.orig.tar.gz`
  （sha256 `8fd9c289244e69e38bb7709f3523d39edf1c2ced2cbcc687fcf00ecfca78ea47`，Debian 官方归档的原始上游发布包）
- 版本：`0-20150903-r2013`（2013 年 trunk 快照，版本号沿用赛事清单）

## 功能概述

- `meryl`：k-mer 计数、合并、比较、过滤与统计（kmer-mask / mapMers / build / dump ...）
- `leaff`：基于 meryl 的 reads 连接与分区
- `sim4db` / `sim4dbutils`：cDNA 与基因组比对的存储与后处理（pickBestPolish / sortPolishes / detectChimera ...）
- `snapper2` / `tapper`：重测序拼接与纠错
- `seagen`：EST 比对与过滤
- `libkmer` / `libmeryl` / `libseq` / `libbio` / `libsim4` / `libutil`：上述工具的静态库，公开头文件随包交付

## OHOS 适配

构建系统是该项目的自研非递归 GNU make（`Makefile` + `Make.rules` + `Make.include`），
各平台编译选项集中在 `configure.sh` 的一个 `case` 分支里，`configure.sh` 据此生成 `Make.compilers`。
HarmonyOS 不在它认识的系统名里，且继承得到的 Linux 分支硬编码了 `-m64`，因此：

1. **`patches/0001-configure-add-ohos-arm64-target.patch`** —— 为 `configure.sh` 增加 `OHOS-arm64` 目标块
   （`-fPIC -D_REENTRANT -O3 -D_THREAD_SAFE -pthread -fcommon -fno-strict-aliasing`，去掉 x86 专属的 `-m64`），
   配方以 `./configure.sh OHOS-arm64` 显式选择它。
2. **`patches/0002` / `patches/0003`** —— 2013 年的代码把 printf 格式宏直接粘在字符串字面量后面
   （`"count: "uint64FMT" mers"`）。clang++ 的 C++11 词法会把「字面量 + 标识符」读成用户自定义字面量后缀而报错，
   需在右引号与宏名之间补一个空格（宏展开后再拼接，字符串逐字节不变）。命中既有知识条目
   `DRAFT-cohomcalg-0.32-cpp11-literal-concat`：`libutil/util.h` 的 7 处宏定义 + 全仓 173 个翻译单元共 1986 处调用点。
3. 配方在 `build()` 中预置 `PWD`（HMDFS 上 `getcwd()` 与 libtool 式的 `cd $dir && pwd` 不可用，E114/E386），
   并按 R9 以 `make -j1` 构建、`make -j1 install` 安装到 `OHOS-arm64/`。

## 依赖关系

- 无第三方依赖：仅用 C/C++ 标准库与 `-pthread -lm`。
- 可选组件 ATAC/A2Amapper 需要 Python 2 的 `distutils` 与 Python 开发头文件，OHOS 上没有该环境，
  因此按上游 `configure.sh` 自带的行为（`WITHOUT_ATAC`）跳过，其余工具链全部构建。

## 功能验证

```bash
# 版本/用法（自带 --help 风格的用法输出）
bin/meryl --help | head -3
bin/leaff --help | head -3

# 消费者用例（链接安装后的静态库并调用公开 C API）
conan test <test_package 目录> kmer/0-20150903-r2013
# → KMER_CONSUMER_CHECKS=6 FAILURES=0 / KMER_CONSUMER_OK
```

## 参考

- [上游项目主页](http://kmer.sourceforge.net/)
- [源码归档](https://deb.debian.org/debian/pool/main/k/kmer/)
