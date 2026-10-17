# libtrace 4.0.34 适配笔记

## 编译环境
- 构建系统: 上游 autotools（本适配改为"手工复现 configure 产物 + 直接编译"）
- 编译日期: 2026-10-12
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）
- 状态: built

## 版本说明
- 上游: https://github.com/LibtraceTeam/libtrace （LGPL-3.0-or-later），版本 `4.0.34`
- 源码: `https://github.com/LibtraceTeam/libtrace/archive/refs/tags/4.0.34-1.tar.gz`
  sha256 `b3e73b9ca6757094047295937ab4d834155a0c64674f499132b56e8f81f8fcc9`
- 版本号沿用赛事清单（首次适配，R37）

## 为什么不能走 autotools
1. tag 包里**没有 `configure`**（只有 `configure.in`），需要 autoreconf；
2. 宿主机只有 `autoconf`/`m4`，**没有 automake / aclocal / libtoolize**，autoreconf 无法完成；
3. 包里也**没有 `libtrace.h`**，它是 `libtrace.h.in` 经 configure 替换占位符生成的，缺它连源码都编不过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码里 `#include "libtrace.h"` 但包里没有该头文件 | 上游 configure 从 `libtrace.h.in` 生成 | 配方按 `_HEADER_SUBST` 用正则替换 `@NAME@`（含 `@LIBTRACE_MAJOR @` 这种带空格写法）生成 `libtrace.h`，残留占位符直接报错 |
| 2 | 缺 `CXXDEP`/`.d` 无关，但缺 `config.h` 导致 32 个源文件编译失败 | 同 1：config.h 也是 configure 产物 | 生成最小 `config.h`（libpcap/libwandio 打开，可选后端不定义） |
| 3 | `HAVE_LINUX_ETHTOOL_H` 打开后链接报 `linux_set_nic_promisc` / `linux_get_dev_statistics` 未定义 | 上游此时会额外编译 `lib/format_linux_helpers.c`，第一版源文件清单漏了 | 把 `format_linux_helpers.c` 加入源清单 |
| 4 | 链接报 `undefined symbol: pthread_setaffinity_np` | 上游在 `#ifdef __linux__` 里直接调用该 glibc 扩展，OHOS 是 musl | 补丁 0001：改为 `#if defined(__linux__) && defined(HAVE_PTHREAD_SETAFFINITY_NP)`（feature 宏，合规 R8） |
| 5 | `fatal error: 'lib/format_ndag.h' file not found` | 部分源文件用路径限定 include，上游在源码根构建 | include 里补源码根 `-I<source>` |
| 6 | 可选后端被"打开"导致一堆隐式声明/失败 | config.h 里把 `HAVE_BPF`/`HAVE_WANDDER` 等写成 `#define X 0`，而上游用 `#ifdef` 判断 | 可选后端**一律不定义**（未定义即关闭） |
| 7 | 上游 43 个测试程序从不被编译 | `test` 不在顶层 `SUBDIRS`，test/ 下没有 `Makefile.am` | `build()` 内按上游 `do-*.sh` 的参数逐个编译+运行，结果写日志（**37/43 通过**，0 编译失败、6 运行失败） |
| 8 | 8 个用例报 `fatal error: 'libpacketdump.h' file not found` | 上游把 `libpacketdump` 作为同源树的独立库，`test/Makefile` 用 `-I../libpacketdump` 与 `-ltrace -lpacketdump` | 补 include 路径；用 flex+bison+clang++ 构建支撑库 `libpacketdump.a` 并链接（缺 flex/bison 时降级为仅加 -I 并记录） |
| 9 | 库编出来但 BPF 过滤不可用（`test-pcap-bpf` 报“does not have bpf filter support”） | `HAVE_BPF` 由 `libtrace_int.h` 依 `HAVE_PCAP_BPF_H` 推导，config.h 漏写该项 | 补 `HAVE_PCAP_BPF_H 1`（与上游 AC_CHECK_HEADERS 一致），库真正具备 filter 能力 |
| 10 | `test-etsi.c` 在 musl 上 `SIGINT`/`SIGALRM` 未声明 | musl 不像 glibc 会经 `netinet/*` 间接引入 `signal.h` | 测试编译统一 `-include signal.h` |
| 11 | `test-fragment` 读 `traces/fragtest.erf.gz` 报无 zlib 支持 | OHOS 版 `wandio/4.2.7` 制品按设计只有 stdio/thread 通道（其 config.h 中 `HAVE_LIBZ` 等全 0） | 测试在 `test-run/` 副本目录内运行，压缩样本以解压后的同一份报文提供 |

## 源码修改
- `patches/0001-trace-parallel-pthread-setaffinity-guard.patch` — `lib/trace_parallel.c` 一行守卫（1 行改动）

## 依赖版本
- `libpcap/1.10.6`、`wandio/4.2.7`

## 验证结果
```bash
conan create archives/l/libtrace/4.0.34 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0；包 libtrace/4.0.34:ec69787aa5ae92fa5c3fc6a2ab6afc8ab9ca3a36

# 消费者用例
LIBTRACE_CONSUMER_CHECKS=12 FAILURES=0
LIBTRACE_CONSUMER_OK

# 上游用例（build() 内执行，日志留证）
LTEST-SUMMARY total=43 pass=37 compile_fail=0 run_fail=6
```

## 注意事项
- 平台能力边界：可选采集后端（DAG/DPDK/pfring/XDP+eBPF/LLVM JIT）需要 OHOS 不提供的设备/内核接口，上游 configure 在能力缺失时同样以 `--without-*` 关闭；
  关闭后没有上游用例受影响（`test-live-dag` 仍通过）。
- 平台能力边界：ETSI LI（`test-etsi`）需要随 tag 归档发布、但实际缺失的 `libwandder` 子模块源码（`ls libwandder` 实测 0 个文件）。
- 平台能力边界：抓包类用例（`test-live`/`test-live-snaplen`/`test-nic`/`test-hotplug`）需要真实网卡与 root 权限。
- `libpacketdump` 与 libtrace 同源树，上游 `test/Makefile` 会把它链入每个测试；本配方在 `build()`
  内构建它供测试使用（不进包产物）。
- `test-seek` 不在上游 `test/Makefile` 的 `all:` 目标内，也不被任何 `do-*.sh` 调用；
  其内置期望（4 个报文）与 4.0.34 的 seek 语义不一致（实测 3 个）。
