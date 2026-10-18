# E4310 — `/dev/shm` 写满时 POSIX shm 的 `mmap` 首次访问以 SIGSEGV 呈现（掩盖 ENOSPC/SIGBUS）

> 状态：**草稿**（`knowledge/drafts/E4310-draft-8CAA.kv`）
> 首次命中：lttng-ust 2.12.10 适配（`feat/lttng-ust-2.12.10`）· 2026-10-18
> 严重度：🔴 3（现场无任何 ENOSPC 提示，极易误判为包/内核缺陷）
> **定级说明**：根因是**环境**（`/dev/shm` 这个全设备共享的 1GiB tmpfs 被写满），
> 但「把 ENOSPC 呈现为不可捕获的 SIGSEGV」这一**掩盖机制**是平台语义，
> 值得沉淀；排查时应先看 `df -h /dev/shm`。

## 错误特征

没有任何可读的报错日志，现场只有一行：

```
Segmentation fault (core dumped)      # 进程 rc=139 / terminated by signal 11
```

典型上下文（多线程库）：程序在加载后**数毫秒内**被杀，日志停在库的某个"等待/通知"
输出上；在 `main` 线程里安装的 `SIGSEGV` handler **永不触发**。上游 TAP 框架下表现为：

```
ERROR: ust-elf/test_ust_elf - too few tests run (expected 48, got 7)
ERROR: ust-elf/test_ust_elf - exited with status 139 (terminated by signal 11?)
```

审计侧还有一种误判形态：CI/设备上"同一份二进制有时过有时不过"（本机实测同一用例一次
跑到 12 条断言、下一次只到 7 条），被当成 flaky test 忽略。

## 触发条件

- 平台：OpenHarmony / HarmonyOS PC，aarch64-linux-ohos
- **前置条件：`/dev/shm`（tmpfs，本机 1.0 GiB）Avail = 0**
- 触发调用面：`shm_open()` → `ftruncate()` → `mmap(MAP_SHARED|MAP_PRIVATE, …)`
  之后**对该映射第一次访问"尚未分配的那一页"**
- 与编译器/构建系统无关；与 `PROT_READ` / `PROT_READ|PROT_WRITE` 无关；
  `MAP_POPULATE` 不能让它提前报错

## 根因分析

`/dev/shm` 写满时，POSIX 共享内存对象仍然可以"申请"成功——tmpfs 的 `ftruncate`
只改 i_size、页在**首次触碰时**才分配：

```
$ df -h /dev/shm
tmpfs           1.0G 1.0G     0 100% /dev/shm
$ python3 -c "import shutil;print(shutil.disk_usage('/dev/shm'))"
usage(total=1073741824, used=1073741824, free=0)

shm_open("/probe-shm", O_CREAT|O_RDWR, 0600) = 3      # 成功
ftruncate(fd, 4096)                          = 0      # 成功
fstat(fd).st_size                            = 4096   # 成功
mmap(NULL, 4096, PROT_READ, MAP_SHARED, fd, 0) = 0x…  # 成功，非 MAP_FAILED
*(volatile int32_t *)0x…                     -> SIGSEGV   # 首次触碰，页分配不出来
```

**判据（把"空间"与"映射机制"分开）**：对同一对象的 fd 直接写，错误码是可见的：

```
write(fd, buf, 4096)  ->  -1, errno=28 (ENOSPC)
```

五组合全部复现 rc=139：`MAP_SHARED`+`PROT_READ`（读）、`MAP_SHARED`+`PROT_READ|WRITE`
（读/写）、`MAP_PRIVATE`+`PROT_READ`（读）、`MAP_PRIVATE`+`PROT_READ|WRITE`（写）。
加 `MAP_POPULATE` 后 `mmap` 仍返回成功、随后读仍 SIGSEGV。

对照组**全部正常**（rc=0），说明不是"映射机制坏了"，而是"这个 tmpfs 没空间"：

| 对照 | 结果 | 说明 |
|---|---|---|
| 匿名 `mmap(MAP_SHARED\|MAP_ANONYMOUS)` 读写 | rc=0 | 不落在 `/dev/shm` |
| 普通文件 `mmap(MAP_SHARED)` 读 | rc=0 | 页已存在（先写过） |
| `memfd_create()+ftruncate()+mmap()` 读写 | rc=0 | 走内核内部 tmpfs，有空间 |
| `liburcu-bp` `rcu_register_thread`/`call_rcu` | rc=0 | — |
| 空程序 / `nanosleep` | rc=0 | — |

