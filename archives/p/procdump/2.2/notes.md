# procdump 2.2 适配笔记

## 编译环境
- 构建系统: 上游手写 Makefile（无 configure），配方在 `build()` 内按上游规则逐步驱动
- 编译日期: 2026-10-05
- 编译器: clang/clang++ 15（OHOS NDK，profile `ohos-aarch64`，目标 `aarch64-linux-ohos`）
- 状态: built（本地 `conan create` 通过，含 test_package）

## 源码
- 上游: Sysinternals ProcDump for Linux（MIT），tag `2.2`，2023-09-07
- URL: https://github.com/microsoft/ProcDump-for-Linux/archive/refs/tags/2.2.tar.gz
  （`github.com/.../archive/refs/tags/2.2.tar.gz` 会 302 到 codeload，两种写法取到的字节完全相同）
- 实测：HTTP 200，6144581 字节
- sha256: `a8ac2e4db3f357c897adb8c11c2279853ebea0c766eb4cdc158e77ca11b77690`（conan 下载后校验一致）
- 顶层目录 `ProcDump-Linux-2.2`，`strip_root=True` 后正常

## 编译步骤（配方 build() 内自动执行）
1. 应用两个补丁（见「源码修改」）
2. **特性探针**：编译+链接一行 `return pthread_cancel(pthread_self());`
   - 成功 → 不加任何宏，上游调用点原样使用（glibc 目标）
   - 失败（本机 OHOS 即是）→ 加 `-DPROCDUMP_NO_PTHREAD_CANCEL`，启用 PthreadCompat 退路
3. 逐个编译 `src/*.c`（11 个），CCFLAGS = `-O2 -g -Wall -I ./include -pthread -std=gnu99
   -fstack-protector-all` + 探针宏
4. 编译 CLR profiler：`clang++ -shared --no-undefined -fms-extensions -std=c++11 …`
   `profiler/src/{ClassFactory,ProcDumpProfiler,dllmain,corprof_i}.cpp` + `easylogging++.cc`
   → `obj/ProcDumpProfiler.so`
5. 内嵌 profiler：生成 `obj/embed_profiler.S`（`.incbin "obj/ProcDumpProfiler.so"`，
   导出 `_binary_obj_ProcDumpProfiler_so_start/_end`）→ `clang -c -fPIC` → `obj/ProcDumpProfiler.o`
6. 链接 `bin/procdump`（11 个 .o + 内嵌 blob .o）
7. 顺带编译上游 `tests/integration/ProcDumpTestApplication.c`（上游 `make build` 也会编，
   集成测试的被监视负载生成器；**不打包**）
