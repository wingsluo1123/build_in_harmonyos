# iw

## 简介

`iw` 是基于 nl80211（cfg80211）的无线设备配置命令行工具 —— 扫描、连接、网卡与
phy 管理、功率/regulatory 设置等，是 `wireless-tools`（老 WEXT ioctl 协议）在
新内核上的继任者。

- 官网: https://wireless.wiki.kernel.org/en/users/documentation/iw
- 上游源: https://www.kernel.org/pub/software/network/iw/
- 许可证: ISC
- 语言: C
- 构建系统: 纯 Makefile（无 configure、非 autotools）

## OHOS 适配

- 当前编译版本: 6.17
- 平台三元组: `aarch64-unknown-linux-ohos`
- 需要的补丁: 1 个（musl sysroot 下 `<linux/socket.h>` 与 `<sys/socket.h>` 的
  `struct sockaddr_storage` 重定义 —— 预锁 `_UAPI_LINUX_SOCKET_H` 并补
  `__kernel_sa_family_t` typedef）
- 依赖: libnl/3.11.0（generic netlink 封装；制品仓仅发布静态库 ⇒ iw 静态链入，
  运行期只依赖 `libc.so`）

## 功能验证

- 可用面：CLI 契约（`--version` / usage / 命令表）与交叉编译产物正确性；
  `test_package/test_iw.py` 11 条断言实跑全过。
- **平台能力墙（不可修）**：本平台 app 沙箱在**创建**
  `socket(AF_NETLINK, SOCK_RAW, NETLINK_GENERIC=16)` 时即返回 `EACCES(13)`
  （`NETLINK_ROUTE(0)` 可创建可 bind；连未分配的协议号也是 `EACCES` 而非
  `EAFNOSUPPORT`，说明是沙箱按协议号做白名单，不是内核缺该协议族）。
  因此所有需要内核回话的子命令（`iw dev` / `iw list` / `iw phy` …）以
  `Failed to connect to generic netlink.` 退出 `rc=1`。与 `ethtool` 的 netlink 面
  同源（ethtool 为此改用 `--disable-netlink`）。
- **上游测试**：注册自动化用例数 = 0（R51 六探针全 0 命中）；Makefile 里唯一的
  `check:` 目标是 `sparse -Wall cgcc` 静态分析 lint，**不是测试套件**，故不作为
  上游套件执行、也不计入通过率。
