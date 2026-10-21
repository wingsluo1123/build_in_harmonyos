# KB-SOCK-MACRO — BSD 兼容层兜底定义覆盖系统已有的 socket 扩展宏

**一句话**：兼容层为老系统写的 `#ifndef HAVE_SOCK_CLOEXEC` → `#define SOCK_CLOEXEC 0` 兜底，
在 OHOS musl（`sysroot/usr/include/sys/socket.h`）已经把 `SOCK_CLOEXEC` 定义为 `02000000` 的平台上
会**覆盖系统真值**：编译期 `-Wmacro-redefined`（`-Werror` 下直接红），运行期 `socket()` 的
`CLOEXEC` / `NONBLOCK` 位静默丢失。

## 触发场景

- 适配对象是 BSD 系代码或带 `bsd-compat/`、`compat/`、`portable/` 目录的库；
- 上游 `configure` 没有探测 `HAVE_SOCK_CLOEXEC` 一类能力宏，兼容层走兜底分支；
- 兜底值写成 `0`（或任何与平台不同的值），且**没有** `#ifndef <MACRO>` 硬守卫。

两类症状（同源，可只出现其一）：

| 阶段 | 特征 | 说明 |
|---|---|---|
| 编译期 | `warning: 'SOCK_CLOEXEC' macro redefined [-Wmacro-redefined]` + `note: previous definition is here ... sys/socket.h:99: #define SOCK_CLOEXEC 02000000` | `-Werror` / `-Werror=macro-redefined` 下变 error；多数发行构建与 CI 默认开 |
| 运行期 | `socket()` 返回成功，但 `fcntl(fd, F_GETFD)` 无 `FD_CLOEXEC`、`F_GETFL` 无 `O_NONBLOCK` | 宏已被覆盖成 `0`，type 参数里这两位直接消失；fd 泄漏给 exec 的子进程、非阻塞语义丢失 |

**实证库**：sndio 1.10.0 —— `bsd-compat/bsd-compat.h:58`

```c
#ifndef HAVE_SOCK_CLOEXEC
#define SOCK_CLOEXEC	0        /* 平台真值是 02000000 */
#endif
```

同形态代码广泛存在于 BSD 移植层（tmux、openssh、OpenBSD ports 的 `bsd-compat`、各类 `portable/` 目录），
因此按**共性问题**入库，而不是 sndio 单库补丁。

## 为什么必须修，而不是当警告放过

1. `-Werror` 是发行构建常态；即使只当警告，CI 里 `2 warnings generated.` 也会被门禁拦。
2. 更严重的是值错了：`02000000` → `0` 之后编译依然成功，缺陷只在运行期以 fd 泄漏/阻塞语义错乱的形式出现，
   静态看宏名完全正常。**编译通过 ≠ 行为正确**，这是本条目的核心教训。

## 检测（`detect.sh`）

三通道，只读，不修改任何文件：

| 通道 | 输入 | 判据 |
|---|---|---|
| A 源码 | `--src <dir>` | 源码中 `#define <宏>` 前 12 行内没有同宏 `#ifndef` 守卫，且**目标平台已定义该宏** |
| B 日志 | `--log <build.log>` | `'<宏>' macro redefined` / `redefinition of '<宏>'` |
| C 能力对照 | `--cc <compiler>` | `$CC -dM -E` 探平台真值，与兜底值对照；平台未定义该宏时**不命中**（兜底合理） |

```bash
bash detect.sh --src <source-dir> [--log <build.log>] [--cc <clang>] [--json]
# 退出码 0=未命中 1=命中A 2=命中B 3=A+B
```

实测（真实 sndio 1.10.0 源码）：

```
KB-SOCK-MACRO HIT-A (1): .../sndio-1.10.0/bsd-compat/bsd-compat.h:58 SOCK_CLOEXEC: platform 02000000 overridden by SOCK_CLOEXEC 0
platform: MSG_CMSG_CLOEXEC=0x40000000 MSG_NOSIGNAL=0x4000 SOCK_CLOEXEC=02000000 SOCK_NONBLOCK=04000 SOCK_SEQPACKET=5 SO_REUSEPORT=15
```

## 处理策略（`fix.sh`）

只做一件事：给未守卫的兜底定义补上硬守卫，让**系统已提供时以系统为准**、平台真没有时兜底照旧生效。

