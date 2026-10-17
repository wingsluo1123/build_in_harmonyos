# miredo

miredo 是 Rémi Denis-Courmont 维护的 **Teredo IPv6 隧道**（RFC 4380）实现：在只有 IPv4
的环境里为用户提供 IPv6 连通性，含客户端守护进程、中继服务器与配套工具。

## 功能概述

- **miredo**：Teredo 客户端守护进程（建立隧道、维护 Teredo 地址、处理认证）
- **miredo-server**：Teredo 中继（relay）服务器
- **miredo-checkconf**：配置语法与语义校验工具
- **teredo-mire**：Teredo 数据包诊断/伪造工具
- **库**：
  - `libteredo` —— Teredo 协议实现（隧道建立、HMAC 认证、peerlist 维护），头文件 `include/teredo`、`include/libteredo`
  - `libtun6` —— TUN/TAP 用户态驱动封装（隧道设备与 IPv6 地址配置）

## OHOS 适配要点

- **config.guess / config.sub 不识别 HarmonyOS**：上游发布包自带 2012 年版 autotools
  辅助脚本，`uname -s` 返回 `HarmonyOS` 时既猜不出三元组，且该版本没有新版 `GUESS`
  出口机制（插入分支必须自带 `echo ... ; exit ;;`）→ 补丁 0004/0005（E007/E429）
- **HMDFS 权限归一化**：`(umask 077 && mktemp -d)` 生成的探测/临时目录在 HMDFS 上连属主
  都不可写（`config.guess` 报 `can't create .../dummy.c`、`config.status` 报
  `could not setup config files machinery`）→ 去掉 config.guess 的 umask 077（补丁 0004），
  预生成 `configure` 的同类改写在配方 `build()` 内完成（E114/E430）
- **无 POSIX 线程取消**：OHOS musl 不导出 `pthread_cancel` / `pthread_setcancelstate` /
  `pthread_testcancel`（E127）→ 回退实现内联进 `libteredo/debug.h` 与 `src/relayd.c`
  （补丁 0003/0006）；只靠取消停止的 peerlist 回收线程改为 stop 标志协作式退出（补丁 0001，E431）
- **`struct ethhdr` 重复定义**：libc `netinet/if_ether.h` 与内核 UAPI `linux/if_ether.h`
  冲突，按 `__UAPI_DEF_ETHHDR` 守卫（补丁 0002，E119）
- **依赖注入**：配方 `generate()` 叠加 `AutotoolsDeps`，否则 `Judy.h`/`-lJudy`、
  `sys/capability.h`/`-lcap` 的 `AC_CHECK_*` 探测为 no（回落 tdestroy、无特权降级）

## 依赖关系

### 编译依赖

- **judy**（1.0.5）—— 配置解析使用的动态数组库（`configure` 以 `Judy.h` + `-lJudy` 探测）
- **libcap**（2.78）—— 特权降级（`sys/capability.h` + `-lcap` 探测）

### 运行依赖

- **TUN/TAP 设备**（`/dev/net/tun`，需特权）—— 隧道本体；无该设备时库 API 与
  `miredo-checkconf`/`teredo-mire` 仍可用，隧道建立不可用
- IPv6 网络与服务端（做端到端连通性验证所需）

## 已知限制

- Teredo 需要 TUN 设备、IPv6 网络与服务端，本项目构建环境不具备，**未做端到端隧道
  连通性验证**；`libtun6-diagnose` 用例因此 SKIP（上游 12 项：11 PASS / 1 SKIP）
- 线程取消回退只覆盖 peerlist 回收线程的停止路径；`libteredo/relay.c` 接收线程、
  `libteredo/server.c` 中继线程与 `src/relayd.c` 封装线程仍依赖取消语义，
  在 OHOS 上退出时可能残留等待（不影响库 API 与 CLI 可用性）

## 参考资料

- 官网与源码：https://www.remlab.net/miredo/
- Teredo 协议：RFC 4380