8. 打包 `bin/procdump` + `share/man/man1/procdump.1`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译报 `use of undeclared identifier 'pthread_cancel'`（GenHelpers.h / Monitor.c / CoreDumpWriter.c / ProcDumpProfiler.cpp） | OHOS musl libc 不实现 POSIX 线程取消：`<pthread.h>` 里连 `PTHREAD_CANCEL_*` 宏之外的一个声明都没有（musl 上游是有的，OHOS 这份头文件删掉了），`libc.a` 里有 `pthread_cancel.o` 但 `libc.so` **不导出**该符号 → 光看头文件会误判，真正卡住的是链接 | 配方加「编译+链接」探针（不是 grep 头文件、也不是平台宏），只有真链不上才定义 `PROCDUMP_NO_PTHREAD_CANCEL`；补丁提供 `PthreadCompat.h`（知识 E085/E320/E407 的既有口径） |
| 2 | 链接报 `undefined symbol: pthread_setcanceltype` | `WriteCoreDump()` 用它把写 dump 的临界区设成 deferred/async cancel；`CoreDumpWriter.c:113/143` | 同上，改为 `ProcdumpDeferThreadExit()` / `ProcdumpResumeThreadExit()`；在无取消 API 的目标上用 `pthread_sigmask` 只屏蔽调用线程的保留信号来等价表达 defer 语义（作用域与 `PTHREAD_CANCEL_DEFERRED` 一致，请求会挂起到恢复后投递） |
| 3 | 编译报 `'cleanup' function 'cancel_pthread' parameter has type 'unsigned long *' … incompatible with 'pthread_t *'` 与 `incompatible integer to pointer conversion initializing 'pthread_t' … with an expression of type 'int'` | OHOS musl 的 `pthread_t` 是 `struct __pthread *`（C 模式），上游假设 glibc 的 `unsigned long` | `cancel_pthread()` 形参改 `pthread_t *`；两处 `pthread_t x = -1` 哨兵改 `((pthread_t)-1)`（对整数型和指针型 pthread_t 都合法） |
| 4 | 上游 `Makefile` 的 `CCFLAGS` 带 `-fanalyzer -Werror` | `-fanalyzer` 是 GCC 专有（clang 报 unknown argument），`-Werror` 会把 2022 年源码里已有的 clang 诊断变成硬错误 | 配方自己拼 CCFLAGS，只保留其余上游开关 |
| 5 | **产物链接成功但真机/任何 musl 环境都加载不了**：`Error relocating …: __vsnprintf_chk: symbol not found`（同类共 11 个 `__*_chk`） | 上游 `-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=2` 让 clang 改调 glibc 的 FORTIFY 入口，musl 一个都没有。lld 在这条链路上没有拦住，留到了运行期 | 从 CCFLAGS 里去掉这两个开关（`-fstack-protector-all` 保留，musl 有 `__stack_chk_fail`）；并在 test_package 加断言 8 防止回归 |
| 6 | `ld -r -b binary -o obj/ProcDumpProfiler.o obj/ProcDumpProfiler.so` 不可用 | GNU ld 专有语法；本机 `ld` 不是 GNU ld，lld 还要求 `-m aarch64linux` 模拟名，而 CI worker 上是否有名为 `ld` 的 GNU 工具无法保证 | 改成生成 `.S` + `.incbin` 再用同一个 clang 编译，产生完全相同的 `_binary_<path>_{start,end}` 符号对，只依赖 C 编译器 |
| 7 | 无法「预置产物再 make」 | 上游 `$(OBJDIR): clean` / `$(BINDIR): clean` 让**每次** make 都先 `rm -rf obj bin`（clean 是 .PHONY），预置的 blob .o 会被删掉 | 因此配方不调 make，按上游同样的源文件集合与编译/链接顺序逐步执行 |
| 8 | `can_run()` 在 x86_64 主机上返回 True | conan 不认识 `os=OHOS` 这个枚举名，`can_run()` 判定「可运行」，test 于是真去 exec aarch64 ELF 并报 relocation 错误 | test_package 的 conanfile 额外用 `platform.machine()` 判定；不可运行时**显式声明延后**运行层断言，静态断言照跑 |

### pthread_cancel 缺失时的退路为什么这样做（不是空壳 stub）

被取消的线程都阻塞在取消点上：`SignalThread` 阻塞在 `sigwait()`，`SignalMonitoringThread`
阻塞在 `waitpid()`，`WaitForProfilerCompletion` 阻塞在 `accept()`，profiler 里的
`HealthThread` 阻塞在 `sleep()`。所以退路是「投递一个保留信号 → 处理器里 `pthread_exit(NULL)`」，
调用方随后照旧 `pthread_join()`：

- 保留信号用 `SIGUSR1`。proc_dump 只为 sigwait 屏蔽 `SIGINT`/`SIGTERM`
  （`ProcDumpConfiguration.c:60-63`），`SIGUSR1` 在所有工作线程里都是通的，不需要改屏蔽逻辑。
- 处理器 `sa_flags = 0`，**不能带 `SA_RESTART`**：带了就必须靠处理器自己 unwinding，
  不带则阻塞中的系统调用先返回 `EINTR`，处理器随即 `pthread_exit`，两条路都能退出。
- 绝不返回「成功」的假取消：那会让调用方以为线程已停而继续 join/释放资源（E320 forbid_1）。
- `PROCDUMP_INVALID_THREAD` 哨兵让清理函数在「线程从未创建」的早退路径上什么都不做。

## 源码修改
- `patches/0001-thread-cancel-compat-header.patch`
  - 新增 `include/PthreadCompat.h`：`PROCDUMP_NO_PTHREAD_CANCEL` 分支下的
    `ProcdumpCancelThread` / `ProcdumpInstallThreadExitHandler` / `ProcdumpDeferThreadExit` /
    `ProcdumpResumeThreadExit`，glibc 分支原样包 `pthread_cancel` / `pthread_setcanceltype`；
    以及对两种 `pthread_t` 都成立的 `PROCDUMP_INVALID_THREAD`
  - `include/Includes.h` 最前面 include 它
  - `include/GenHelpers.h`：`cancel_pthread(unsigned long*)` → `cancel_pthread(pthread_t*)`，
    `!= -1` → `!= PROCDUMP_INVALID_THREAD`，函数体走 `ProcdumpCancelThread`
