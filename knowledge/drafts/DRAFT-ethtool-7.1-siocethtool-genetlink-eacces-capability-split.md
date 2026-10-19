# DRAFT: OHOS 上 SIOCETHTOOL/genetlink 双双 EACCES —— 差分能力探针 + 信息面断言交付

- **草稿 ID**: DRAFT-ethtool-7.1-siocethtool-genetlink-eacces-capability-split
- **来源库**: ethtool 7.1（HarmonyOS PC aarch64, clang 15.0.4, HongMeng Kernel 1.12.0）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **申报口径**: 按「组合型知识不判重」按 create 申报 —— 组分清单与组合后新增路径见文末

## 问题（三机实测）

ethtool 7.1 的核心功能面是 **ETHTOOL ioctl** 与 **ethtool netlink(genetlink)** 两条通道。
在本平台上**编译全通、功能面运行期全不可达**，且这是**权限策略**而非内核缺失：

| 探针（本机 + A 机 + B 机三处读数一致） | 结果 |
|---|---|
| 正对照：同一 `AF_INET/SOCK_DGRAM` 套接字 `ioctl(SIOCGIFFLAGS)` / `ioctl(SIOCGIFINDEX)` | **rc=0** |
| 目标：`ioctl(SIOCETHTOOL, 0x8946)`，含只读 `ETHTOOL_GDRVINFO` | **errno=13 EACCES**（lo/eth0/wlan0 全拒） |
| `socket(AF_NETLINK, SOCK_RAW, NETLINK_GENERIC)` | **创建即 errno=13 EACCES** |
| `socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE)` + 修正版 `RTM_GETLINK` dump | OK，收 17916B / 8 块 / 含 NLMSG_DONE |
| `os.listdir("/sys/class/net")` | **errno=13 EACCES**（`/proc/net/dev` 可读，15–16 行） |
| `/proc/self/status` | `CapEff=000000000000002a`（无 CAP_NET_ADMIN/CAP_NET_RAW）、`Seccomp=2`、`Seccomp_filters=1` |
| 对照族：`socket(AF_CAN, SOCK_RAW, 0)` | **errno=97 EAFNOSUPPORT**（can-utils 型"内核不提供"墙，用于区分两类墙） |

A/B 两机的探针由各自 `sshd` 启动进程执行（不经发起会话的沙箱）⇒ 读数是**平台事实**，
不是某一环境的伪影。首版探针的 `RTM_GETLINK` 因漏发 16 字节 `ifinfomsg` 载荷而 Timeout，
已自纠重跑，**不拿错读数充数**。

## 上游降级路径穷举（结论：无非特权替代）

- `ethtool.c` 的 `args[]` 表中 `no_dev=true` **只有两条**：`-h|--help`（:6386）与 `--version`（:6392）；
- 其余全部功能命令走 `ETHTOOL_G/S` ioctl（ethtool.c 内 94 处）或 netlink/genetlink；
- `--disable-netlink`（:6420/:6677）只是 **netlink ↔ ioctl 互退**，两面同墙；
- `fopen` 的 `gregs_dump_file`（:3548）与 `do_writefump`（:4775）都要**先** `send_ioctl` 拿到设备数据，不构成文件替代路径。

⇒ 属「唯一功能面被权限策略拦死且上游无替代」，但**信息面（--version/-h）与构建产物完整可交付**。

## 交付口径（可执行、可复核）

1. **差分探针留证**：正对照（基础 ioctl rc=0）+ 目标面 errno + 进程态（CapEff/Seccomp）+ 跨机复测，四件套齐才允许下"能力面被拦"的结论；
2. **test_package 只断言信息面真实输出**：`ethtool --version` 退出码 + 输出含 `ethtool version 7.1`；`ethtool -h` 退出码 + 输出含 `Usage:` 与 `--disable-netlink` 特征串（`grep -q`，非空即过），**⛔ 不用 `|| true` 兜底、⛔ 不断言任何网卡诊断功能**；
3. **披露措辞钉死**：写「本平台测试进程无相应 capability，功能面未能实测；已实测 `-h`/`--version` 与构建产物完整」，**⛔ 不写「在鸿蒙上不可用」** 这类平台级定性（对外口径归主理/用户裁定）；
4. **不改上游语义、不加平台宏**：能力差异是环境事实，补丁里 `#ifdef __OHOS__` 属 R8/PF5 违规。

## 组分清单与组合后新增的解题路径（create 申报依据）

| 组分 | 池内既有条目 | 本包用到的部分 |
|---|---|---|
| HMDFS `umask 077` 临时目录不可写 → `config.status`/`subs1.awk` Permission denied | **E223**（关键词含 config.status、subs1.awk、mktemp、umask 077） | configure 补丁方案（去 `umask 077` 包裹 + `chmod 755`） |
| netlink 运行期不可用 → 编译验证 + 运行期降级披露 | **E237**（`no NETLINK_GENERIC`、rec=compile-verify-with-runtime-degradation） | 交付模式（编译/产物为准、运行期降级如实披露） |
| 信息面（--version/--help）作为安全探针与正负对照 | **E357**（informational option、safe probe、negative control） | 测试设计（信息面断言 + 对照组读数） |
| 能力被拦的网络交互测试要给替代测试路径 | **E287**（CAP_NET_RAW、raw socket、alternative test） | "功能面不可测时给替代测试并逐条申报"的记账口径 |
| 能力面切分 + 负对照 | **E240**（capability-split-with-negative-tests） | 差分探针的正/负对照结构 |

