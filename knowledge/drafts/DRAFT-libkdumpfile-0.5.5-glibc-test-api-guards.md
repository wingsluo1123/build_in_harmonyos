# libkdumpfile 0.5.5 — glibc 专用测试 API 在 OHOS 缺失，需可移植守卫

## 问题

OHOS（musl 系 libc）上编译 libkdumpfile 上游测试源码时：

1. `src/kdumpfile/test-blob.c:68` 与 `src/kdumpfile/test-clone-attr.c:120` 的
   `mallopt(M_PERTURB, 1)` 报
   `use of undeclared identifier 'M_PERTURB'`（编译期）。
2. `tests/err-addrxlat.c:63` 的 `malloc_trim(0)` 报
   `undefined symbol: malloc_trim`（链接期，ld.lld 报错）。

## 根因

上游测试常用 glibc 特有内存调试手段：

- `mallopt(M_PERTURB, 1)`：设置 malloc 扰动字节（glibc 扩展参数）。
- `malloc_trim(0)`：归还堆顶空闲页（glibc 专有导出）。

OHOS 的 musl 系 libc 不定义 M_PERTURB 宏、不导出 malloc_trim 符号。直接删除会
丢失上游测试意图；盲目改写会改变测试语义。

## 方案

用守卫包裹调用点，保留上游意图且不改其他平台行为：

```c
/* test-blob.c / test-clone-attr.c */
#ifdef M_PERTURB                     /* 特性守卫：本平台 malloc.h 未定义则跳过 */
	mallopt(M_PERTURB, 1);
#endif

/* tests/err-addrxlat.c */
#ifdef __GLIBC__                     /* libc 识别守卫：OHOS 未定义 __GLIBC__ 则跳过 */
	malloc_trim(0);
#endif
```

守卫方式选择：M_PERTURB 用**特性守卫**（符号存在性）；malloc_trim 用 **libc 守卫**
（__GLIBC__，R8 例外口径为"识别 libc 的探针/守卫"，需在 notes/PR 说明理由，
不用 __OHOS__ 平台宏以避免 PF5 拦截）。

## 验证

- 修补前：`make check` 编译 test-blob.o/test-clone-attr.o 报 undeclared
  identifier，链接 err-addrxlat 报 undefined symbol，均 Error 1。
- 修补后：`make check` 中 47 个 addrxlat/addrmap 脚本测试与 4 个 kdumpfile
  单元测试（test-blob/test-clone-attr/test-cache/test-fcache）全部 PASS，0 FAIL。
- 该守卫在 glibc 环境不改变行为（宏/符号存在时照常执行）。

## 适用边界

- 适用于所有携带 glibc 风格测试源码（mallopt 扰动、malloc_trim、qsort_r 等
  glibc 专有 API）的三方库在 OHOS 上的 make check 适配。
- 仅修改测试文件，不影响库本体；守卫保持向上游可合并的移植性写法。
- 与 E531（glibc qsort_r 在 OHOS 不导出）同属"glibc 专有 API 在 musl 缺失"家族，
  但错误面为编译期宏缺失/链接符号缺失，方案为源码守卫而非替换实现。

## 查重差异

- E046（chmod 不生效）：平台行为差异，与本条目无等价。
- E531（qsort_r undefined reference）：同为 glibc 专有 API 在 OHOS 缺失，但
  符号不同（qsort_r vs M_PERTURB/malloc_trim）、错误面不同（库实现链接 vs
  测试源码编译/链接）、方案不同（替换实现 vs 守卫调用点），不构成等价命中。
- 快照中无 M_PERTURB / malloc_trim 的正式条目或草稿，属新增可复用经验。