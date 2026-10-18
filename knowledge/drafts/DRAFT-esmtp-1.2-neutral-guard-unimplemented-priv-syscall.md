# DRAFT-esmtp-1.2-neutral-guard-unimplemented-priv-syscall

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-esmtp-1.2-neutral-guard-unimplemented-priv-syscall.kv`
> 说明：该 kv 为结构化条目，本文档为其可读镜像 + 查重说明。

---

# 平台未实现的特权 syscall：用「语义等价守卫」跳过，而不是平台宏

- 条目主题：运行期无条件调用 `setregid`/`setreuid` 的程序在本平台被 seccomp 直接 SIGSYS(31)
  终止（exit 159），且信号不可捕获；当该调用本就是空操作时，用**等价条件守卫**跳过它。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联包：`archives/e/esmtp/1.2`（机制面不限于 esmtp）

## 适用场景

- 表象：`--version` / `--help` 全部正常，一进入**真实功能路径**就
  `Bad system call (core dumped)`、退出码 **159**（=128+31）。
- 典型代码形态（esmtp 1.2 `main.c:27 drop_sgids()`）：

```c
real_gid = getgid();
effective_gid = getegid();
if( setregid(real_gid,real_gid) != 0 ) { ... exit(EX_DROPPERM); }
```

- 命中条件：进程**不是** setgid/setuid（`real == effective`），即该调用在 POSIX 语义上是
  **空操作**，却仍触发被拦截的 syscall 号。

## 诊断步骤（30 行级探针，不含第三方库代码）

1. 读 `/proc/self/status` 的 `Seccomp` / `Seccomp_filters`，确认存在过滤器。
2. **fork-per-syscall 探针**：父进程逐个 fork 子进程调用候选 syscall，按
   `WIFSIGNALED/WEXITSTATUS` 分类 —— 一次跑完一整张能力表，避免「第一个就崩、后面没测到」。
   本包实测读数：

   | syscall | 结果 |
   |---|---|
   | `setregid` | **SIG31 (Bad system call)** |
   | `setreuid` | **SIG31 (Bad system call)** |
   | `setgid` / `setuid` / `setresgid` / `setresuid` / `setgroups` / `initgroups` / `chown` | 正常返回 |
   | `connect(127.0.0.1)` | 正常返回（回环 TCP 面可用） |

3. 打印 `uid/euid/gid/egid` 证明是否本就不需要降权（本包四者同为 20020084）。
4. 定位上游调用点，确认它是不是**无条件**执行。

## 解法（推荐，rec_priority=1）

只在真的需要改变身份时才发 syscall：

```c
if( real_gid != effective_gid && setregid(real_gid, real_gid) != 0 ) { ... }
```

- 等价性：`real == effective` 时 `setregid(x,x)` 按 POSIX 就是 no-op，跳过它不改变任何语义；
  真正的 setgid 部署下分支照常执行，降权行为不打折。
- 补丁只依赖上游已有变量，**不含 `__OHOS__`、不含任何平台条件编译** ⇒ R8/PF5 天然通过。

## 为什么不是 `hit(E051)`

- `E051` 诊断一致（`setreuid/setregid` 的 SIGSYS 不可捕获、进程直接终止），本条**引用**它。
- 但 `E051.rec_approach = source-patch`，`rec_description` 明确写「在 C 源码中用 **#ifdef __OHOS__**
  守卫」—— 该写法在本工作区被铁律 R8 + PF5 fail-closed **明令禁止**。
- 按 `手册/03` 判 `hit` 四条件之第 2 条：**「症状相同、但用的是既有条目没写的另一条解法时不算 hit，
  按 create 报」** ⇒ 本条报 `create`，`similar_to: E051, E246`。
- 新增价值（组合型知识）：**「诊断沿用 E051 + 解法换成中性等价守卫」**这条解题路径的适用面本身是增量
  —— 它把「被禁的平台宏写法」换成了任何包都能照抄的 POSIX 写法。

## 证据（真实执行）

- `conan create esmtp/1.2` 第二轮红：`test.sh: line 120: 49507 Bad system call (core dumped)`、
  `esmtp delivery exited with 159`；server 侧 `accept()` 超时（客户端根本没走到连接）。
- 打 `0002-skip-noop-setregid.patch` 后第三轮 **G2 PASS**，test_package 端到端会话全绿：
  `EHLO localhost / MAIL FROM:<sender@example.com> / RCPT TO:<rcpt@example.com> / DATA /
  （含 Date、Message-Id 的完整报文）/ QUIT`。
- 探针与日志：`~/tmp/uc2/esmtp/probe/forkprobe.c`、`archives/e/esmtp/1.2/reports/conan-create.log`。

## 推广价值

- 所有 sendmail 兼容程序、邮件/网络客户端、setgid 守护进程的降权分支，在「非 setgid 部署」场景下
  都可用同一守卫照抄。
- 给「平台宏被禁（R8/PF5）」的包提供一条**不引入 `__OHOS__`** 的等价替代写法。

## 查重关键词

SIGSYS, signal 31, exit 159, setregid, setreuid, Bad system call, seccomp, 空操作, 等价守卫,
drop_sgids, 降权, R8, PF5, __OHOS__, neutral patch, E051, E246
