# E552 — musl libc 不传递包含 pthread 类型与 PATH_MAX

## 错误特征

```
pommed/beep.h:49:3: error: unknown type name 'pthread_mutex_t'
pommed/beep.h:50:3: error: unknown type name 'pthread_cond_t'
pommed/beep.h:51:3: error: unknown type name 'pthread_t'
pommed/mactel/ambient.c:93:20: error: use of undeclared identifier 'PATH_MAX'
```

## 触发条件

- 构建系统: 任意
- 阶段: compilation
- 代码: 2010 年前后、依赖 glibc 隐式包含习惯的 C 代码

## 根因分析

glibc 的部分头文件（`<sys/types.h>`、`<unistd.h>`、`<syslog.h>` 的某些组合）
会**顺带**引入 `<pthread.h>` 的类型定义与 `<limits.h>` 的 `PATH_MAX`；
musl（OHOS 使用的 C 库）严格按 POSIX 拆分头文件，**不做**这种传递包含。
于是"只在 `.h` 里用了 `pthread_mutex_t` 却没 include `<pthread.h>`"、
"用了 `PATH_MAX` 却没 include `<limits.h>`"的旧代码，
在 glibc 上编译正常、在 OHOS 上直接报 `unknown type name`。

## 解决方案

### 推荐方案

在缺头文件的文件里补上显式 include（最干净的可移植性修复，glibc 上重复 include 有保护宏）：

```c
/* beep.h，include guard 内 */
#include <pthread.h>

/* mactel/ambient.c，include 区 */
#include <limits.h>
```

### 备选方案

不便改源码时可用编译期强包含：`CPPFLAGS="-include pthread.h -include limits.h"`。

### 禁止做法

- ❌ `#include <bits/pthreadtypes.h>` / `<bits/local_lim.h>`——glibc 内部头文件，musl 无此路径，属未定义接口。
- ❌ 手写 `#define PATH_MAX 4096`——掩盖真实缺失，数值可能与平台不符。

## 验证

```bash
grep -n '#include <pthread.h>' pommed/beep.h
grep -n '#include <limits.h>'  pommed/mactel/ambient.c
make -j1            # 应无 unknown type name / undeclared identifier
```

## 关联条目

- 相关: E550
