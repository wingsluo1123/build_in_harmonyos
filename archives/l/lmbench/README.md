# lmbench

lmbench 3.0-a9 —— Larry McVoy / Carl Staelin 的系统微基准套件：一组独立的 C 基准程序，
测量操作系统延迟与带宽工作面，覆盖系统调用、上下文切换、管道、进程创建、信号处理、
内存/缓存访问延迟，以及管道、TCP、UDP、Unix socket、文件、内存映射带宽。

## 功能概述

- **延迟类（lat_*）**：syscall（null/read/write/stat/fstat/open）、ctx（进程上下文切换）、
  pipe、fifo、unix socket、tcp/udp、connect、select、signal、sem（信号量）、
  pagefault、mmap、proc（fork/exec/shell）、fs、mem_rd、dram_page、rand、usleep、
  pmake、cmd、http
- **带宽类（bw_*）**：pipe、tcp、udp、unix、mem（rd/wr/rdwr/copy/bcopy/frd/fwr）、
  mmap_rd、file_rd
- **整机类**：mhz（CPU 主频）、memsize（内存大小）、lmdd（磁盘读写吞吐，dd 风格）、
  cache/tlb/par_mem/par_ops/stream/line（缓存与内存并行性）
- **标定三件套**：enough / timing_o / loop_o —— 生成 `ENOUGH` / `TIMING_O` / `LOOP_O`
  三个环境变量（上游 `scripts/config-run` 的官方标定机制）

共 49 个可执行文件，全部安装到包的 `bin/`。

## 使用方法（OHOS）

每个基准程序独立运行，输出到 stdout/stderr，例如：

```sh
$PREFIX/bin/lat_syscall null      # 空系统调用延迟（微秒）
$PREFIX/bin/lat_pipe              # 管道延迟
$PREFIX/bin/bw_pipe               # 管道带宽（MB/sec）
$PREFIX/bin/lat_ctx -s 0 2        # 2 进程上下文切换延迟
$PREFIX/bin/lat_proc fork         # fork+exit 延迟
$PREFIX/bin/lat_mem_rd 16 0.5     # 内存访问延迟 vs 工作集（示例参数，耗时较长）
```

**先标定再测量**（推荐，与上游套件流程一致）：

```sh
ENOUGH=$($PREFIX/bin/enough)      # 本机合适的测量时间窗（微秒）
TIMING_O=$($PREFIX/bin/timing_o)  # gettimeofday 单次开销
LOOP_O=$($PREFIX/bin/loop_o)      # 基准循环单次开销
export ENOUGH TIMING_O LOOP_O
$PREFIX/bin/lat_pipe              # 之后运行的基准使用这些标定值
```

说明：不导出标定时，每个程序启动时自行自适应标定（上游默认行为）。标定算法按
±2% 窗口收敛，**对机器负载敏感**：共享/高负载机器上应使用上述显式标定值，
否则程序可能在标定阶段长时间运行（非缺陷，是 lmbench 1990 年代设计的固有特性）。

## OHOS 适配要点（aarch64 / HarmonyOS PC）

- **构建**：上游 `scripts/build` 驱动（`make OS=aarch64-ohos CC=<clang> AR=llvm-ar`），
  编译器取自 Conan conf（R33）。OS 标签不可依赖 `config.guess`
  （`scripts/gnu-os` 在 OHOS 无法运行），必须显式传 `aarch64-ohos`。
- **5 个 portability 补丁**（无 `__OHOS__` 平台宏注入）：
  1. `0001-scripts-build.patch`：特性探测临时目录基址优先 `$TMPDIR`
     （OHOS `/tmp` 只读，原代码探针全部静默失败）。
  2. `0002-src-bench.h.patch`：Sun RPC 头 include 加 `HAVE_pmap_clnt_h` 保护；
     未定义时补 `TRUE/FALSE`（原由 `rpc/types.h` 提供）。
  3-5. `0003/0004/0005`：`lat_rpc.c` / `lib_tcp.c` / `lib_udp.c` ——
     musl/OHOS 无 Sun RPC，用上游既有 `HAVE_pmap_clnt_h` / `NO_PORTMAPPER`
     宏补齐保护；`lat_rpc` 保留为明确报错的诊断入口。
- **包布局 = 上游 install 目标**：`bin/`（49 基准）、`include/`（10 头文件）、
  `lib/libmbench.a`。上游的交互式套件驱动（`scripts/config-run`、`scripts/results`）
  不在 install 目标内，本包同样不分发；基准程序独立运行。

### 已知平台差异（与 Linux 对比）

| 现象 | 根因 | 影响 |
|------|------|------|
| `lat_rpc` 报 “Sun RPC is not available on this platform” 并以非 0 退出 | musl/OHOS 不提供 Sun RPC（`rpc/rpc.h` 缺失） | RPC 事务延迟项不可用；TCP/UDP/Unix socket 延迟与带宽项不受影响 |
| 高负载机器上基准程序标定耗时显著变长 | lmbench 自适应标定（`find_N` ±2% 窗口）对测量噪声敏感 | 使用上述 `ENOUGH`/`TIMING_O`/`LOOP_O` 显式标定规避（官方机制） |
| `lat_unix_connect -s` 无法运行（`connect: No such file or directory`） | 该程序服务端使用**文件系统命名** AF_UNIX socket（上游硬编码 `/tmp/af_unix`）；OHOS 平台禁止在文件系统创建 AF_UNIX socket（实测所有可写目录 `bind` 均 EPERM，抽象 socket 可用） | 仅该命名 socket 基准不可用（平台能力限制，上游行为未改动）；`lat_unix`/`bw_unix` 使用 `socketpair`，正常可用 |

## 依赖关系

- **运行依赖**：无第三方库（libc + libm）。
- **构建依赖**：make + OHOS SDK clang/llvm-ar（Conan profile 提供）。

## 许可证

上游 `COPYING` 为 **GNU GPL v2**；`COPYING-2` 在 GPL 之上附加了结果发布限制
（lmbench 原始发行条款）。两文件均随包分发于 `licenses/`。

## 参考资料

- 上游项目：https://sourceforge.net/projects/lmbench/
- 适配归档：`archives/l/lmbench/3.0-a9/`（含 `reports/test-report.md` 真机证据）
