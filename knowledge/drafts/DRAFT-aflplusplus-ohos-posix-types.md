# DRAFT-aflplusplus-ohos-posix-types：OHOS musl libc 不传递包含 POSIX 类型

## 现象

aflplusplus 4.33c `conan create` 首轮编译失败，核心工具 + LLVM 插桩全部卡在头文件编译：

```text
include/forkserver.h:191:3: error: unknown type name 'uid_t'
include/forkserver.h:193:3: error: unknown type name 'pid_t'
include/forkserver.h:197:3: error: unknown type name 'mode_t'
include/sharedmem.h:61:19: error: unknown type name 'mode_t'
```

## 根因

OHOS SDK 的 libc（musl）不像 glibc 那样通过 `<unistd.h>`/`<stdio.h>`/`<fcntl.h>`
等头文件**传递包含** `<sys/types.h>` 中的 POSIX 类型定义。上游代码在头文件里直接使用
`uid_t`/`pid_t`/`mode_t` 却只 include 自定义的 `"types.h"`（不含 sys/types.h），
依赖 glibc 的传递包含在 Linux 上侥幸编译通过；移植到 OHOS 后传递包含失效，类型未定义。

## 可复用修复模式

任何在头文件/源文件中使用 POSIX 标量类型（uid_t/pid_t/mode_t/gid_t/off_t/ssize_t）
但未显式 include `<sys/types.h>` 的 C/C++ 库，在 OHOS 上编译都可能报
`unknown type name 'xxx_t'`：

1. 定位报错头文件；
2. 检查是否已 `#include <sys/types.h>`；若否，在首次使用 POSIX 类型的 include
   块后补丁加一行 `#include <sys/types.h>`；
3. 用 `difflib.unified_diff` 生成最小 diff（单行增量，不整文件重写，遵循 R6）。

## 验证证据

- aflplusplus 4.33c（已合入）：`conan create` 首轮报上述错误 → 补丁 0001/0002
  各加一行 `#include <sys/types.h>` → 编译通过（5 核心工具 + afl-cc + LLVM pass），
  test_package 5/5，afl-cc 实机插桩 `Instrumented 1 locations`。
- afl++-tools 4.40c 适配亦采用同一修复（补丁 0001/0002 重打，见其适配记录），
  佐证该问题跨 AFL 版本存在（L1 平台真理倾向）。

