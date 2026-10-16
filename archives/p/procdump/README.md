# ProcDump for Linux 2.2（OpenHarmony PC / arm64）

Sysinternals ProcDump 的 Linux 实现：监视目标进程，在 CPU 占用、内存提交量、线程数、
文件句柄数、特定信号、.NET GC 堆增长或 .NET 未处理异常等触发条件命中时写出 core dump。
上游同时支持 .NET CoreCLR 场景：程序把一个自带的 CLR profiler（`ProcDumpProfiler.so`）
以原始字节**内嵌在自己的可执行文件里**，运行时再写回磁盘并注入目标 .NET 进程。

## 功能概述

| 触发条件 | 开关 |
|---|---|
| CPU 占用高于/低于阈值 | `-c` / `-cl` |
| 内存提交量（MB）高于/低于阈值 | `-m` / `-ml` |
| 线程数阈值 | `-tc` |
| 文件句柄数阈值 | `-fc` |
| 指定信号（ptrace 拦截后 detach→dump→转发） | `-sig` |
| .NET GC 内存 / 指定代 / LOH / POH | `-gcm` / `-gcgen` |
| .NET 未处理异常（可按异常名/消息通配过滤） | `-e` / `-f` |
| 手动（单次转储） | `ondemand`（不给阈值即按需） |

其他常用项：`-n` 抓几次、`-s` 抓取间隔秒、`-pf` 轮询频率、`-o` 覆盖已有文件、
`-w` 等待进程启动、`-pgid` 按进程组、`-log` 打开 syslog 详细追踪。

## OHOS 适配要点

1. **目标 libc 没有 POSIX 线程取消。** OpenHarmony 的 musl libc 既不在 `<pthread.h>`
   声明 `pthread_cancel`/`pthread_setcanceltype`，`libc.so` 也不导出它们，上游 5 处调用
   直接是 undefined symbol。配方在 `build()` 里做**编译+链接探针**，只有确认缺失时才
   定义 `PROCDUMP_NO_PTHREAD_CANCEL`，由 `include/PthreadCompat.h`（补丁新增）切换到
   `sigaction(SIGUSR1)` + `pthread_kill()` + 处理器内 `pthread_exit()` 的退路；
   处理器用 `sa_flags=0`（不带 `SA_RESTART`）以便把阻塞在 `waitpid`/`accept`/`sleep`
   的线程唤醒，`PTHREAD_CANCEL_DEFERRED` 的语义则用 `pthread_sigmask` 只屏蔽调用线程
   来等价表达。glibc 目标上探针通过，源码与上游行为完全一致。
2. **`pthread_t` 在 musl 下是 `struct __pthread *`。** 上游的 `pthread_t x = -1` 与
   `static inline void cancel_pthread(unsigned long *)` 两处都类型不匹配；补丁改用
   `((pthread_t)-1)` 哨兵和 `pthread_t *` 形参，同时兼容两种 pthread_t。
3. **内嵌 profiler 的链接方式。** 上游用 GNU ld 专有的 `ld -r -b binary` 把
   `ProcDumpProfiler.so` 转成目标文件；配方改为生成一段 `.S`（`.incbin`）再用同一个
   clang 编译，产生完全相同的 `_binary_obj_ProcDumpProfiler_so_{start,end}` 符号对。
4. **没有 zlib 依赖。** 源码 include 了 `<zconf.h>`，但从未引用任何 zlib 符号
   （上游历史遗留），OHOS sysroot 自带该头文件，因此不写成 Conan 依赖。
5. **保留上游的告警但不加 `-Werror`。** 上游 `CCFLAGS` 带 GCC 专有的 `-fanalyzer`，
   clang 会直接报 unknown argument；连同 `-Werror` 一起在配方里替换。

## 已知限制

- 抓 dump 依赖 `ptrace(PTRACE_SEIZE)` 与「同 uid 或 root」。真机上通常需要 root，
  且 core dump 的落盘路径受 OHOS 自身策略与沙箱约束。
- `.NET` 相关触发（`-e`/`-gcm`/`-gcgen`）要求目标进程是 CoreCLR 且已开放诊断管道；
  OHOS 上没有 .NET 运行时，这些路径无法在真机验证。
- 上游集成测试（40 个场景）强制 root、要求 `/usr/bin/stress-ng`，dotnet 场景还需
  .NET 运行时；本次未在 OHOS 上跑通，见 `2.2/notes.md` 的「上游测试」一节。

## 依赖关系

- 编译期第三方依赖：无（只依赖 libc/pthreads）。
- 运行时：目标 libc（musl）+ `gcore`（`-sig` 路径在 dump 时调用，上游用 `gcore` 生成
  core 文件）。

## 参考资料

- 上游仓库：https://github.com/microsoft/ProcDump-for-Linux
- 上游 2.2 tag：https://github.com/microsoft/ProcDump-for-Linux/releases/tag/2.2
- 官方文档（Windows 版）：https://learn.microsoft.com/sysinternals/downloads/procdump