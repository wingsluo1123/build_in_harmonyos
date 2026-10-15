# DRAFT-9009-ohos-musl-missing-glibc-feature-macros

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-9009-ohos-musl-missing-glibc-feature-macros.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-9009: OHOS musl 缺少 glibc 特性宏导致上游 `#error`（__USE_GNU / _GNU_SOURCE 一族）

- 条目主题：上游用 glibc 特性宏做条件编译（`__USE_GNU` 等）时，HarmonyOS 的 musl 不定义它们，
  典型形态是 `#error "GNU EXTENSION not activated."`；处置是选官方构型开关或打补丁，
  不要试图"造"宏。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxxx）
- 关联 PR：feat/pftools-3.2.12

## 现象

```console
src/C/utils/system.c:14:3: error: "GNU EXTENSION not activated."
# error "GNU EXTENSION not activated."
```

```c
#define _GNU_SOURCE          /* 上游自己定义了 */
#include "config.h"
#include "system.h"
#ifdef USE_AFFINITY
#ifndef __USE_GNU
# error "GNU EXTENSION not activated."
#endif
#endif
```

- `__USE_GNU` 由 **glibc 的 `<features.h>`** 在 `_GNU_SOURCE` 下定义；
- **musl 的 `features.h` 不定义它**（musl 没有这套 `__USE_*` 开关）。实测探针：
  `printf '#define _GNU_SOURCE\n#include <features.h>\n#ifdef __USE_GNU\n#error X\n#endif\n' | clang -E -`
  → 不触发 `#error X`。

## 判定流程

1. 查上游是否提供**关闭该特性的官方开关**（亲和性/`*_S` 接口/`ucontext` 兼容层等）——优先用开关。
2. 无开关且非核心功能不可关 → 打补丁放宽自检或降级实现（注意平台宏口径，见 R8）。
3. **不要**定义 `__USE_GNU`、也不要替换 musl 的 `features.h`（它是所有系统头的入口，污染不可控）。

## 本次处置（pftools 3.2.12）

- 触发点：`src/C/utils/system.c` 在 `USE_AFFINITY` 下要求 `__USE_GNU`；
- 处置：**不补丁**，改用上游 `INSTALL` 记载的官方构型 `-DUSE_AFFINITY=OFF`
  （"Build without affinity (old machines)"；ChangeLog v3.2.11 "Fix compilation with affinity off"）；
- 影响：不再做 NUMA/线程绑核，功能与测试结果不受影响（CTest 6/6；`test_V3_output` 与 x86 参考逐字节一致）。

## 排查提示

- 同一份代码在 glibc 上通过、在 musl 上 `#error`；
- **不要误判为工具链太旧**：`clang --version` 正常、`<sched.h>` 的 `CPU_SET_S` 也能编译，
  只有 `__USE_GNU` 不存在；
- 同族宏：`__USE_XOPEN2K8` / `__USE_MISC` / `__USE_POSIX199309`，判定与处置相同。

## 证据（真实执行）

- 未加 `-DUSE_AFFINITY=OFF`：`system.c:14:3: error: "GNU EXTENSION not activated."`；
- 加 `-DUSE_AFFINITY=OFF`：`make` exit 0，21 个可执行文件，上游 CTest **6/6 通过**。

## 推广价值

- 所有依赖 glibc 特性宏的库向 HarmonyOS（musl）移植：亲和性、`getopt_long`、`strverscmp`、
  `execinfo`、`open_memstream`、`struct ucontext` 兼容层等。

## 查重关键词

__USE_GNU、GNU EXTENSION not activated、musl features.h、glibc 特性宏、
_GNU_SOURCE 无效、USE_AFFINITY=OFF、CPU_SET_S、#error、libc 差异、HarmonyOS musl
