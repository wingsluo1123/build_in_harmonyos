# musl 下 fd_set / FD_SETSIZE / select 需显式 `#include <sys/select.h>`

> Draft: `E757-draft-A7F3`（uqm 0.8.0 适配实测）

## 错误特征

编译期集中报一组 select 相关的未定义（同一文件、一次性 18 个 error）：

```
src/libs/network/netmanager/ndindex.ci:25:38: error: use of undeclared identifier 'FD_SETSIZE'
src/libs/network/netmanager/netmanager_bsd.c:40:8: error: unknown type name 'fd_set'
src/libs/network/netmanager/netmanager_bsd.c:132:17: error: variable has incomplete type 'struct timeval'
src/libs/network/netmanager/netmanager_bsd.c:149:18: warning: call to undeclared function 'select';
      ISO C99 and later do not support implicit function declarations
src/libs/network/netmanager/netmanager_bsd.c:184:7: warning: call to undeclared function 'FD_ISSET';
```

`unknown type name 'fd_set'` + `use of undeclared identifier 'FD_SETSIZE'` 同时出现，
是"头文件缺失"而非"代码写错"的典型指纹。

## 触发条件

- 源码只包含 `<sys/types.h>` / `<sys/socket.h>` / `<unistd.h>`，未显式包含 `<sys/select.h>`
- 目标 libc 为 musl（OHOS SDK、Alpine）
- 阶段: compilation

## 根因分析

glibc 的 `<sys/types.h>`、`<sys/socket.h>` 等会把 `fd_set`、`FD_SETSIZE`
以及 `select()`/`FD_ISSET()` 声明**顺带**暴露出来，导致上游代码长期依赖这种
传递包含（uqm 0.8.0 `netmanager_bsd.c` 只 include 了 socket.h/assert.h/errno.h/
stdlib.h/string.h）。musl 严格按标准拆头文件：这些符号只存在于 `<sys/select.h>`。
于是同一份源码在 glibc 上静默通过、在 musl 上整文件报错。

## 解决方案

### 推荐方案

在缺少该头的源文件里显式包含（POSIX 标准头，glibc/BSD/macOS 同样存在）：

```diff
 #include <assert.h>
 #include <errno.h>
 #include <stdlib.h>
 #include <string.h>
+#include <sys/select.h>
```

uqm 实测只加这一行即消除全部 18 个 error。用 `refresh-patch --auto` 固化为补丁。

### 禁止做法

- ❌ 自行 `typedef ... fd_set` / `#define fd_set int` —— 与 libc 真实定义冲突，
  ABI 由 libc 决定，编译过不等于运行对
- ❌ 用 `-Dfd_set=int` 之类的命令行宏绕过

## 验证

```bash
# 最小复现：只有 sys/types.h 时 musl 是否可见 fd_set
printf '#include <sys/types.h>\nint main(void){fd_set s; FD_ZERO(&s); return 0;}\n' > $TMPDIR/t.c
clang -c $TMPDIR/t.c -o /dev/null && echo GLIBC_OK || echo MUSL_NEEDS_SYS_SELECT_H
# OHOS 期望输出: MUSL_NEEDS_SYS_SELECT_H
```

## 关联条目

- 相关: E194（musl `bits/alltypes.h` 缺头）、E208（musl sys/types.h 缺失路径）
- 取证: uqm 0.8.0 `archives/u/uqm/0.8.0/patches/0002-src-libs-network-netmanager-netmanager_bsd.c.patch`
