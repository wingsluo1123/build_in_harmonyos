# HarmonyOS 专项测试 — libtwirc 0.1.2

**this 工具备注**: `ohc-run.py pre-analysis` 使用旧路径约定
(`archives/l/libtwirc-0.1.2/src`), 与本仓库新布局 `archives/l/libtwirc/0.1.2/`
不匹配, 无法自动运行; 以下为等价手动平台专项扫描 (证据同源, 命令见下)。

## 平台相关扫描命令

```bash
cd $BUILD_SRC_DIR/src
grep -rnE '__GLIBC__|__linux__|#ifdef.*linux|#if.*linux|dlopen|dlsym|syscall|setreuid|chroot|fork\(|execv|system\(|popen' *.c *.h
grep -rhoE '#include <[a-z./]+>' *.c *.h | sort -u
```

## 结论

- 无 `__GLIBC__`/`__linux__` 平台宏条件编译, 无 dlopen/dlsym/syscall/setreuid/
  chroot/fork/system/popen 等平台敏感调用。
- 系统头文件仅 POSIX 通用集: errno/fcntl/netdb/signal/stdio/stdlib/string/
  sys/epoll/sys/socket/sys/types/time/unistd — 均由 OHOS libc 提供。
- 上游自述 Linux-only 并通过 epoll 实现 IO; OHOS 提供 sys/epoll.h, 探索编译
  (clang, os=OHOS) 与消费者冒烟均通过。
- 判定: 无平台适配障碍, 无需补丁。