- `patches/0002-route-cancellation-through-compat.patch`
  - `src/Monitor.c`：3 处 `pthread_cancel` → `ProcdumpCancelThread`；
    `waitForProfilerCompletion`/`processMonitor` 两处 `= -1` → `= PROCDUMP_INVALID_THREAD`
  - `src/CoreDumpWriter.c`：2 处 `pthread_setcanceltype(DEFERRED/ASYNCHRONOUS)` →
    `ProcdumpDeferThreadExit()` / `ProcdumpResumeThreadExit()`
  - `profiler/src/ProcDumpProfiler.cpp`：include PthreadCompat.h，
    `CleanupProfiler()` 里 `pthread_cancel` → `ProcdumpCancelThread`
- **补丁里没有平台宏**（PF5 合规）：唯一条件编译符号 `PROCDUMP_NO_PTHREAD_CANCEL`
  由配方的链接探针产生，且走的是有实质逻辑的分支，不是 `return 0` 空壳。
  glibc 目标上探针通过，补丁整体退化为「原样包一层函数」。

## 依赖版本
- 无第三方编译依赖。任务池原先标的 `zlib/1.3.2.1` **不需要**：`Procdump.h` /
  `ProcDumpConfiguration.h` 确实 `#include <zconf.h>`，但全仓库没有任何一处引用 zlib 符号
  （`z_stream`/`deflate`/`inflate`/`gz*`/`crc32`/`Z_*` 全部零命中），OHOS sysroot 自带
  `zconf.h`，因此不写成 Conan 依赖（写成依赖也只会白拉一个静态库）。
- 运行时只需要目标 libc（`readelf -d` 显示 `NEEDED` 只有 `libc.so`）。

## 上游测试（R51 三步法）
1. **清点**：`make test` → `tests/integration/run.sh` + `tests/integration/scenarios/*.sh`
   共 **40** 个场景脚本（proc 负载类 16 + `ondemand` 1 + `dotnet_*` 23）；另有
   `ProcDumpTestApplication.c`（负载生成器）、`tests/integration/signal/signaltest.c`、
   `tests/integration/TestWebApi/`（dotnet 场景的被监视 C# 工程）。
   注意上游**没有**单元测试框架，只有这一套 shell 集成测试。
2. **运行**：未在 OHOS 上跑通，逐项技术原因（不是「没环境」）：
   - `run.sh` 第一步 `rootcheck()`：非 root 会 `sudo` 重入，OHOS 无 sudo
   - `run.sh` 硬性要求 `/usr/bin/stress-ng`，缺失即 `exit 1`
   - 23 个 `dotnet_*` 场景要求目标进程是 CoreCLR 且开放 diagnostics 管道，OHOS 无 .NET 运行时
   - `-sig` 场景的 dump 走 `gcore`，OHOS 基础镜像无 `gcore`
   - 本地交叉编译主机是 x86_64 WSL，产物是 aarch64 ELF，无法执行上游测试
3. **回填**：消费者验证见 `test_package/test.sh`（静态 8 + 运行 4，共 12 断言）。
   运行层断言（`procdump -h` 输出 usage/options、退出码非信号终止）会在 aarch64/OHOS
   worker 上自动执行；本地 x86_64 主机按 `can_run()+platform.machine()` 显式判定为延后。

## 验证结果
- `conan create archives/p/procdump/2.2 -pr:h=ohos-aarch64-lkyz -pr:b=ohos-aarch64-lkyz --build=missing` → **rc=0**
- 探针输出：`probe: probe exited 1 -- target libc has no pthread_cancel(); enabling the PthreadCompat signal-based fallback`
- test_package：静态层 8 断言全过（安装布局 / ELF / man page / 内嵌 profiler blob 三处特征字符串 / 无 glibc FORTIFY 引用）
- 产物：`ELF 64-bit LSB pie executable, ARM aarch64`，interpreter `/lib/ld-linux-aarch64.so.1`，
  10249600 字节（其中 ~10 MB 是内嵌的 CLR profiler）
- 符号核验：动态未定义符号里**所有强引用（U）都能在 OHOS libc.so 里找到**；
  仅剩 3 个弱未定义 `__at_fini` / `__register_frame_info` / `__deregister_frame_info`
  （glibc 可选符号，弱引用解析为 0 不影响加载）
