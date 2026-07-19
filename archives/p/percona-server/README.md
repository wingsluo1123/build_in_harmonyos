# percona-server

## 简介

Percona Server for MySQL 8.0.36 — Percona 发行的 MySQL 兼容数据库服务器。本配方仅构建客户端库（libperconaserverclient），供 Qt6 SQL 驱动插件（qt-percona-server）等下游消费者链接使用。

## OHOS 适配

- 仅构建客户端库（`-DWITHOUT_SERVER=ON`），不编译完整数据库服务器
- CMake 构建系统，自动下载 Boost 头文件依赖
- 产物：`libperconaserverclient.so` / `libperconaserverclient.a`
- ARM64 X18 保留寄存器问题已在适配补丁中处理

## 依赖

- 编译依赖：cmake、openssl、zlib
- 运行依赖：openssl、zlib

## 参考

- 官网：https://www.percona.com/software/mysql-database/percona-server
- 源码：https://github.com/percona/percona-server