**新增（池内 0 命中，`index.tsv` grep SIOCETHTOOL/genetlink-EACCES 无命中）**：
① **机制域本身**：SIOCETHTOOL ioctl 与 genetlink socket 的 EACCES 能力墙读数（含正对照 rc=0 与 `AF_CAN` errno=97 的"两类墙"区分），`OHOS行为探针清单.md` 43 行也无该机制域行；
② **判定链**：正对照差分 + 三机复测 + 上游 `no_dev` 穷举三步连成可复用的"判能力墙甲乙"流程；
③ **组合交付路径**：E223 的补丁 + E237 的交付模式 + E357 的信息面断言，在"内核接口存在但被权限策略拦死"这一格上合成新的可复用解题路径与适用面。

## 与高相似条目的分层（draft-review TOP 逐条反向举证）

`draft-review --top 5` 实测：E008=0.33、E303=0.31、E363=0.23、E237=0.15、E246=0.05（均 <0.5，预审建议 review-similar→E008 灰区）。

| 条目 | 它的机制/解法 | 本草稿为何不同（同族不同签名不同解法） |
|---|---|---|
| E008 | SELinux 策略拒绝对**管道/终端/套接字等非普通文件 fd** 的 `fstat()/lseek()`；解法 = 源码补丁绕 stat | 本机制是**目标 ioctl(0x8946) 与 genetlink socket 创建**被能力策略拒绝，fd 的 stat/seek 正常；解法**不是源码补丁**，而是差分探针定性 + 信息面断言 + 披露 |
| E303 | 受限域 `opendir("/")` EACCES，被当坏文件名 | 面不同（目录枚举 vs 网卡 ioctl/netlink），解法不同（域识别 vs 交付口径） |
| E237 | 内核**不提供** ACPI 接口（ENOENT 类缺失），acpid 不可运行 | errno 类不同（EACCES 权限拦 vs ENOENT 缺失）；结论不同（信息面可交付 vs 不可运行）；本机制有正对照 rc=0 证明接口本体存在 |
| E246 | seccomp 按 syscall 号拦截（SIGSYS 可捕获） | 本机制返回 errno=13 于 ioctl/genetlink 层，非 syscall 号 SIGSYS |

## 解法对打（与 E237 / E240 正面比，hit 四条件第 1、2 条）

**签名（四条件 1）**：本包 = `SIOCETHTOOL/NETLINK_GENERIC → errno=13`（**权限拦截、接口本体存在**，触发条件 = 测试进程无 CAP_NET_ADMIN、Seccomp=2）；E237 = `/proc/acpi` 等 `No such file`（**ENOENT 接口缺失**，触发 = acpid 启动探测 ACPI）；E240 = `CGDisplayCopyDisplayMode` 等符号/框架面缺失（触发 = 显示工具调 macOS API）。**两类墙判别**：本平台 `socket(AF_CAN)` → `errno=97 EAFNOSUPPORT`（真缺家族走此码）而 `NETLINK_GENERIC` → `errno=13` ⇒ 接口在、权限拦；正对照 `SIOCGIFFLAGS` rc=0 证明基础 ioctl 可用。三签名互不重合，图谱 grep 本机制 0 命中。

**解法（四条件 2）**：
- 相对 **E237 选项 1**（compile-verify-only：编译/verify 全绿 + notes 声明缺失）——交付骨架同形、**明确认作复用组分**；本包多做三件它没写的事：① **差分归因证据包**（正对照 rc=0 + 三机复测 + CapEff/Seccomp + AF_CAN errno=97 两类墙对照；E237 的 verification_cmd 只有存在性检查、区分不了 ENOENT/EACCES）；② **上游无替代穷举**（no_dev 仅 2 条、94 处 ioctl/genetlink、--disable-netlink 互退、fopen 先要 send_ioctl）；③ **test_package 5 条信息面硬断言**（把「跑起来了」变成 CI 可执行判据，E237 止于 notes 声明）。
- 相对 **E240**（capability-split-with-negative-tests）——E240 **实现了 OHOS 后端**（OH_NativeDisplayManager 只读指标）再对不支持项做**负向断言**；本包**无后端可实现**，走「不实现 + 上游 no_dev 信息面**正断言** + 全量披露」；E240 的 fallback（无后端则 validate() 拒发）亦未采用（该取舍属对外口径，由主理/用户裁定）。**对原问的精确作答：功能面＝没有解法、只披露；交付面＝有解法（证据包 + 正断言），而这条交付解法两条既有条目都没写成可执行规则。**

**结论：`create`（组合型）** —— 组分 = E237 交付骨架 + E223 补丁方案 + E357 信息面探针口径 + E287/E240 断言设计；新增面 = 「接口本体存在但被 capability 拦死」这一格的判据流程（差分正对照归因 + 两类墙 errno 判别 + 上游无替代穷举 + 信息面正断言交付）。张力交回：若按「交付骨架同形」改判 `hit(E237)`，四条件 1 的「症状一致」需一并放宽，归主理终审。

## 验证命令

```sh
python3 probe.py   # 差分探针：SIOCGIFFLAGS=rc0 / SIOCETHTOOL=errno13 / genetlink=errno13 / sysfs=errno13
grep -n "no_dev" ethtool.c   # 仅 :6386 与 :6392 两条
ethtool --version | grep -q "ethtool version 7.1" && ethtool -h | grep -q "Usage:"
```