- 内嵌 profiler 已用内容校验：三处只存在于 `profiler/src/ProcDumpProfiler.cpp` 的字符串
  （`CorProfiler::CleanupProfiler: Enter`、`HealthThread: Procdump running`、
  `SendDumpCompletedStatus`）都能在可执行文件里 grep 到，且**不在**普通目标文件里

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/procdump` | 10249600 B | aarch64 ELF，动态链接 musl libc，内嵌 CLR profiler |
| `share/man/man1/procdump.1` | 2300 B | 上游 man page |

（`bin/ProcDumpTestApplication` 按上游 `make build` 一并编译，但不打包。）

## 注意事项
- 抓 dump 需要 `ptrace(PTRACE_SEIZE)` + 同 uid/root，真机上一般要 root；core dump 落盘
  还受 OHOS 自身策略与沙箱约束。上游 `-sig` 路径 dump 时会调 `gcore`，OHOS 基础镜像没有。
- `.NET` 相关触发（`-e`/`-gcm`/`-gcgen`）需要目标进程是 CoreCLR，OHOS 上无法验证；
  本次只保证 `.so` 能构建并被正确内嵌/可抽出。
- profiler 退路会在**目标 .NET 进程内**安装一个 `SIGUSR1` 处理器（`CleanupProfiler` 时用）。
  这是注入式 profiler 的固有代价，`PR#3482`（JACK）用的是同一套办法；已在
  `PthreadCompat.h` 与本文件里写明风险。
- `can_run()` 对 `os=OHOS` 不可靠（见上表 #8），任何新增的 aarch64 工具包 test_package
  都要照此加 `platform.machine()` 判定，否则本地会假失败。
- 二进制未 strip（上游 `-g` 且 CI 流水线负责签名/裁剪）。


## CI #85837 的真根因：`uname()` 内核门槛在 OHOS 上判不过，工具**在打印用法前就退出**

### 现象（诊断化之后的日志第一次把话说清）

```
== runtime layer
run: euid=20020101 rc=255 bytes=455 lines=11
  [FAIL] [7] prints the Capture Usage block   (pattern: Capture Usage 未命中)
  [FAIL] [8] prints the Options block
  [FAIL] [9] lists the -pgid switch
  [FAIL] [10] lists the -sig switch
--- procdump -? 的完整输出 ---
 ProcDump v2.2 …（banner 9 行）
 [10:08:46 - ERROR]: Cannot validate kernel version
 [10:08:46 - ERROR]: Kernel version lower than 3.5+.
```

在此之前 **7 个构建**（#83996 / #84412 / #84441 / #85201 / #85476 / #85645 / #85733）的日志
逐字一致，但只留下 `ConanException: Error 1`，**没有任何一行说明哪条断言红了** ——
旧 test.sh 是 `set -e` + 裸 `grep -q`，第一条不命中的 grep 直接静默退出，而 `head -5`
只显示 banner。诊断化之后一轮就把真话说出来了。

### 根因

`src/GenHelpers.c` 的 `CheckKernelVersion()`：

```c
if(sscanf(kernelInfo.release,"%d.%d",&version,&patch) != 2)
{ Log(error, "Cannot validate kernel version"); return false; }      /* ← OHOS 走这条 */
```

`src/ProcDumpConfiguration.c` 的 `InitProcDump()`：`if(CheckKernelVersion()==false){ Log(error,"Kernel version lower than 3.5+."); exit(-1); }`

OHOS worker 上 `uname(2)` 的 `sysname` 不是 `Linux`（见坑 T374：CI worker 的 `uname -s` 报
`HarmonyOS`），`release` 也不是 Linux 的 `major.minor` 形式 ⇒ `sscanf` 失败 ⇒
**`exit(-1)`(255)，永远走不到 `-h/-?` 的用法分支**。本地 WSL 的 `uname -r` 是
`6.18.33.2-…-WSL2`，能正常解析 ⇒ 本地全绿、CI 必红（典型「本地绿 CI 红」）。

### 处置：`patches/0003-ohos-kernel-version-gate.patch`

只在**解析失败且 sysname 明确是 HarmonyOS/OpenHarmony/OHOS** 时放宽（`Log(warn, …)` 后
`return true`），其余系统保持原严格判据 —— 用运行时字符串判定，不含平台宏：

