# ubridge

ubridge 是 GNS3 项目自研的**用户态 bridge**：它在用户空间把 UDP tunnel、Ethernet、TAP 等
接口彼此桥接，从而在无法或不宜使用内核 bridge/tap 的环境里（无特权、跨平台、需要精细控制
转发行为的场景）提供网络互联能力。

## 功能概述

- 用户态二层转发：在 UDP tunnel、Ethernet、TAP 接口之间桥接以太网帧。
- 多 hypervisor 支持：`brctl`（Linux 内核 bridge）、`link`（veth/pcap 链路）、`docker` 四类
  后端，外加 `bridge`（用户态 bridge）与 `hypervisor`（管理通道）两类基础模块。
- 模块化：每个 hypervisor 以独立 `.c` 文件实现，通过统一注册表按名字装载，未编译进的模块
  在 `module_list` 中不出现。
- 控制协议：通过 TCP 控制端口（`-H <host> -p <port>`）以文本命令驱动，命令形如
  `<module> <command> [args...]`，应答首字段为状态码（100 = OK，2xx = 各类错误）。
- 附带 CLI：`-v` 打印版本、`-h` 打印用法。

## OHOS 适配

与 Linux 的差异及适配要点（实现见版本级 `conanfile.py` 与 `patches/`）：

- **`uname` 返回 `HarmonyOS` 而非 `Linux`**：上游 Makefile 用 `ifeq ($(shell uname), Linux)`
  判定平台，OHOS 上该分支整段被跳过，导致 `brctl`/`link`/`docker`/netlink 等源文件根本不参与
  编译（产物只剩 `hypervisor`/`bridge` 两个模块）。判定条件需同时接受 `Linux` 与 `HarmonyOS`。
- **`struct sockaddr_storage` 重复定义**：OHOS 的 UAPI `<linux/socket.h>`（经 `<linux/if.h>`、
  `<linux/netlink.h>`、`<linux/if_tun.h>` 间接引入）与 musl 的 `<sys/socket.h>` 都定义该结构，
  在 OHOS 下需把内核头包裹在临时宏改名区间内。
- **glibc 专有类型 `ushort` 在 musl 未定义**：应改用标准 `unsigned short`（`u_short` 亦可用）。
- **线程取消 API 缺失**：OHOS 的 musl 既不声明也不导出 `pthread_cancel`/`pthread_testcancel`。
  本软件是 `pthread_cancel(tid); pthread_join(tid, NULL);` 的用法，用空实现顶替会让 `join`
  永久阻塞，需以保留信号 + 处理器内 `pthread_exit` 保留取消语义。
- **无 `setcap`**：上游 `make install` 目标依赖 `setcap`，OHOS 不提供该工具；打包不应走
  `make install`，直接拷贝二进制即可。
- **运行权限**：真实创建/删除内核 bridge 需要 `cap_net_admin,cap_net_raw`；无特权时变更类命令
  返回 `206`/`207`（EACCES/EPERM）并保持进程存活，属预期行为而非缺陷。

## 依赖关系

| 类型 | 依赖 | 说明 |
|------|------|------|
| 编译 | libpcap（`-lpcap`） | 唯一外部依赖，用于 `link` 模块的抓包/注入 |
| 编译 | iniparser | 上游默认内嵌 `src/iniparser/`，无需外部包 |
| 运行 | `cap_net_admin`、`cap_net_raw` | 仅真实变更内核网络设备时需要 |
| 运行 | TCP 控制端口 | 由调用方（GNS3 / 测试套件）连接驱动 |

## 参考资料

- 源码仓库：<https://github.com/GNS3/ubridge>
- 项目主页：<https://www.gns3.com/>
