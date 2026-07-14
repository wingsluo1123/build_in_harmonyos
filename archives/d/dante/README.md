# dante

> SOCKS server and client, implementing RFC 1928 and related standards.

## 简介

Dante 是一个免费的 SOCKS 代理服务器和客户端实现，支持 SOCKS4、SOCKS5 协议（RFC 1928）。它由服务端 `sockd` 和客户端工具 `socksify` 组成，同时提供 C API 库 `libsocks` 供应用程序直接集成。

## OHOS 适配要点

1. **config.guess/config.sub 需替换**：添加 OHOS triplet 支持（E007）
2. **HMDFS 权限修复**：configure 中 `umask 077` 导致临时目录权限异常（E011），已在补丁中修复
3. **resolver 禁用**：OHOS musl libc 不支持 `_res` 全局变量，需 `HAVE_NO_RESOLVESTUFF=1`
4. **CPU affinity 禁用**：OHOS 不支持 `cpu_set_t`，需 `HAVE_SCHED_SETAFFINITY=0`
5. **CONFIG_SHELL=bash**：系统 `/bin/sh` 为 mksh，需指定 bash 作为 configure shell

## 依赖

无外部依赖，仅依赖 musl libc (OpenHarmony 系统自带)。

## 功能验证

```bash
# 服务端版本验证
sockd -v
# 预期: Dante v1.4.4

# 配置文件验证（非root可用）
sockd -V -f /etc/sockd.conf
```

## 参考

- [官方网站](https://www.inet.no/dante/)
- [源码下载](https://www.inet.no/dante/files/)