```c
if(strstr(kernelInfo.sysname,"HarmonyOS")!=NULL || strstr(kernelInfo.sysname,"OpenHarmony")!=NULL
   || strstr(kernelInfo.sysname,"OHOS")!=NULL)
{ Log(warn, "uname release '%s' on %s is not a Linux version string; assuming kernel >= %d.%d", …); return true; }
```

门槛的**本意**是「拒绝 <3.5 的老内核」，而 HarmonyOS 内核是 Linux 5.10+；解析不出来
并不构成「内核古老」的证据，却让工具在 OHOS 上完全不可用。

### 本地 A/B（同一个 aarch64 产物，用 LD_PRELOAD 把 `uname()` 换成 HarmonyOS 版本）

| 组合 | 结果 |
|---|---|
| **未打补丁** + HarmonyOS uname | rc=255，输出 12 行，`Cannot validate kernel version` + `Kernel version lower than 3.5+.`，**用法块缺失** ← **与 CI #85837 完全一致** |
| **打补丁** + HarmonyOS uname | rc=255，输出 50 行，出现 `[WARN] uname release 'OHOS-6.0.0.0' on HarmonyOS is not a Linux version string; assuming kernel >= 3.5`，**用法块正常打印**，11/11 断言 PASS |
| **打补丁** + 真实 Linux uname | 48 行，用法块正常，11/11 PASS（无回归） |

`conan create`（profile `ohos-aarch64-lkyz`）：`Apply patch (portability): … kernel>=3.5 gate …` +
`Package folder …/p`，静态层 6/6 PASS。

### 顺带：test.sh 现在会把平台信息写进日志

```
platform: uname -a => Linux lkyz 6.18.33.2-…-WSL2 …
platform: /proc/version => Linux version 6.18.33.2-…
```

CI 上这一行会记录 worker 真实的 `uname`，以后同类「本地绿 CI 红」不必再猜。
（补丁不依赖 release 的具体取值：只在解析失败时生效；若 worker 的 sysname 不是
HarmonyOS 系，日志里的 `uname -a` 会直接暴露，下一轮据此收紧/放宽。）

---
**编译结束**: 2026-10-05
**最终状态**: built

## CI #91222 的排查：dump 类场景为何 14/21 失败（2026-10-14）

### 现象（先排掉一层假象）

1. 之前几轮 CI 的失败其实是**worker 进程数耗尽**：日志里十几行
   `test.sh: fork: (retry: )Resource temporarily unavailable`，脚本被 EAGAIN 打死，
   conan 只报 `Error 254`，连一条 `[FAIL]` 都没有 —— 与产物无关。
   已在 `test_package/test.sh` 开头加 fork 自检（`env: fork OK` / `env: ⚠ fork 受限`），
   并把产物路径推导改成不依赖 fork 的 bash 参数展开（原来 `$(dirname "$(dirname "$BIN")")`
   在 fork 受限时会塌成 `/share/man/man1/procdump.1`，把「man page 其实在包里」误报成缺失）。
2. 排掉这一层后（构建 #91222，fork OK），脚本真正跑到了上游场景层，结果：

```
[ohos-upstream] SUMMARY scenarios_total=40 executed=21 passed=7 failed=14 dotnet_blocked=19
```

- **7 个通过的全部是 `*_notdump` 场景**（high_cpu_notdump / high_fd_notdump / high_mem_notdump /
  high_tc_notdump / low_cpu_notdump / low_mem_notdump / high_cpu_nonexisting_output_directory）——
  它们断言「不该产生 dump」，所以不需要真正抓 dump。
- **14 个失败的全部是「应当产生 dump」的场景**，报错形态一致：
  `[ohos-validate] no dump but shouldDump=true -> FAIL`。

### 失败现场（每个失败场景的 tail 都是同一形态）

```
Process:                                ProcDumpTestApplication (15040)
CPU Threshold:                          >= 80%
Commit Threshold:                       n/a
/path/runProcDumpAndValidate.sh: line 89: 15075 Trace/breakpoint trap
[ohos-validate] no dump but shouldDump=true -> FAIL
```

即：procdump 打印完监视头（说明它认到了目标进程与阈值），随后**目标进程收到 SIGTRAP 被打死**，
30 秒窗口内没有任何 dump 落盘。

### 判据与上游实现对照

- 上游 `src/CoreDumpWriter.c:178` 生成 dump 的方式是 **外部程序**：
  `snprintf(command, ..., "gcore -o %s %d 2>&1", prefix, pid)` + `popen2()`；
  `gcore` 的每一行输出经 `ReadCoreDump()` 解析。
