# SSE2-only Smith-Waterman 内核（ksw.c）无法在非 x86 编译：`<emmintrin.h>` 是 x86 专属头

- **草稿 ID**: DRAFT-trimadap-0.1-4-ksw-sse2-scalar-fallback
- **来源**: trimadap 0.1-4 HarmonyOS PC（aarch64-linux-ohos）适配；同源先例 `archives/f/fermi-lite/0.1/patches/0001-ksw.c.patch`
- **分类**: makefile / simd-x86-only / platform-branch / portability / aarch64
- **状态**: 本地草稿（随 trimadap 0.1-4 配方 PR 提交，路径 B 知识库扩展候选）

## 问题 / 错误签名

- **错误**：`ksw.c:29:10: fatal error: 'emmintrin.h' file not found`（OHOS 15.0.4 / clang 15，target `aarch64-unknown-linux-ohos`）。
- **平台相关性（关键）**：`ksw.c` 是"一条路径、一份实现"——文件顶部无条件 `#include <emmintrin.h>`，
  `struct _kswq_t` 的 `qp/H0/H1/E/Hmax` 直接声明成 `__m128i*`，`ksw_qinit`/`ksw_u8`/`ksw_i16` 全程 `_mm_*` intrinsics。
  `emmintrin.h` 只在 x86/x86-64 工具链中存在，因此 **x86 构建全绿、aarch64 必然失败**；
  即便头文件存在，aarch64 也没有 SSE2 指令可映射这些 intrinsic（不存在"加个 `-msse2`"的解法）。
- **次要同源坑**：`kthread.c` 只 include `<pthread.h>/<stdlib.h>/<limits.h>` 却使用 `int64_t`；
  glibc 会经 `<pthread.h>` 间接暴露该类型，OHOS 的 libc 不会 → `unknown type name 'int64_t'`。

## 根因

1. **上游只保留 SIMD 路径**：ksw.c（lh3 系，见 `fermi-lite`/`trimadap`；与 `bwa`/miniSSW 同源）未提供标量或 NEON 回退分支，
   也没有 `#if defined(__SSE2__)` 之类的能力守卫。上游自测与主要用户群在 x86，非 x86 缺口不会在上游 CI 暴露。
2. **布局与硬件强耦合，不能"删掉 SIMD 用普通 DP 顶上"就完事**：
   query profile 按条纹（striped）布局存放（`slen = ceil(qlen/p)`，`p = 16`（size=1）/`8`（size=2）），
   H 向量的相邻 lane 相差 `slen` 列，跨 lane 的 F（插入）项依赖 SWPS3 风格的 lazy-F 循环（最多 16 轮）补齐。
   等价改写必须同时更换布局（线性）与 F 传播方式（行内直接传播），否则结果会偏。
3. **饱和算术最易写错**：SSE2 版是"先 `_mm_adds_epu8(h, S)` 再单独 `_mm_subs_epu8(_, shift)`"两次饱和，
   合并成一次 `clamp(h + S - shift)` 仅在 `h + S ≤ 255` 时等价；i16 路径同理
   （`_mm_adds_epi16` + `_mm_subs_epu16`，后者是**无符号**饱和，与有符号 clamp 语义不同）。
4. **另一处易漏**：`ksw_align` 第二遍比对后会改写入参（上游 v 版用 `copy` 缓冲规避），
   标量移植时若沿用"直接翻转原缓冲"的老写法会破坏调用者数据。

## 判定方法（可复用）

```bash
# 1) 定位无守卫的 SIMD 依赖
grep -n "emmintrin\|xmmintrin\|__m128\|_mm_" *.c *.h | head -30
grep -c "if.*__SSE2__\|ifdef.*__SSE2__" *.c            # 0 → 无能力守卫，aarch64 必失败

# 2) 判定"任务真正会走到哪条内核"（决定标量回退要写几个函数）
#    trimadap 走 ksw_u8（xtra 含 KSW_XBYTE）；fermi-lite 只走 ksw_i16
grep -n "KSW_XBYTE\|ksw_align(" trimadap-mt.c

# 3) 找同源先例（省一整轮试错）
ls archives/*/*/patches/ | grep -i "ksw"
```

## 修复方案（已在 trimadap 0.1-4 实测）

1. `#if defined(__SSE2__)` 条件化 `#include <emmintrin.h>` 与 SIMD 结构体成员（`__m128i*` ↔ `void*`），
   并把整块 SIMD 实现（`ksw_qinit`/`ksw_u8`/`ksw_i16`）包进守卫 —— **x86 分支一字不改**。
2. `#else` 提供等价标量实现：线性 profile 布局、行内 F 传播；
   用 `KSW_ADDS_U8`/`KSW_SUBS_U8`/`KSW_ADDS_I16`/`KSW_SUBS_U16` 四个宏**逐步**复刻 SSE2 的饱和顺序。
3. 补齐非 glibc 缺失的头（`kthread.c` 加 `<stdint.h>`）。
4. 补丁不得引入 `__OHOS__`（R8 口径）：平台分支依据 ISA 能力宏 `__SSE2__`，对 x86 完全透明；
   禁止 `#ifdef __OHOS__ return 0;` 之类空壳（R40：功能静默丢失而测试全绿）。

## 验收判据

| 判据 | 方法 | trimadap 实测 |
|------|------|---------------|
| 补丁可干净应用 | `patch -p1 < patches/0001-ksw.c.patch` + 与工作区 `cmp` | MATCH |
| x86 路径未变 | 补丁内 SSE2 块为上下文行（未改动） | `+#if defined(__SSE2__)` ×3，无 SSE2 代码行被改 |
| 跨架构 oracle | 用上游生态已公布的期望值反查 | Homebrew `brew test trimadap` 断言第 4 个接头 `ATCTCGTATGCCGTCTTCTGCTTG` 命中数 = 1；aarch64 标量路径实测 **1** |
| 端到端行为 | 上游样本数据 + 构造型用例 | test.fa 6 条读段掩码边界与接头已知位置一致；`-t 8` 精确剪切为插入片段 |
| 线程一致性 | `-p 4` 与单线程 `cmp` | 逐字节一致 |
| 门禁 | W3 本地 CI（conan create + L0/L1/L2/L4/L5） | 全过（L4 warn：补丁含 memcpy 类函数） |

## 影响范围与不覆盖项

- **覆盖**：内嵌 lh3/SSW 系 SIMD 内核的 C/C++ 项目（fermi-lite、trimadap、bwa 早期版本、miniSSW 衍生），
  以及更一般地"上游只保留 x86 SIMD 分支、无标量/NEON 回退"的源码（自研 SSE2 点积、只写 `_mm_*` 的信号/图像处理）。
- **不覆盖**：上游已提供 NEON/标量分支但被构建开关误关（属"平台检测/开关"类问题）；
  用 `__builtin_ia32_*` 直写 intrinsic 或内联汇编的场景（需换架构特定实现，不是标量回退能解决）。

## 性能说明（须如实申报）

标量内核为逐单元 DP，无 SSE2 的 16/8 路并行，aarch64 单线程吞吐低于 x86；
同一输入的**结果**与 x86 oracle 一致，属预期性能差异而非功能差异，须在 notes.md / PR 中明示。

## 相关

- 先例配方：`archives/f/fermi-lite/0.1/patches/0001-ksw.c.patch`（同一份 ksw.c，同一策略）
- 本次配方：`archives/t/trimadap/0.1-4/patches/0001-ksw.c.patch`、`0002-kthread.c.patch`
