# dhcp-probe

Attempts to discover DHCP and BootP servers on a network.

## 功能特性

- 发送 DHCP 探测请求并捕获响应
- 支持 IEEE 802.1Q VLAN 标签
- 配置文件驱动，支持自定义探测参数
- 支持多个合法 DHCP 服务器白名单
- 可配置的响应等待时间和重试策略

## 版本列表

| 版本 | 状态 | 发布日期 |
|------|------|----------|
| 1.3.1 | ✅ published | 2026-08-06 |

## 依赖

- libpcap >= 1.0 (数据包捕获) — Conan: libpcap/1.10.6
- libnet >= 1.2 (网络数据包构造) — Conan: libnet/1.2

## 相关链接

- 官方网站: https://www.net.princeton.edu/software/dhcp_probe/
- 源码下载: https://www.net.princeton.edu/software/dhcp_probe/dhcp_probe-1.3.1.tar.gz