- 本包 `notes.md` 早已记录「OHOS 基础镜像无 `gcore`」（「上游测试」小节第 2 步第 4 条与
  「注意事项」），本机 WSL 有 `/usr/bin/gcore`、而 OHOS worker 没有。
- procdump 监视目标进程走 `ptrace(PTRACE_SEIZE)`（`src/Monitor.c:1055` 起），
  目标在 attach 时收到的就是 SIGTRAP —— 这正是日志里 `Trace/breakpoint trap` 的来源。

### 结论（本轮到此为止，不做未经验证的改动）

- 这两条（缺 `gcore`、attach 时目标被 SIGTRAP 打死）**都不是本 PR 引入的缺陷**，
  而是上游 dump 后端在 OHOS 上的适配缺口：上游把 dump 委托给 `gcore`，
  而 OHOS 既没有 `gcore`，ptrace attach 的信号语义也与 Linux 不同。
- 因此「14/21 失败」不应当被读成「配方坏了」，但它确实意味着：**本 PR 宣称的
  「21 个非 dotnet 场景在 OHOS 上真实执行」目前只能覆盖 7 个不需要抓 dump 的场景**。
- 可选的下一步（都需要单独决策，不在本轮擅自实施）：
  1. 在 OHOS 上实现一个不依赖 `gcore` 的 dump 后端（直接读 `/proc/<pid>/mem` 生成 ELF core，
     或改用 OHOS 自带的 coredump 机制）—— 改动量大，属于产品侧能力补齐；
  2. 把这 14 个场景按「环境能力缺失」如实标记为 SKIP 并计数（不减少断言、不伪造通过），
     同时把覆盖口径写进 PR 描述与 MANIFEST —— 需要评审认可这种口径；
  3. 维持现状，等平台侧提供 `gcore`/放开 ptrace。

---

## 上游测试执行层：平台能力探测（2026-10-16，MR 15275 / rule4）

针对裁决「编译状态字段缺失；上游有用例 40 个但一个也没测（0/40）…请解决后真实执行上游测试用例」，
本轮不再用「环境限制」这类说法概括，而是把**判定依据本身**做进执行层：跑场景前先探测平台能力、
把原始证据（errno / /proc 内容 / 命令路径）打进构建日志，再据探测结论逐类处置。

### 执行层新增的探测（`test_package/upstream_tests/capprobe.c` + `run_upstream_ohos.sh`）

| 探测项 | 方法 | 为什么这一项决定「能不能跑」 |
|--------|------|------------------------------|
| `euid` | `geteuid()` | 上游 `run.sh` 强制 root；本包 0004 patch 放宽为「同 uid ptrace」，故非 root 不阻塞，但如实记录 |
| `/proc/<pid>/cmdline` argv[0] | 读第一个 NUL 字段取基名 | **上游 `src/Process.c:527 GetProcessName()` 读的就是这里**，该名字进入转储文件名 |
| `/proc/<pid>/comm` | 读 comm | 与上一项对照用（翻译层下两者不一致） |
| `PTRACE_SEIZE` / `PTRACE_ATTACH` | 真实 `ptrace()` 调用，打印返回值与 errno | procdump 监视目标的手段（`src/Monitor.c`） |
| `/proc/<pid>/mem` | `open` + `pread` | 内存阈值判定与转储的数据来源 |
| `gcore` 是否存在 | `command -v gcore` | 上游 `src/CoreDumpWriter.c` 把转储**全部委托给外部 gcore** |
| 端到端转储探针 | 真实负载 + `procdump -n 1 -c 80`，看是否落盘 | 判定「后端真的可用」而不是「装了命令」 |

### 转储后端：判据已落到上游源码（不再是推测）

```
src/CoreDumpWriter.c:178   snprintf(command, BUFFER_LENGTH, "gcore -o %s %d 2>&1", gcorePrefixName, pid)
src/CoreDumpWriter.c:237   commandPipe = popen2(command, "r", &gcorePid);
src/CoreDumpWriter.c:282   Log(error, "\tDump exit status = %d", gcoreStatus);
```

即：**procdump 自己不产生 core，全部交给外部 `gcore`**。OHOS 基础镜像无 `gcore`/`gdb`，
因此任何 `shouldDump=true` 的场景都不可能在「产出转储」这一步成立 —— 这与 CI 日志里
`An error occurred while generating the core dump` / `Dump exit status = 1` 完全对得上。

