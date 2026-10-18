# E550 — 遗留 Makefile 探测 /usr/include 而非 sysroot，OHOS 下误判 syscall 头文件缺失

## 错误特征

编译日志出现（来自上游自带的 syscall 编号 shim）：

```
pommed/evdev.c:38:10: fatal error: 'inotify-syscalls.h' file not found
inotify-syscalls.h:NN:2: error: "inotify not supported on this architecture!"
timerfd-syscalls.h:NN:2: error: Unsupported architecture
```

## 触发条件

- 构建系统: 纯 Makefile（手工 `test -e` 探测）
- 阶段: compilation
- 平台: OHOS（sysroot 化）/ 任何交叉编译环境

## 根因分析

老式 Makefile 用**构建机绝对路径**判断平台能力：

```make
INOTIFY_CFLAGS = $(shell test -e /usr/include/sys/inotify.h || echo -DNO_SYS_INOTIFY_H)
TIMERFD_CFLAGS = $(shell test -e /usr/include/sys/timerfd.h || echo -DNO_SYS_TIMERFD_H)
```

OHOS 的工具链头文件在 sysroot（`<sdk>/native/sysroot/usr/include`）里，
`/usr/include` 下并不存在这两个头文件，于是 make 误判"平台不支持"，
加上 `-DNO_SYS_*`。源码随即改为 include 上游自带的 syscall 编号 shim
（`inotify-syscalls.h` / `timerfd-syscalls.h`），而这些 shim 只列举了
x86/ppc/ia64/s390/alpha/sparc/arm/sh/hppa/mips 分支，aarch64 落到 `#else` → `#error`。

## 解决方案

### 推荐方案

不改 Makefile，用**命令行变量覆盖**（GNU make 命令行赋值优先于 makefile 内部赋值）：

```bash
make -j1 -C <dir> INOTIFY_CFLAGS= TIMERFD_CFLAGS=
```

变量被清空后，源码头文件解析走真实 sysroot，`<sys/inotify.h>` /
`<sys/timerfd.h>` 正常可用。

### 备选方案

若探测结果参与条件分支，则 patch Makefile，用编译器自身能力探测：

```make
INOTIFY_CFLAGS = $(shell $(CC) -E - </dev/null -include sys/inotify.h >/dev/null 2>&1 || echo -DNO_SYS_INOTIFY_H)
```

### 禁止做法

- ❌ 往构建机 `/usr/include/sys/` 里拷贝头文件——污染共享文件系统，CI 干净 worker 上不存在，本地绿 / CI 红。
- ❌ 主动 `-DNO_SYS_INOTIFY_H` / `-DNO_SYS_TIMERFD_H`——正好是错误方向，会强制走 aarch64 不支持的 shim。

## 验证

```bash
test -e /usr/include/sys/inotify.h; echo "host has it: $?"
ls <sysroot>/usr/include/sys/{inotify,timerfd}.h
make -j1 -C pommed INOTIFY_CFLAGS= TIMERFD_CFLAGS=   # 应编译通过
```

## 关联条目

- 相关: E551（同为"平台能力判断错误"类）