**为什么难查（本条目的核心价值）**：Linux 常规语义下，触碰未分配的 tmpfs 共享页
应得到 **SIGBUS**；本平台把它投递成 **SIGSEGV**，且 `write()` 的 ENOSPC 在 mmap
路径上完全不可见。若该访问发生在一个
`pthread_sigmask(SIG_SETMASK, sigfillset())` 的线程里，同步 SIGSEGV 在信号被屏蔽时
由内核**直接按默认动作终止**——用户态 handler 不运行。实测：同一进程内
`*(int*)0=1` 的 handler 能被正常调用（rc=77），而该库线程的崩溃永远进不了 handler
（rc=139）。本机复核手段：把该线程的信号屏蔽临时解除后重新编译被调库，再用
`SA_SIGINFO` + `ucontext.uc_mcontext.pc` + `dladdr()` 打出 PC，即可定位到
`liblttng-ust.so` 的 `wait_for_sessiond()`（`liblttng-ust/lttng-ust-comm.c:1471`，
`uatomic_read((int32_t *) sock_info->wait_shm_mmap)`）。

**影响面**：`/dev/shm` 是**全设备共享**的 1GiB tmpfs。任一并发任务写满它，就会让所有
正在用 POSIX shm 的进程在加载后数毫秒内静默死亡，而它们的日志里不会出现 ENOSPC。
`ls /dev/shm` 在本机亦 `Permission denied`（无法列举、无法自查是谁占满）。

**与既有条目的关系**：E1940 / E2070 记录"OHOS 沙箱拦截 SysV 共享内存
（shmget/shmat → SIGSYS），应改用 POSIX `shm_open`+`mmap`"。本条目补上限定条件：
在 `/dev/shm` 有空间时该建议成立；**空间耗尽时 POSIX 通道会以 rc=139 静默失败**。

## 解决方案

### 推荐方案（环境面优先）

1. **先看空间再跑**：`df -h /dev/shm`（Avail 非 0）与
   `python3 -c "import shutil;print(shutil.disk_usage('/dev/shm'))"`。
   这是**环境**问题，不要改配方、不要判配方失败——按本仓库口径等同于
   `conan_verify_round` 的 rc=3「环境暂时耗尽」，记录读数后等窗口重跑。
   **可重跑性**：本轮失败与包无关；空间恢复后同一份提交应能取得干净读数。
2. **空间受限时仍要前进**：
   - 同进程 / 父子进程共享 → `memfd_create()` + `ftruncate` + `mmap`
     （本机实测 rc=0，可 fork 继承）；跨无关进程经 Unix 域套接字 `SCM_RIGHTS` 传 fd。
   - 只需一个可 futex 的共享字 / 小状态 → 匿名 `mmap(MAP_SHARED|MAP_ANONYMOUS)`。
   - 库侧自保：初始化阶段做一次"写入 + 读回"可用性探针，用只覆盖探针区间的
     `SIGSEGV` handler + `sigsetjmp/siglongjmp` 兜住；不可用时降级到不依赖 shm 的
     路径（poll/pipe）。不要"跳过整个初始化"——那会让功能静默失效。

### 禁止做法

- ❌ 看到 `mmap` 返回非 `MAP_FAILED` 就认为映射可用（空间耗尽时它一定成功）。
- ❌ 在**屏蔽了全部信号**的线程里指望 `SIGSEGV` handler 兜住（handler 不会运行）。
- ❌ 把它当 flaky test 重跑或加 `sleep` 掩盖（重跑只是碰巧在崩溃前跑完）。
- ❌ 只凭"另一台/另一轮能过"就判定包有问题或平台缺陷——先 `df -h /dev/shm`。

## 验证

```bash
# ① 环境读数：期望 Avail=0、Use%=100
df -h /dev/shm
python3 -c "import shutil;d=shutil.disk_usage('/dev/shm');print('avail_bytes=',d.free)"

# ② 证明是"空间"而非"映射"：fd 直写应报 ENOSPC
python3 - <<'PY'
import os, errno
fd = os.open("/dev/shm/probe-write-test", os.O_CREAT|os.O_RDWR, 0o600)
os.ftruncate(fd, 4096)
try:
    os.write(fd, b"x"*4096); print("write ok")
except OSError as e:
    print("write FAILED:", e.errno, errno.errorcode.get(e.errno))   # 期望 28 ENOSPC
os.close(fd); os.unlink("/dev/shm/probe-write-test")
PY

# ③ 五组合探针：期望 "mmap ok 0x..." 之后 Segmentation fault、rc=139
clang -O0 -std=gnu11 -D_GNU_SOURCE "$TASK_DIR/w0/probe/shm2.c" -o /tmp/shm2
for m in 0 1 3 5 7; do /tmp/shm2 $m /p$m; echo "mode=$m rc=$?"; done

# ④ 对照（均应 rc=0）：匿名+普通文件 / memfd
clang -O0 -std=gnu11 "$TASK_DIR/w0/probe/mm1.c" -o /tmp/mm1 && /tmp/mm1; echo rc=$?
clang -O0 -std=gnu11 "$TASK_DIR/w0/probe/mm2.c" -o /tmp/mm2 && /tmp/mm2; echo rc=$?
```

## 关联条目

- 相似 / 需并列阅读：E1940、E2070（SysV shm → SIGSYS，建议改 POSIX shm）、
  E1340（HMDFS 不支持 mknod/FIFO，同类"平台原语缺失"）
- 本条目由 lttng-ust 2.12.10 适配的 `ust-elf/test_ust_elf` 阻塞触发
