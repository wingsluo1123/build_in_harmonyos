# ifenslave — bonding 接口配置工具

## 简介

ifenslave 用于将从接口绑定到 bonding 主设备，实现简单的负载均衡（与交换机的 channel bonding / trunking 同理）。2.10 起不再提供 `/sbin/ifenslave` 二进制，改由 ifupdown 钩子脚本通过 `ip` 命令与 `/sys/class/net/*/bonding/` sysfs 完成 enslavement。

本仓库 2.14 分发上游 3 个 ifupdown 钩子（`ifenslave.if-pre-up`、`ifenslave.if-up`、`ifenslave.if-post-down`）、systemd link 与 4 个接口配置示例。

## 已适配版本

- **版本**: 2.14
- **状态**: built（待真机预检后由 HMBS 更新）
- **许可证**: GPL-3.0-or-later
- **构建系统**: custom（纯脚本，无编译）

## 下载地址

- 源码: https://deb.debian.org/debian/pool/main/i/ifenslave/ifenslave_2.14.tar.xz
- 上游仓库: https://salsa.debian.org/debian/ifenslave

## 用法示例

```bash
# 查看钩子（Conan 包 bin/ 下）
ls /path/to/ifenslave/bin
sh -n /path/to/ifenslave/bin/ifenslave.if-pre-up

# Debian 接口配置示例（详见 share/doc/ifenslave/examples/two_ethernet）
# auto bond0
# iface bond0 inet dhcp
#   bond-slaves eth0 eth1
```

## 注意事项

- 需要 Linux bonding 内核支持与 `ifupdown` + `iproute2` 运行时，HarmonyOS PC 无此栈，仅做脚本分发与静态校验
- 上游无自动化测试，消费者测试为静态检查（存在性/shebang/`sh -n`/sysfs 契约关键字/文档），不触碰 `/sys`、不调用 `ip`
