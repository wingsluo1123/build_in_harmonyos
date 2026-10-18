# E545 — OHOS 不提供 Linux 内核追踪接口（eBPF/kprobe/perf_event/tracefs）

> 草稿状态：待主编审核 promote 为正式条目（R17/R31）
> 载体库：ply-probe 2.4.0（上游 iovisor/ply），知识库扩展任务产出

## 错误特征

追踪类软件（内嵌 BPF 编译器 / libbpf / bcc / bpftrace）在 OHOS 上的表现按阶段分三类：

```
# 运行期：bpf() 不是返回 ENOSYS，而是被平台直接以信号杀死
Bad system call
$ echo $?          # 159 = 128 + 31
159

# 运行期：perf_event_open() 权限拒绝（普通用户 euid=20020100）
perf_event_open: Operation not permitted

# 编译期：kallsyms 不可用导致 kprobe 脚本编译器直接失败（ply -e 静默 rc=1）
ply: error: unknown symbol 'vfs_read'      # 或解析期无输出直接退出

# 编译期：内核头文件缺失（vendored 头可绕开，见下）
linux/bpf.h: No such file or directory
cannot find -lbpf
```

## 触发条件

- 构建系统: autotools / cmake / make / meson 均可（与本模式无关）
- 阶段: configuration / compilation / **runtime**（多数场景仅在运行期暴露）
- 触发动作: 任何调用 `bpf()` / `perf_event_open()`，或读取 `/proc/kallsyms`、`/sys/kernel/debug/tracing` 的代码

## 根因分析

OHOS 内核未提供 Linux 追踪子系统，且各接口的失败形态与常规 Linux 容器/无权限环境**完全不同**：

| 接口 | OHOS 实测 | 与常规 Linux 的差异 |
|------|-----------|---------------------|
| `bpf()`（syscall 280） | **SIGSYS（aarch64 信号 31）→ 进程被终止，rc=159** | Linux 无权限时返回 `EPERM`；ENOSYS 时才表示未实现。此处直接杀进程，**无法用返回值优雅降级** |
| `perf_event_open()` | `EACCES` | 与 Linux 的权限模型一致，但无任何可用替代 |
| `/proc/kallsyms` | 文件存在，**地址列被 `kptr_restrict` 全部抹零**（`0000000000000000`） | Linux 下 root/CAP_SYSLOG 可读到真实地址；无法读到地址 → kprobe 符号表无法建立 → 脚本**编译期**即失败 |
| `/sys/kernel/debug/tracing`、`/sys/kernel/tracing` | **目录存在但无后端**（仅目录表象，无 tracefs 接口） | Linux 下可从 `available_*` 系列文件枚举可挂载的 kprobe/tracepoint |
| `linux/bpf.h` / `linux/perf_event.h` | 头文件**存在**（构建期不报错） | 与"缺头文件"型故障表象相反：**能编译，不能运行** |

两条关键结论：

1. **编译通过 ≠ 可用**。头文件齐备使软件可正常编译链接，故障只在运行期出现，若只做构建期验证会漏判。
2. **探测此特性本身有副作用**：调用 `bpf()` 的进程会被直接杀死，因此探测代码**必须 fork 隔离**（子进程内调用、父进程 `waitpid` 收集终止信号），否则探针自己就被 SIGSYS 打断、拿不到后续证据。

## 解决方案

### 推荐方案

构建期保留产物、运行期**如实声明平台不支持**（feature-gate + declared-unsupported）：

1. 配方照常编译发布（`ply` 一类软件的 BPF 编译器/解析器部分在 OHOS 上可编译、可执行）；
2. `notes.md` / 软件级 `README.md` 明确写出「哪些路径不可用、失败形态是什么」，不做任何桩替代；
3. `test_package` 只断言**确实存在**的能力（`--version` / `--help` / 脚本解析器拒绝非法输入），并对内核路径断言「失败但未下沉到 `bpf()`」（如 `rc != 159`）；
4. 需求方确需追踪能力 → 用 Linux 主机/容器，不在 OHOS 侧伪造成功。

### 禁止做法

- ❌ 用空壳 stub 让 `bpf()` / `perf_event_open()` 假装成功（返回 0 或假 fd）——用户会得到错误的"追踪可用"信号，问题被推迟到运行期（违反 R8：禁止空壳 stub）
- ❌ 把 `bpf()` 的 SIGSYS 误判为「平台不支持该 syscall → 补个 ENOSYS 包装就完事」：进程已被杀死，包装无意义
- ❌ 在 `patches/` 中新增 `#elif defined(__OHOS__)` 之类平台宏分支来"绕过"能力探测（违反 R8/PF5；本模式的正确做法是如实声明 + 三元组修复，而非宏分支）

## 验证

```bash
# 自包含探针：fork 隔离 + ctypes 直调 bpf()（syscall 280），父进程收集终止信号
python3 -c "import ctypes,os;pid=os.fork();
print('CHILD-KILLED-BY-SIGNAL', (os.waitpid(pid,0)[1] & 0x7f)) if pid else (ctypes.CDLL(None,use_errno=True).syscall(280,0,0,0,0,0), os._exit(0))"

# 预期输出: CHILD-KILLED-BY-SIGNAL 31      （31 = SIGSYS，即 bpf() 被平台终止）

# kallsyms 地址抹零
awk 'NR<=3 {print $1, $3}' /proc/kallsyms     # 预期: 0000000000000000 T <symbol>

# tracefs 目录存在但无后端
ls -d /sys/kernel/debug/tracing /sys/kernel/tracing
```

完整探针源码与实测日志见载体库 `archives/p/ply-probe/2.4.0/notes.md`（OHOS 内核追踪能力探针附录），
本仓库 `reports/` 目录为 `.gitignore` 覆盖的 AI 元数据区，故此处以自包含命令为准。

## 关联条目

- 相关: E334（syscall/追踪相关系统调用缺口）, E051（未实现 syscall → 需从能力探测中排除）
- 反向: E002（`/tmp` 只读）、E114（`mktemp -d` 目录不可写）——同为"平台语义差异而非编译错误"族