### 场景分类改为**从场景源码读 `shouldDump`**（修掉一个少算）

原执行层用文件名猜（`*_notdump.sh` → 不需要转储），这会把
`high_cpu_nonexisting_output_directory.sh` 误判为「需要转储后端」而白白跳过 —— 它的
`shouldDump=false`（转储目录不存在 ⇒ 不应产出转储），断言根本不需要后端。
按文件名只跑 6 个，按源码判定是 **7 个**（本笔记上一节列的 7 个通过的场景里本来就含它）。
现改为逐场景 `grep '^[[:space:]]*shouldDump=false'` 判定，与上游校验器同源。

分类结果（实测，与上游 40 个 `.sh` 逐字节一致）：

| 类别 | 数量 | 断言 | OHOS worker 处置 |
|------|------|------|------------------|
| A `shouldDump=false` | 7 | 不应产生转储 | **真实执行**（不需要后端） |
| B `shouldDump=true` | 14 | 转储文件按预期出现 | 缺 `gcore` ⇒ 有据跳过，**不计入 passed** |
| C `dotnet_*` | 19 | 需 CoreCLR 诊断管道 | 如实阻塞计数 |
| **合计** | **40** | | |

### 架构翻译层护栏（`target_identity`）—— 本轮新增，理由是实测到的两种假象

本机 WSL 装了 `qemu-aarch64` 且 binfmt_misc 已注册（`flags: P`），OHOS aarch64 产物**能直接执行**，
于是一度看起来可以「在本机跑上游场景」。实测发现该环境**两个方向都会给出错误答案**，必须拒绝采信：

1. **假通过**：`gcore`(/usr/bin/gcore) 能 attach 到 qemu 进程并"成功"落盘，产物文件名却是
   **解释器名** —— `aarch64_binfmt_P_cpu_2026-10-16_13:42:44.1984`（`sanitize()` 把 `-` 换成 `_`）。
   原因是 `GetProcessName()` 读 `/proc/<pid>/cmdline` 的 argv[0]，而 binfmt 下 argv[0] 被内核
   换成了 `/usr/libexec/qemu-binfmt/aarch64-binfmt-P`。
2. **假失败**：那次"对解释器的转储"会落进场景的转储目录，于是 `shouldDump=false` 的场景被判
   `[ohos-validate] dump produced but shouldDump=false -> FAIL`（实测 `low_mem_notdump.sh`）。

本机 `capprobe` 原始输出（同一次运行）：

```
euid=0
target_cmdline_argv0=/usr/libexec/qemu-binfmt/aarch64-binfmt-P
target_argv0_basename=aarch64-binfmt-P
target_comm=capprobe
PTRACE_SEIZE=FAIL errno=38 (Function not implemented)
PTRACE_ATTACH=FAIL errno=38 (Function not implemented)
proc_pid_mem=OK errno=0 (-)
proc_pid_mem_pread=FAIL errno=5 (I/O error)
```

注意 `target_comm=capprobe` 看起来"正常"——**用 comm 判定会漏判**，必须按 upstream 同源的
cmdline argv[0] 判定（执行层里为此专门写了注释说明这一点）。

据此执行层的行为：`target_identity=translating` ⇒ 端到端转储探针不再执行（探了也无判定价值）、
需转储的场景不执行不申报、且**该环境下的 pass/fail 不作为构建门禁**（两个方向都不可归因）。
在真实 aarch64/OHOS 机器上 `target_identity=faithful`，行为与原来一致。

### 本机（翻译层环境）自测结果 —— 仅证明护栏有效，**不作为上游通过率**

```
[ohos-upstream] SUMMARY scenarios_total=40 executed=7 passed=6 failed=1
                skipped_no_dump_backend=14 dotnet_blocked=19
                dump_backend=absent gcore=present target_identity=translating
[ohos-upstream] failed_list: low_mem_notdump.sh          # 即上述「假失败」
```

**这组数字不能当作本包的上游通过率**：A 类里那 1 个 FAIL 是解释器被 gcore 转储所致，
真实 OHOS worker 上无 `gcore` 故不会发生。上游通过率以 CI（真实 OHOS worker）为准。
本机此轮的价值是：验证能力探测与护栏按预期工作，即**拒绝**在翻译层上产出通过结论。
