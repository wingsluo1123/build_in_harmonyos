# DRAFT — lockfree b08f761900 16 字节双字 CAS 的 aarch64 移植（asm → __int128 原子 + 16 字节对齐）

> 草稿（路径 B 知识候选），随 lockfree b08f761900 归档同 PR 交付。
> 关联 .kv: `DRAFT-lockfree-b08f761900-cas2-16byte-cas-aarch64.kv`
> 状态：两处补丁已实施（0001 CAS2 asm 替换 + 结构对齐、0002 TMPDIR），conan-verify G1-G4/L2/L4/L5 全过，W3 本地 CI 模拟 PASS。

## 问题

huangfcn/lockfree（C99 变体）的无锁队列/栈在 `lffifo.h` 中用 **x86 专属内联汇编**
实现 16 字节双字 CAS（指针 + ABA 计数器，`lock cmpxchg16b`，寄存器约束
`"=a"/"a"/"b"/"c"/"D"/"d"`）。在 aarch64（OHOS arm64，Clang 15）下：

1. **编译期**：`clang` 报 `error: invalid output constraint '=a' in asm` ——
   aarch64 没有 cmpxchg16b，x86 寄存器约束无效；
2. **运行期（修复 1 后仍会踩）**：换成可移植 `__atomic_compare_exchange_n` 作用在
   `__int128*` 上之后，若被 CAS 的结构体只有 8 字节对齐（`struct lf_pointer{node,aba_}`
   默认对齐 8），堆栈堆上地址 8 对齐但不 16 对齐时执行 16 字节原子访问 → **SIGBUS
   （Signal 7）**，测试进程直接崩溃。

## 根因

- 上游 2010s 库把 x86 平台的 cmpxchg16b 内联汇编直接写在头文件公共路径，没有
  aarch64 分支；`CAS2` 是 lffifo/lfstack 的 ABA 防伪核心，无法绕开。
- `__int128` 的 16 字节原子比较交换（GCC/Clang 内建）在 armv8 下降级为
  ldxp/stxp（或 ARMv8.1 LSE casp），**要求地址 16 字节对齐**；而原结构只声明了
  8 字节对齐，嵌入它的 `head_/tail_/freelist` 字段在典型栈/堆布局下往往只有
  8 对齐 → 运行期 SIGBUS。
- C++11 变体用 `std::atomic`（`magicq.hpp/rbq.hpp/lffifo.hpp`）实现同语义，
  std::atomic 自动处理对齐与内建 → 无此问题，印证了根因在裸内联汇编 + 对齐。

## 最小修复补丁（本库实施）

补丁 `patches/0001-C99-lffifo.h.patch`（两处一体，缺一处不可）：

```diff
--- a/C99/lffifo.h
+++ b/C99/lffifo.h
@@ static inline char CAS2(...)
-        void* v1 = (void*)(oldval[0]);
-        int64_t v2 = (int64_t)(oldval[1]);
-        ...
-        __asm__ __volatile__(
-            "lock cmpxchg16b (%1) \n\t"
-            "sete %0               \n\t"
-            :"=a" (ret)
-            : "D" (addr), "d" (v2), "a" (v1), "b" (n1), "c" (n2)
-        );
-        return ret;
+        __int128* p = (__int128*)(void*)addr;
+        __int128 ov = ((__int128)(uint64_t)oldval[0]) | ((__int128)(uint64_t)oldval[1] << 64);
+        __int128 nv = ((__int128)(uint64_t)newval[0]) | ((__int128)(uint64_t)newval[1] << 64);
+        return __atomic_compare_exchange_n(p, &ov, nv, 0, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST);
@@ struct lf_pointer
-    struct lf_pointer
+    struct __attribute__((aligned(16))) lf_pointer   /* 16-byte CAS 对齐要求 */
```

字节序与语义与 cmpxchg16b 完全一致（low=oldval[0]，high=oldval[1]；匹配
x86 的 RAX:RDX / RBX:RCX 布局）。

## 验证

```bash
# 修复前：编译期失败
conan create . -pr:h=ci/conan/profiles/ohos-aarch64
#   → error: invalid output constraint '=a' in asm (lffifo.h)

# 只修 asm 不修对齐：运行期 SIGBUS
./test_lockfree → Signal 7 (core dumped) @ lffifo_init 内 CAS2

# 修复后（本库实测）
conan-verify lockfree b08f761900
#   G1 配方完整性 PASS / G2 conan create + test_package PASS
#   （magicq/rbq/lffifo 真实 push/pop 12/12 断言 PASS）
#   G3 系统同名库隔离 PASS / G4 产物完整性 PASS / L2/L4/L5 PASS
finish lockfree b08f761900 built   # W3 本地 CI 模拟 PASS，.ci-result exit_code=0
```

## 适用边界

- **适用**：所有在 C/C++ 源码或头文件用 x86 cmpxchg16b（或
  `_InterlockedCompareExchange128`）实现 16 字节双字 CAS 的无锁库，移植到
  aarch64（OHOS / HarmonyOS PC 原生 arm64 / Linux ARM）；ABA 计数器 + 指针
  的 queue/stack/ring 结构。
- **反例/限制**：C++11 及以上用 `std::atomic` 的实现无需处理；纯 64 位 CAS
  （`__sync_bool_compare_and_swap` 单字）无 16 字节对齐问题；x86 目标继续用
  cmpxchg16b 也可，但统一换 __int128 内建更可移植（x86-64 亦支持）。
- 若结构体被嵌入数组/容器导致无法整体 16 对齐，需改用显式对齐分配或
  __int128 对齐包装，而非只改结构声明。

## 查重差异（vs E016 / E659）

- **E016**（"assembler error unknown instruction → reconfigure-no-asm"）：
  针对独立 .S/汇编文件的目标不支持指令，方案是整体禁用汇编；本条目是
  **C 内联汇编 + 寄存器约束**的编译期报错与**可移植原子内建替换**，并新增
  **16 字节对齐导致的运行期 SIGBUS** 维度——E016 未覆盖。
- **E659 草稿**（quickfix AtomicCount x86 `lock xadd` → `__atomic_fetch_add`）：
  同为"x86 内联汇编 → 原子内建"家族，但只覆盖**单字 fetch-add**；本条目覆盖
  **16 字节双字 CAS**（cmpxchg16b → __int128 compare_exchange）并补充
  **对齐 SIGBUS** 陷阱与结构对齐修复，属组合新颖。