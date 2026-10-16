# trimadap

trimadap 是 Illumina 测序数据的接头（adapter）修剪命令行工具。它对每条 read 与
每个接头序列做条带化 Smith-Waterman 比对，按启发式规则判定接头命中位置，并把接头
来源的碱基掩码为 `X`（`-t` 时直接剪掉）。默认接头取自上游 `illumina.txt` 中的
TruSeq 接头。

当前适配版本：

- `0.1-4`：plain Makefile 构建，依赖 `zlib/1.3.1`，打包 `trimadap-mt` 可执行文件。

## OHOS 适配要点

上游 `ksw.c` **只提供 SSE2 实现**并无条件 `#include <emmintrin.h>`，该头文件为 x86
专属，在 aarch64（OHOS）上无法编译。适配补丁 `patches/0001-ksw.c.patch`：

- 用 `#if defined(__SSE2__)` 把 SSE2 实现整块条件化，**x86/x64 代码路径与结果完全不变**；
- 为非 x86 主机提供等价的标量实现（线性 profile 布局、F 项直接传播），饱和运算
  语义与 `_mm_adds_epu8` / `_mm_subs_epu8` / `_mm_adds_epi16` / `_mm_subs_epu16` 一致。

`patches/0002-kthread.c.patch` 为 `kthread.c` 补 `#include <stdint.h>`：glibc 会经
`<pthread.h>` 间接暴露 `int64_t`，其他 libc 不会。

> 性能提示：标量内核为逐单元 DP，无 16/8 路并行，aarch64 上比 x86 的 SSE2 路径慢，
> 但同一输入的修剪结果与该 oracle 一致（见下）。
