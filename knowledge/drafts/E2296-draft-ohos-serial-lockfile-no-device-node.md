# E2296 — HarmonyOS 无 `/var/lock` 且无串口设备节点：termios 串口 bring-up 的失败点与降级取证

## 错误特征

串口类程序在无串口硬件的 HarmonyOS PC 上启动时，stderr 出现下述之一（按出现顺序）：

```
lockfile directory unavailable (No such file or directory), continuing without serial lock
using serial device /dev/ttyUSB0 9600 baud
Unable to connect to card reader device at /dev/ttyUSB0: No such file or directory
```

未适配的上游形态则是**更早**失败、且措辞指向「读写器/驱动」而非「锁目录」：

```
Could not create lockfile /var/lock/LCK..ttyUSB0 : No such file or directory
```

设备实测：`ls -ld /var` → `No such file or directory`（根目录没有 `/var`，自然也没有
`/var/lock`）；`/dev/ttyUSB0`、`/dev/ttyS0`、`/dev/input` 全部 ABSENT，仅 `/dev/tty` 存在。

## 触发条件

- 构建系统：任意（本例 autotools；现象在运行时，与构建系统无关）
- 阶段：runtime（程序启动时的设备初始化；在上游做法里常由一个 1s 定时器在 GUI 事件循环中触发）
- 前提：代码走 `#if defined(__linux__)` 一类分支做 `/var/lock/LCK..` 锁 + 固定 `/dev/ttyUSB*` 路径
  （OHOS clang 三元组为 `aarch64-linux-ohos`，`__linux__` **仍被定义**，该分支会被编进来）

## 根因分析

1990 年代串口惯例把互斥锁放在 `/var/lock/LCK..<ttyname>`，并要求「打不开锁文件就拒绝打开串口」。
HarmonyOS PC 没有 `/var` 目录树，也没有 USB/PCIe 串口设备节点，于是：

1. `fopen("/var/lock/LCK..ttyUSB0","w")` 以 `ENOENT` 失败 → 上游直接 `return -1`，
   **根本没走到 `open()` 设备节点那一步**。此时日志说的是锁文件，而真正缺的是整条设备平面，
   极易被读成「配方/权限/CMake 参数」问题而开始错误排查。
2. 即使越过锁文件（目录存在或跳过），`open("/dev/ttyUSB0", O_RDWR|O_NOCTTY)` 仍以 `ENOENT` 失败，
   后续 `tcgetattr/tcsetattr`（termios 波特率/数据位/流控配置）全部无从验证。
3. 因此「串口配置代码是否正确」在本机**结构性不可验证**——除非把设备探测做成可在无设备环境下
   独立调用并自报结果的入口。

## 解决方案

### 推荐方案

1. **锁目录降级而非硬失败**：把候选锁目录当作可选前置。`stat()` 命中目录才加锁；目录不存在时打印
   一行可 grep 的说明后继续（只对真实的权限类 errno 保持硬失败）。这样失败点回到「设备节点缺失」，
   归因正确。
2. **加无头设备探测入口**：例如 `--probe-reader`，在 `gtk_init`/主循环**之前**依次执行
   「包内资源加载 → 设备表解析 → 打开串口」，每步打一行 `PROBE key=value`，并按失败类别返回
   不同退出码（资源缺失 / 设备表为空 / 无读写器 / 无设备节点各自可区分）。
3. **测试断言 PROBE 行 + 退出码**，而不是断言"程序没崩"。这样在既无串口硬件、又无图形会话的
   机器上仍能回归到真实代码路径（实测 rfdump：`PROBE ui=OK widgets=5/5`、`PROBE tagtypes=26`、
   `reader=ABSENT`、`device_node=MISSING`，退出码 5）。

### 禁止做法

- ❌ 在设备或 CI 上 `mkdir /var/lock`（或 `touch` 锁文件）来"修好"它——只是掩盖问题：
  CI worker 与设备环境不同，造出的目录不跟随交付；且 HMDFS 上目录模式落盘后不可改（E011 族）。
- ❌ 把「Could not create lockfile /var/lock/...」当成配方/工具链缺陷去调参。
- ❌ 断言"GUI 能开窗"作为串口类适配通过条件（无显示环境下永远不成立）。

## 验证

```bash
# 1) 环境事实：没有 /var，也没有串口设备节点
ls -ld /var/lock; ls -l /dev/ttyUSB0

# 2) 无头探测（GTK3 broadway 后端提供显示连接；无串口硬件时按返回码判类别）
GDK_BACKEND=broadway BROADWAY_DISPLAY=:7 rfdump --probe-reader -p /dev/ttyUSB0
#   PROBE ui=OK widgets=5/5 file=<prefix>/share/rfdump/rfdump.ui
#   PROBE tagtypes=26
#   PROBE serial_device=/dev/ttyUSB0 fd=-1
#   PROBE reader=ABSENT
#   PROBE device_node=MISSING        → 退出码 5

# 3) 归因断言：失败点是设备节点，而不是锁目录
... 2>&1 | grep -c "Could not create lockfile"        # 期望 0
```

## 关联条目

- 相关：E011（同为 HMDFS/权限位类目录故障；可叠加出现，需按证据区分）
- 相关：`/tmp` 只读族（同为「路径在该平台不存在/不可写」的固化石窟）