```diff
 #ifndef HAVE_SOCK_CLOEXEC
+#ifndef SOCK_CLOEXEC
 #define SOCK_CLOEXEC	0
 #endif
+#endif
```

取舍（为什么不选别的路）：

| 方案 | 问题 |
|---|---|
| `-D<MACRO>=02000000` 塞进构建命令 | 平台细节煮进 recipe，换平台/换 SDK 即错；且把缺陷藏起来 |
| 关掉 `-Wmacro-redefined` | 告警是编译期唯一能发现"值被覆盖"的信号 |
| 把兜底值改成系统值 | 兼容层是给没有该宏的系统用的，写死 Linux 值会破坏它原本的用途 |
| 只补守卫（本方案） | 一份代码在两类系统上都正确，改动最小、无行为副作用 |

```bash
bash fix.sh --src <source-dir> [--cc <clang>] [--dry-run] [--json]   # 幂等，可重复执行
```

**配方集成建议**：走 recipe 侧 `patching`（与 sndio 0001 一致），而不是在 `build()` 里现改。
打完补丁后必须**断言生效**——本机 `/usr/bin/patch` 是 toybox，对部分补丁会 RC=0 却不改文件
（见图谱 E510/E254/E484），建议：`grep -q '#ifndef SOCK_CLOEXEC' <src>/bsd-compat/bsd-compat.h` 或
`git apply --check` 复核，失败即 `raise ConanInvalidConfiguration`/直接报错。

## 复现（`reproduce.sh`）

样例库 `sample/sockcloexec-demo/`：兼容层头（上游缺陷形态）+ 真实 `socket()` 调用点 + 消费者行为断言。

```bash
bash reproduce.sh [--sample <dir>] [--cc <clang>] [--keep] [--json]
# 退出码 0=两阶段符合预期 1=ON 阶段未通过 2=OFF 阶段未复现
```

实测结果（clang 15.0.4，Target `aarch64-unknown-linux-ohos`）：

| 阶段 | 命令 | 结果 |
|---|---|---|
| ① 无 SKILL | `clang -Wall` 宽松编译 | **rc=0**，2 条 `macro redefined` 警告 |
| ① 无 SKILL | 运行消费者断言 | **rc=1**，`not ok 2 FD_CLOEXEC` / `not ok 3 O_NONBLOCK` |
| ① 无 SKILL | `-Werror=macro-redefined` 严格编译 | **rc=1**，2 errors（abort 在编译期） |
| ② 有 SKILL | `detect.sh` | HIT-A **2 处**（SOCK_CLOEXEC / SOCK_NONBLOCK） |
| ② 有 SKILL | `fix.sh` | 2 sites guarded |
| ② 有 SKILL | 严格编译 + 断言 | **rc=0**，`ok 1..3` 全绿 |

## 限制与边界

- **只在目标平台已定义该宏时命中**：平台确实没有该宏（老 BSD、非 Linux 目标）时，上游兜底是正确行为，脚本不报；
- 判据是"值被覆盖"，不处理"语义差异"：如 `MSG_NOSIGNAL` 平台值非 0 但行为不同、`SO_REUSEPORT` 语义在新旧内核不同，
  这些需逐条人工判断，不能靠守卫机械修；
- 只覆盖 socket 扩展位这一族；其它"兼容层兜底值与平台冲突"的宏（`CLOCK_UPTIME`、`strlcpy` 等）应另立条目；
- 不替代 `configure` 能力探测：补守卫只保证值正确，若上游还需要 `HAVE_*` 走不同代码路径，另见对应条目（如 E086 ucred 族）。

## 文件清单

| 文件 | 作用 |
|---|---|
| `README.md` | 触发场景、判据、策略、限制（本文件） |
| `detect.sh` | 三通道检测器（源码 / 日志 / 平台能力对照），退出码可编排 |
| `fix.sh` | 守卫插入器，幂等，`--dry-run` 可预览 |
| `notes.md` | 取证表（宏真值、日志原文、实测数据）+ 踩坑 + 与图谱条目边界 |
| `reproduce.sh` | 两阶段复现（OFF 必失败 / ON 必通过），日志落盘、无管道截断 |
| `sample/sockcloexec-demo/` | 最小样例库：兼容层头 + 调用点 + 消费者断言 + Makefile |
