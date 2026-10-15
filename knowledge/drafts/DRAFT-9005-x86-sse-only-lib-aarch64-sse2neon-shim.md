# DRAFT-9005-x86-sse-only-lib-aarch64-sse2neon-shim

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-9005-x86-sse-only-lib-aarch64-sse2neon-shim.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-9005: x86 SSE intrinsic 专用库在 aarch64 上的可移植适配模式（sse2neon 转译层 + CMake 架构判定）

- 条目主题：把只提供 x86 SSE2/SSE4.1 intrinsic 实现的 C/C++ 库适配到 HarmonyOS PC（aarch64）时，
  用 sse2neon 转译层 + 构建系统架构判定替代"逐文件重写内核"的通用做法与诊断清单。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxxx）
- 关联 PR：feat/pftools-3.2.12（本题由 pftools 3.2.12 适配实证）

## 适用场景

源码在 aarch64 上编译时报：

```
fatal error: 'emmintrin.h' file not found
error: "This header is only meant to be used on x86 and x64 architecture"
fatal error: 'smmintrin.h' file not found
error: unrecognized instruction mnemonic        (x86 内联汇编)
```

且满足以下任一特征（说明库是"x86 SIMD 专用"而非单纯构建配置问题）：

- 核心头文件无条件 `#include <emmintrin.h>` / `<smmintrin.h>` / `<xmmintrin.h>`；
- 库无标量/NEON 回退实现；
- 上游所有分支均无 `__ARM_NEON` / `aarch64` 代码；
- 程序通过函数指针在运行时切换 SSE2/SSE4.1 实现，删除 SIMD 编译单元会直接导致未定义符号。

## 处置流程

1. **判定性质**：先区分"构建配置问题"（可关开关）与"架构缺失"（必须引入转译/重写）。
2. **引入转译层**：`sse2neon.h`（MIT，<https://github.com/DLTcollab/sse2neon>，固定 tag + sha256）。
   作为"额外 source"由配方拉取，单头文件用 `download()` 而非 `get()`。
3. **垫片重定向，不改几百处 include**：新增 `src/<lib>/simd/` 目录放
   `{emmintrin,smmintrin,xmmintrin,mm_malloc}.h`（各只有一行 `#include "sse2neon.h"`），
   构建系统**仅非 x86 架构**加入该 include 路径。不要用 `#ifdef __OHOS__` 之类的平台宏（R8）。
4. **清掉 x86 内联汇编**：改写为等价 intrinsic（见速查表）。
5. **停用 x86 CPU 探测**：`cpuid`/`xgetbv`/`bsrq` 加 x86 门控 + 非 x86 回退分支。
6. **验证必须是行为级**：跑上游测试；有"逐字节比对参考输出"的用例务必通过（见 DRAFT-9006）。

## x86 内联汇编 → intrinsic 速查

| x86 asm | 等价 intrinsic |
| --- | --- |
| `xorps %0,%0` / `pxor %0,%0` | `_mm_setzero_ps()` / `_mm_setzero_si128()` |
| `movaps %1,%0; maxps %2,%0` | `_mm_max_ps(a, b)` |
| `movdqa %1,%0; pmaxsd %2,%0` | `_mm_max_epi32(a, b)` |
| `maxps 16(%p,%i,4), %0` | `_mm_max_ps(v, _mm_loadu_ps(&p[i+4]))` |
| `phaddd %1,%1; pshufd $225,%1,%2; paddd %2,%1; movd %1,%0` | `_mm_hadd_epi32` + `_mm_shuffle_epi32(_MM_SHUFFLE(3,2,0,1))` + `_mm_cvtsi128_si32` |
| `movss %1,%0`（mem→xmm） | `_mm_set_ss(v)` |
| `cvtsi2ss %1,%0` | `_mm_cvtsi32_ss(_mm_setzero_ps(), i)` |
| `movsd %1,%0`（低 64bit 覆盖） | `_mm_or_si128(_mm_and_si128(A, _mm_set_epi32(-1,-1,0,0)), _mm_slli_si128(_mm_cvtsi32_si128(B), 4))` |
| `addss (mem), %0` | `_mm_add_ss(v, _mm_load_ss(&mem))` |
| `bsrq %k` + `cmovzl` | `63 - __builtin_clzll(k)`（先判 `k == 0`） |
| `__asm__(".align 16;")` | 直接删除 |

> 注意 GCC inline asm 的操作数编号：输入列表里的匹配约束（如 `"0"(x)`）也占一个编号，
> 因此 `: "=x"(A) : "0"(A), "x"(B), "x"(C)` 中 A/B/C 分别是 `%0/%1`、`%2`、`%3`。

## 证据（真实执行）

pftools 3.2.12（pftoolsV3，9 个内核文件 4586 行、35 种 `_mm_*`）：

- 未适配：`clang -c src/C/sse2/heuristic_sse2.c` →
  `emmintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"`（exit 1）；
  `pfProfile.h:17` 无条件 `#include <emmintrin.h>` 使**全部** C 程序不可编译；
- 引入垫片后 9 个内核全部编译通过，仅余 15 处内联汇编需改写；
- 最终 `conan create` exit 0；上游 CTest **6/6 通过**；`test_V3_output` 与上游 x86 参考输出
  **1959 行逐字节一致**（`diff` 退出码 0）；
- 附注：`mm_malloc.h` 也要进垫片目录并让构建系统把 `HAVE_MM_MALLOC_H` 置真，
  否则库自带的 `posix_memalign` 回退会与 sse2neon 的 `_mm_malloc/_mm_free` 重定义冲突。

## 推广价值

- 所有"纯 SSE intrinsic"科学计算/生物信息/编解码库向 aarch64 鸿蒙 PC 的适配；
- 把"重写 SIMD 内核"降级为"构建接线 + 少量 asm 改写"，风险与工作量差一个数量级；
- 反例提醒：若上游存在标量回退（`#ifdef` 分支），优先用官方开关关闭 SIMD，不引入转译层。

## 查重关键词

emmintrin.h、smmintrin.h、This header is only meant to be used on x86、sse2neon、
SSE→NEON、x86 内联汇编、xorps、maxps、pmaxsd、phaddd、bsrq、cpuid、aarch64 SIMD 回退、
非 x86 构建判定
