# ply-probe 2.4.0 适配笔记

> **本任务为「知识库扩展」任务**：以 ply-probe 2.4.0 为载体，补齐 SKILL 对
> **"Linux 内核追踪特性（eBPF / kprobe / perf_event / tracefs）"** 这一平台共性缺口的检测与记录能力。
> 知识条目草稿：`knowledge/drafts/E545-draft-44F3.kv`（含 `prescan_pattern`，PreScanner 运行时自动派生
> `PSCAN-KB-E545` 规则，**无需改框架文件**）；复现脚本与实测日志在本目录 `reports/`。

## 编译环境

- 构建系统: autotools（上游**不含预生成的 `configure`**，必须 `autoreconf` 引导）
- 构建工具链: autoconf + automake + libtool（`autogen.sh` = `autoreconf -W portability -visfm`）+ flex + bison
- 编译日期: 2026-10-02
- 编译器: clang / clang++（OHOS SDK）
- 状态: 见版本级 `manifest.yaml`

## 上游与源码

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/iovisor/ply （`wkz/ply` 为其旧地址，GitHub 会自动重定向） |
| 版本 | 2.4.0 |
| 源码归档 | https://github.com/iovisor/ply/archive/refs/tags/2.4.0.tar.gz |
| sha256 | f7c1461f3c570c91f28b1d33424846ead0d6e4429e4a9ce4429db8f2327283a5 |
| 语言构成 | C：38 × `.c`、20 × `.h`，另 1 × `.y`（grammar）、1 × `.l`（lexer）、6 × `Makefile.am`、1 × `configure.ac` |
| 外部库依赖 | **无**；`configure.ac` 仅 `AC_CHECK_HEADERS(linux/bpf.h linux/perf_event.h linux/version.h)` |
| 构建期工具依赖 | `AC_PROG_LEX` / `AC_PROG_YACC`（flex、bison）+ `AM_PROG_LIBTOOL`（libtool）+ automake ≥ 1.11 |

> ⚠️ 归档源必须用 **tag archive**（`/archive/refs/tags/2.4.0.tar.gz`）：GitHub Releases 无该版本资产
> （`/releases/download/2.4.0/...` 返回 404）。tag archive 返回 HTTP 200，属官方正式源（R39 合规）。

## 编译步骤

