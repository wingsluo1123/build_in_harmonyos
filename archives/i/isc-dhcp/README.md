# isc-dhcp

ISC DHCP 的 **客户端/服务器/中继套件本体**，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

ISC DHCP 是经典的 DHCPv4/DHCPv6 实现。本包交付 4.4.3-P1 完整套件：

- `dhcpd` —— DHCP 服务器（租约数据库、failover 对等、OMAPI 管理接口）
- `dhclient` —— DHCP 客户端（含 DHCPv6 客户端能力）
- `dhcrelay` —— DHCP/BOOTP 中继代理（支持 DHCPv6 模式）
- `omshell` —— OMAPI 交互式管理 shell
- `libdhcp.a` / `libomapi.a` / `libdhcpctl.a` —— 服务器运行时库、OMAPI 对象 API、
  控制通道 API（`include/omapip` 与 `include/dhcpctl` 公共头随包）
- 捆绑 BIND 9.11.36 的四个库（libisc/libdns/libisccfg/libirs）——三个 DHCP 库的
  静态链接闭包，同包交付

## OHOS 适配要点

- 上游是 2014 年代的 autotools 构建树，config.guess/config.sub 不识别 OHOS：
  补丁 `0001`/`0002` 增加 HarmonyOS 主机探测（输出 `aarch64-unknown-linux-ohos`）
  与 `*-linux-ohos` 三元组模式；`0004`/`0005` 同修捆绑的 BIND 9.11.36
- HMDFS 用户卷拒收 configure 临时目录探测创建的 0700 目录（E011）：`0003`/`0006`
  把探测的 umask 077 改为 022
- OHOS 内核拒绝直接 exec 非签名解释器脚本：`0007` 让 bind/Makefile 以
  `$(SHELL) ./configure` 调用捆绑 BIND 的 configure；配方另把 configure 生成的
  Makefile 中 automake 的 `MKDIR_P` 回退（`install-sh -c -d`）改写为 `mkdir -p`
- 发布 tarball 捆绑的 BIND 以 `bind/bind.tar.gz` 内嵌：配方先解包（补丁有落点）
  再应用补丁链，捆绑 BIND 的 configure/make 由 bind/Makefile 幂等规则全自动驱动
- 构建为 in-source，与 OHOS 真机 bring-up 一致；对外无第三方依赖

## 依赖关系

- 无第三方依赖（捆绑 BIND；`--without-openssl/libxml2/libjson/gssapi/lmdb`）
- 上游测试（server/tests 五个 ATF 套件）需外带 atf-0.19 工具链：
  `-o tests=True -c user.isc-dhcp:atf_prefix=<prefix>`

## 参考资料

- 官网：https://www.isc.org/dhcp/
- 上游仓库：https://gitlab.isc.org/isc-projects/dhcp
- 源码包：https://ftp.isc.org/isc/dhcp/4.4.3-P1/dhcp-4.4.3-P1.tar.gz
