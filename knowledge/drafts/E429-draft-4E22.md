# E429 — musl 缺 glibc 专有类型与函数时的垫片方案

## 错误特征

从 glibc 迁到 musl 时，同一轮构建会连续报出这类错误（pesign 116 实测）：

```
include/libdpe/libdpe.h:69:8: error: unknown type name 'loff_t'; did you mean 'off_t'?
src/cms_common.c:565:4: error: use of undeclared identifier 'error_t'
src/list.h:759:2: warning: call to undeclared function 'qsort_r'
src/password.c:70:10: warning: call to undeclared function 'secure_getenv'
src/password.c:70:8: error: incompatible integer to pointer conversion assigning to 'char *' from 'int'
src/file_pe.c:309:5: error: use of undeclared identifier 'program_invocation_short_name'
（链接期）ld.lld: error: undefined symbol: secure_getenv
（若自行 typedef）…/bits/alltypes.h:15:18: error: typedef redefinition with different types
```

## 触发条件

- 构建系统: 任意（autotools / 手写 Makefile / CMake 都会遇到）
- 阶段: **compilation** 为主，未声明的函数会在 **linking** 阶段以 `undefined symbol` 再次爆发
- 环境: OHOS / musl（本仓库）；本质是"上游按 glibc 扩展写代码"

## 根因分析

- `loff_t` 是内核/glibc 里的类型；musl 只在 `bits/alltypes.h` 中按 `__NEED_*` 机制条件定义，
  而且该头经常没被上游文件包含。
- `error_t` 在 glibc 里由 `<errno.h>` 无条件提供；**musl 根本没有这个类型**。
- `secure_getenv`、`program_invocation_short_name/name` 是 glibc 扩展；musl 侧**连实现都没有**。
- `qsort_r` 在 musl 里通常需要 `_GNU_SOURCE` 才声明。
- **clang 15 在 C99 下把"隐式声明函数 + 返回值赋给指针"判为硬错误**（`-Wint-conversion`），
  所以这些不能靠 `-Wno-error` 糊过去。

## 解决方案

### 推荐方案：垫片头 + 垫片对象

1. 在源码树里生成 `conan_musl_shim.h`，放到**已经在 `-I` 路径上**的目录（例如 `<source>/include/`，
   上游编译命令里就有 `-I<source>/include`），内容：

```c
#ifndef __OHOS_MUSL_SHIM_H__
#define __OHOS_MUSL_SHIM_H__
#include <stddef.h>
#include <sys/types.h>
#ifndef __OHOS_ERROR_T_DEFINED__
#define __OHOS_ERROR_T_DEFINED__
typedef int error_t;                       /* musl 无 error_t（glibc 在 <errno.h>） */
#endif
#ifndef __DEFINED_loff_t                   /* 用 musl 自己的守卫宏，避免与 bits/alltypes.h 撞 */
#define __DEFINED_loff_t
typedef off_t loff_t;
#endif
extern void qsort_r(void *base, size_t nmemb, size_t size,
                    int (*compar)(const void *, const void *, void *), void *arg);
extern char *secure_getenv(const char *name);
extern char *program_invocation_short_name;
extern char *program_invocation_name;
#endif
```

2. 再由构建文件引入（**用相对名字**，因为该目录已在 `-I` 上）：在真进了编译命令的那个变量里追加
   `-include conan_musl_shim.h`（实测手写 Makefile 里 `CFLAGS` 会进命令、`ARCH_CFLAGS` 不会）。

3. 光有声明不够 —— 缺失的**实现**用一个 `.c` 补齐并编成 `.o` 交给链接：

```c
#include <stdlib.h>
char *secure_getenv(const char *name) { return getenv(name); }   /* musl 无此扩展 */
__attribute__((weak)) char *program_invocation_short_name = "prog";
__attribute__((weak)) char *program_invocation_name = "prog";
```

   `weak` 定义的意义：libc 若有**强定义**会被优先采用，两边都不冲突。

### 禁止做法

- ❌ 直接 `typedef int error_t;` / `typedef off_t loff_t;` 而不加守卫 —— 会与 musl 的
  `bits/alltypes.h` 撞成 `typedef redefinition with different types`（实测如此）。
- ❌ 用 `-Wno-error` 把"隐式声明 + int→指针"放过 —— clang 15 下那是**错误**不是警告，
  且问题会推迟到链接期以 `undefined symbol` 形式爆发。

## 验证

```bash
grep -rn "loff_t\|error_t\|qsort_r\|secure_getenv\|program_invocation" <源码树> | head
# 修好后：编译期不再报 undeclared / unknown type name；链接期不再报 undefined symbol
```

## 关联条目

- 相关：同类"换 libc 的成体系补齐"思路也适用于 `reallocarray`（musl 不声明 → 换等价 `realloc`）、
  `__ALIGN` 之类的宏重定义（musl 头里已有同名宏 → 先 `#undef`）。pesign 116 一轮里把这几类一并处理，
  细节见该版本 `notes.md` 与 `manifest.yaml` 的 `deviations`。
