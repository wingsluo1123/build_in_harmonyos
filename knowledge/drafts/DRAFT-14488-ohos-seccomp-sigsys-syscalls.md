# DRAFT-14488-ohos-seccomp-sigsys-syscalls

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-14488-ohos-seccomp-sigsys-syscalls.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-14488-2: OHOS seccomp 以 **SIGSYS 终结进程**而非返回 errno —— 可用性探测型库的适配诊断模式

- 条目主题：OHOS 的 seccomp 策略对部分系统调用直接投递 **SIGSYS（信号 31，进程被终结）**，而 Linux 生态的库普遍以「调用后读 errno（ENOSYS/EPERM/EINVAL）」的方式探测能力。两者语义冲突：**探测即进程死亡**。含实测清单（`clone3`/`rseq`/`ptrace`/`memfd+PROT_EXEC`）与运行时检测方案。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联 PR：`archives/d/dynamorio/11.91.20676`（PR !14488）

## 适用场景

- 进程「无征兆猝死」，退出码 `159`（=128+31，SIGSYS）或 `126`（EPERM）；dmesg/日志无输出。
- 库在初始化阶段**静默 no-op** 或崩溃：典型如「探测某 syscall 是否可用 → 决定是否启用某特性」。
- 有 `ptrace` 依赖的工具链（gdb/lldb/strace）不可用 → 常规排障手段失效。

## 现象与实测清单（OHOS PC aarch64）

| 系统调用 | 实测结果 | 对库的影响 |
|---|---|---|
| `clone3` (435) | **SIGSYS 终结**（非 ENOSYS/EINVAL） | 依赖「探测 clone3 再回退 clone」的运行时（DR 的 `detect_unsupported_syscalls`）直接被杀 |
| `rseq` (293) | **SIGSYS 终结** | 同上；且库若按「seccomp 拦 rseq 返回 -EPERM」编写回退逻辑，此处语义不成立 |
| `ptrace` | `EACCES`（非 SIGSYS） | gdb/lldb 完全不可用（`Could not trace the inferior process`） |
| `memfd_create` + `PROT_EXEC` mmap | mmap 失败 | JIT/代码缓存类库必须改走匿名 RWX 或 `mprotect`（**匿名 RWX 与 RWX↔RX 的 mprotect 实测可用**） |
| 匿名 `mmap(RWX)`、`mprotect` | 可用 | JIT 可执行内存的正确路径 |
| `MAP_FIXED_NOREPLACE` | **ENOSYS**（非 EINVAL） | 只按 EINVAL 回退的库会「保留失败」 |

## 诊断步骤

```bash
# 1) 启动期加 SA_SIGINFO 的 SIGSYS 处理器，打印被拦的 syscall 号（无需 ptrace）
#    handler: write("SIGSYS syscall=%d", si->si_syscall) 然后 _exit()
# 2) 或运行时判定「是否有 seccomp 过滤器」：
grep -E '^Seccomp' /proc/self/status      # Seccomp: 2 + Seccomp_filters: 1 → 过滤器生效
# 3) 探针式逐 syscall 验证：每次只调一个 syscall 并 `echo rc=$?`，
#    159/31 → SIGSYS 型拦截；errno 有值 → 常规拦截
```

## 规避（推荐做法）

1. **运行时能力判定优先**：读 `/proc/self/status` 的 `Seccomp` 字段（原始 syscall 读取 + 结果缓存，因初始化期堆/fd 未就绪），过滤器生效时**跳过**可能被阻断的 syscall 探测，直接判定「不可用/不启用」。
2. **不要**用编译期平台宏短路（`#ifdef __OHOS__`）——知识库 R8 要求可移植性；运行时判定对「任何启用同类 seccomp 策略的环境」都成立（沙箱化容器同理受益）。
3. JIT 类库：可执行内存走**匿名 mmap(RWX) → mprotect(RX)**，不要依赖 `memfd` + `PROT_EXEC`。
4. 依赖 `MAP_FIXED_NOREPLACE` 的库：把 **ENOSYS 与 EINVAL 一同**作为「回退到不带该 flag」的触发条件。

## 证据（本库实测）

- `syscall(SYS_clone3, NULL, 0)` → 进程被 SIGSYS 终结（探针捕获 `si_syscall=435`）。
- `syscall(SYS_rseq, 0,0,0,0)` → SIGSYS（`si_syscall=293`）。
- `mmap(..., MAP_FIXED_NOREPLACE)` → `errno=38 (Function not implemented)`。
- `memfd_create` 成功但 `mmap(memfd, RWX)` 失败；匿名 RWX 成功、`mprotect(RW→RX)` 成功。
- `/proc/self/status`: `Seccomp: 2`, `Seccomp_filters: 1`。