```sh
# 1) autotools 引导（上游无 configure，必须先 autoreconf）
./autogen.sh                      # = autoreconf -W portability -visfm

# 2) 配置 + 编译 + 安装
./configure --prefix="$DEFAULT_PREFIX" && make && make install DESTDIR="$TEST_PREFIX"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `automake`/`libtool`/`libtoolize` 缺失，`autogen.sh` 无法执行 | 本机 cmd-pkgs 环境未预装 autotools 全链 | 安装 `automake 1.16.5` + `libtool 2.4.7`（cmd-pkgs 社区源） |
| 2 | 探针进程在 `bpf()` 处**被信号 31（SIGSYS）直接杀死**（退出码 159），前半段输出随缓冲丢失 | OHOS 对未适配系统调用不返回 `ENOSYS`，而是以 SIGSYS 终止进程；stdout 为块缓冲 | 探针改造：① 每个系统调用探测放 `fork()` 子进程，父进程据退出方式判定；② `setvbuf(stdout, NULL, _IONBF, 0)` + fork 前 `fflush`。**这两条是所有 OHOS 系统调用探针的通用前提** |
| 3 | `init-build` 的嵌套源码提升对本库**误判**：纯 autotools 树无 `configure`/`Makefile`，提升逻辑把 `test/` 子目录当源码根并把真源码删除 | `_BUILD_MARKERS` 仅含 `configure/CMakeLists.txt/Makefile/meson.build`，不含 `configure.ac`/`Makefile.am`/`autogen.sh` | 手工重解 tarball 取源码（本任务以 `$TMPDIR/ply-src` 为工作源）；已作为 SKILL 框架缺陷单独上报（见"知识库扩展"节） |

## 源码修改

无（本任务未产生补丁）。

## 依赖版本

无第三方库依赖（仅内核头文件可选检测，见上表）。

## 知识库扩展：OHOS 内核追踪能力（本任务核心）

### 原理

ply 是 Linux 侧的 eBPF 追踪前端：把 ply 脚本编译成 BPF 程序 → 经 `bpf()` 系统调用加载到内核 →
用 `perf_event_open()` 创建 ring buffer 取回事件 → 通过 `tracefs`/`debugfs` 读取 `kprobe` 事件与内核符号。
它依赖**四件套**，缺一不可：

| 能力 | ply 中的位置 | 用途 |
|---|---|---|
| `bpf()` 系统调用 | `src/libply/aux/syscall.c`（`__NR_bpf`：`BPF_PROG_LOAD`/`BPF_MAP_*`） | 加载 BPF 程序、管理 BPF map |
| `perf_event_open()` | `src/libply/aux/perf_event.c`、`built-in/buffer.c`（`PERF_COUNT_SW_BPF_OUTPUT`） | 建立事件缓冲区、读取追踪数据 |
| `tracefs`/`debugfs` | `src/ply/self-test.sh`（挂载 `/sys/kernel/debug`） | kprobe 事件与追踪数据源 |
| 内核符号表 | `src/libply/aux/kallsyms.c`（`CAP_SYSLOG`） | 解析 kprobe 目标地址 |

### 实测证据（本机 HarmonyOS PC，aarch64）

复现命令：`sh archives/p/ply-probe/2.4.0/reports/repro-kernel-tracing.sh`
（完整原始日志：`reports/probe-output.log`）

| 探测项 | 实测结果 | 判定 |
|---|---|---|
| `bpf(BPF_MAP_CREATE)` | **SIGSYS（信号 31）终止子进程，退出码 159** | 🔴 平台直接拒绝（连 `ENOSYS` 的机会都没有） |
| `perf_event_open()` | `EACCES (Permission denied)` | 🔴 系统调用存在但被策略/权限拒绝 |
| `/sys/kernel/debug/tracing` | **存在**（debugfs 已挂载） | 🟡 仅目录表象 |
| `/sys/kernel/tracing` | **存在** | 🟡 同上 |
| `/proc/kallsyms` | 可读，但抽查 32 条地址**全为 0** | 🔴 符号地址被 `kptr_restrict=1` 抹零（无 CAP_SYSLOG） |
| `/proc/sys/kernel/perf_event_paranoid` | 存在可读 | 🟡 仅说明 perf 接口的准入策略存在 |
| `RLIMIT_MEMLOCK` | soft=-1 hard=-1（unlimited） | 🟢 `ply` 的 `memlock_uncap()` 为无害 no-op |

**综合判定：`VERDICT UNSUPPORTED`**——内核追踪四件套中 `bpf()`、`perf_event_open()`、符号解析三项均不可用，
tracefs 目录存在但无后端支撑。**库本体可编译安装，但除 `ply -v` / `ply -h` 外没有任何可用功能路径**
（实测于 conan 包内二进制，2026-10-02）：

| ply 调用 | 实测结果 | 原因 |
|---|---|---|
| `ply -v` / `ply -h` | ✅ rc=0 | 纯用户态输出，不触碰内核 |
| `ply -e <kprobe 脚本>` | ❌ rc=1 且**静默无输出** | 编译期即需 kallsyms 解析 `kprobe:` 目标地址；cache 创建失败（`Operation not permitted`）后 err 置位、val 为 0，`ply.c:345` 分支静默返回 1 |
| `ply -e <tracepoint 脚本>` | ❌ 报 `Unable to parse tracepoint at`（rc=133，SIGTRAP） | `/sys/kernel/debug/tracing` 无后端 |
| `ply -S <脚本>`（打印生成的 BPF） | 💀 进程被 SIGSYS 杀死（rc=159） | 该路径已下沉到 `bpf()` 加载 |
| `ply -e <非法脚本>` | ❌ rc=1 + `expecting PSPEC` / `syntax error` | 解析器本身正常（可用来证明产物非空壳） |

⇒ 此前"`-e`/`-S` 是免内核路径、可当编译前端用"的假设**已证伪**：`-e` 仍需 kallsyms。
test_package 因此只断言「产物可执行 + 解析器真实工作 + kprobe 编译路径确定性失败」，
并有意**不执行** `ply -S` / `ply -T`（二者会调用 `bpf()` 被 SIGSYS 杀死并可能落 core 文件，属 CI 环境噪声）。

### 边界（本条目适用/不适用的分界）

- **适用**：源码出现 `syscall(__NR_bpf, ...)` / `bpf_prog_load` / `perf_event_open(` / `libbpf` /
  `tracefs` / `/sys/kernel/{debug,tracing}` / `kprobe`，或链接 `-lbpf` 的软件。
- **不适用**：只用 Linux 网络抓包后端（AF_PACKET/AF_XDP/pcap）的软件 → 那是 **E334** 的范畴
  （抓包走的是 socket，不经 `bpf()`；仅当真的加载 BPF 程序时才落回本条）。
- **不适用**：仅"包含 `linux/bpf.h` 结构体/常量定义"用于**解码**的用户态程序（不调用 `bpf()` 系统调用）——
  这类程序在本平台可正常工作，预扫描命中后需人工二次确认是否真的调用系统调用。
- **注意**：探测这类系统调用**本身会杀进程**。任何"能力自检"代码都必须 `fork()` 隔离并做无缓冲输出，
  否则探测行为会把宿主进程一起带走（本任务踩坑 #2）。

### 不适用场景（本条不解决问题，只提前暴露）

- OHOS 上**没有**等价的内核追踪替代（无 bpf、无 perf、无 tracefs 后端）→ 本条目给出的是"提前识别 +
  如实声明不支持"，**不是**一个能让追踪跑起来的修复方案；需要追踪能力时应改用 Linux 环境运行该库。
- 若未来 OHOS 内核补齐 BPF（平台版本相关），本条目的 `error_signature` 会随之失效——届时应重新跑
  复现脚本并把条目降级为 `severity: 0`（resolved），而不是直接删除（保留历史判定依据）。

### 与已有知识的关系

- `similar_to: E334`（Linux 抓包后端 feature-gate：AF_PACKET/AF_XDP/libbpf）——**不同**：E334 面向网络栈
  抓包后端，本条面向内核追踪系统调用。
- `similar_to: E051` / `principles: P008`——**同一机制的另一实例**：E051 记录 `setreuid/setregid` 在 OHOS 上
  SIGSYS 且不可被 handler 捕获（进程直接终止，exit 159）；本条证明 **`bpf()` 属同一类**（同为 SIGSYS + 159），
  把该机制从"进程凭证类系统调用"扩展到"内核追踪类系统调用"，为 P008 增加第二组证据。

### 对 SKILL 框架的反馈（本任务实测发现，未在本 PR 内修改框架文件）

1. **`init_build._BUILD_MARKERS` 不含 autotools 源树标记**（`configure.ac`/`Makefile.am`/`autogen.sh`），
   导致纯 autotools 包（上游不预生成 `configure`）被嵌套源码提升逻辑**误判并删除真源码**。
   建议：`_BUILD_MARKERS` 增加 `configure.ac`、`Makefile.am`、`autogen.sh`；且提升前先确认目标子目录
   与根目录的源码文件占比，避免"把测试目录当源码根"。
2. **预扫描规则集缺"内核追踪"域**：本机 `prescan` 对 ply 全部 38 个 `.c` 文件 **0 命中**。
   本条目的 `prescan_pattern` 直插后可覆盖该缺口（验证方式：对该源码目录跑 `prescan` 应命中 E545）。

## 上游测试清点（R51）

上游测试资产共 **3 项**。用例级清点在 `test/rootfs/lib/ply/test.sh`（QEMU rootfs 套件的用例定义处）：

| 上游测试资产 | 用例数 | 在 OHOS 上的可运行性 |
|---|---|---|
| `test/rootfs/lib/ply/test.sh`（用例定义） | **9** | ❌ 0 可运行：9 个用例全部以 `ply -c` / `ply -T` 驱动真实内核追踪（kprobe / tracepoint / profile provider） |
| `src/ply/self-test.sh`（功能自测脚本） | 5 项检查 | ❌ 0 可运行：首段即要求内核追踪后端（`bpf()` → SIGSYS，见上表） |
| `test/Makefile` + `rootfs/`（QEMU 编排） | — （harness） | ❌ 不可运行：需 `qemu-system` + 交叉工具链 + 下载 rootfs/vmlinuz 镜像（网络+特权），且被测对象仍是 **Linux 内核**，与 OHOS 无交集 |

**上游用例总数 = 9**（`test/rootfs/lib/ply/test.sh` 的 9 个 `case=`）。

### 上游 9 用例逐项实测执行轨迹（2026-10-16，本机 HarmonyOS PC，aarch64）

以本包产物 `bin/ply`（含随包 `libply.so.0`）逐项执行上游用例，`ulimit -c 0`、每项 15s 上限，
退出码与平台门禁逐项对应：

| # | 上游用例 | 实测 rc | 平台门禁机制（E545） |
|---|---------|--------|---------------------|
| 1 | `self-test`（`ply -T`） | 124（超时） | 无内核追踪后端，等待无响应；`/proc/config.gz` 不可读 → `Unable to verify kernel config` |
| 2 | `exit` | 133（SIGTRAP） | kallsyms cache 创建失败（`Operation not permitted`，`kptr_restrict` 抹零） |
| 3 | `if-stmt` | 133（SIGTRAP） | 同上 |
| 4 | `print` | 133（SIGTRAP） | 同上 |
| 5 | `wildcard` | 159（SIGSYS） | `bpf()` 被信号 31 直接终止 |
| 6 | `quantize` | 1 | kallsyms 受限 → 脚本编译期失败（未下沉到 `bpf()`） |
| 7 | `interval` | 159（SIGSYS） | `bpf()` 被信号 31 直接终止 |
| 8 | `tracepoint-dyn` | 133（SIGTRAP） | kallsyms cache 创建失败 |
| 9 | `profile` | 159（SIGSYS） | `bpf()` 被信号 31 直接终止 |

**执行结果：9/9 已真实执行、0/9 通过**——9 项失败点全部落在 E545 声明的平台门禁（SIGSYS / SIGTRAP /
kallsyms EPERM）上，无一项因适配缺陷失败。

**结论**：上游用例 **9 个**、本平台可运行 **0 个**（技术原因逐项见上，非"没环境"）；
按 R51 要求补 **鸿蒙独有测试**：`test_package/` 以本平台的**真实可验证路径**覆盖产物完整性
（4/4 通过，见 `test_package/conanfile.py` 与 `reports/test-report.md`）。

## 验证结果

```sh
# 平台能力复现（预期：VERDICT UNSUPPORTED，退出码 1）
sh archives/p/ply-probe/2.4.0/reports/repro-kernel-tracing.sh

# 配方复现（详见 reports/conan-create.log 与 .ci-result.json）
conan create . --build=missing -pr:h ohos-aarch64 -pr:b default
```

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` / `conandata.yml` | Conan 配方（CI 输入） |
| `test_package/` | 鸿蒙独有测试（CI 输入） |
| `reports/ohos-kernel-tracing-probe.c` | 平台能力探针源码（知识库扩展产物） |
| `reports/repro-kernel-tracing.sh` | 复现脚本（E545 的 `verification_cmd`） |
| `reports/probe-output.log` | 探针实测原始日志（存证） |
| `knowledge/drafts/E545-draft-44F3.kv` | 知识条目草稿（含 `prescan_pattern`） |

## 注意事项

- **探测即杀进程**：任何针对 `bpf()`/`perf_event_open()` 的能力自检必须 `fork()` 隔离 + 无缓冲输出，
  否则宿主进程被 SIGSYS 带走（本任务踩坑 #2）。
- **不要伪造可用性**：`bpf()`/`perf_event_open()` 的失败是平台级事实（P013：平台限制必须降级而非绕过），
  禁止用空壳 stub 使其"成功"（R8；本条目 `forbid_1_pattern` 已机械化该红线）。
- **归档源**：只认 `github.com/iovisor/ply/archive/refs/tags/2.4.0.tar.gz`（R39：单一官方源）。
---

**编译结束**: 2026-10-02 16:24
**最终状态**: built
