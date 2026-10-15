# musl-nscd

## 简介

musl-nscd 是 NSCD（Name Service Cache Daemon）协议的一个实现，面向 musl libc。
它像 glibc 的 nscd 一样使用 NSS 模块，从而为 musl 的 user/group 数据库提供可替换的
后端（LDAP、NIS、自定义模块等）。所用协议是 glibc nscd 协议的一个子集。

要使用哪些模块由 `/etc/nsswitch.conf` 配置，语法与 glibc 一致。

## 功能概述

- `nscd` 守护进程：按 `nsswitch.conf` 装载 NSS 模块（`dlopen("libnss_<service>.so.2")`
  + `dlsym("_nss_<service>_<name>")`），在 AF_UNIX socket 上提供 NSCD 协议服务。
- 支持四类请求：`GETPWBYNAME`、`GETPWBYUID`、`GETGRBYNAME`、`GETGRBYGID`，
  以及 `GETINITGR`（initgroups）。
- 可选缓存：`-C <秒>` 设置缓存失效时间、`-n <条数>` 设置最大条目数。
- 命令行参数：`-c <nsswitch.conf>`、`-s <socket 路径>`、`-p <pidfile>`、
  `-j <线程数>`、`-d`（守护化）。

## OHOS 适配

- **开箱可编译，无需补丁**。上游为纯 POSIX C（`dlopen` / `AF_UNIX` / `pthread` /
  `poll` / `syslog` / `stdatomic`），零外部依赖；OHOS 的 libc 为 musl 派生，与上游
  设计目标一致，`port/*.c` 的结构体字段探针在 OHOS 上也正常通过。
- **构建系统是手写 configure + Makefile**（不是 Autotools）。`configure` 只接受
  `--prefix` 等目录参数与 `VAR=VALUE` 形式的 `CC`/`CFLAGS`；配方以
  `--prefix=/` + `make install DESTDIR=<package_folder>` 精确控制打包内容。
- **R33**：Makefile 直接用 `$(CC)`，Conan Toolchain 无法注入编译器；配方在
  `generate()` 中从 `tools.build:compiler_executables` 取编译器并写入 conanbuild
  env 脚本，不依赖 shell 里的 `$CC`。
- **R38**：产物含可执行文件 `sbin/nscd`，软件级目录已声明 `commands.json`。
- **上游无测试套件**（Makefile 无 `check`/`test` 目标、无 `tests/` 目录）。按 R51
  清点后补全测试：`test_package/` 编译一个桩 NSS 模块与 NSCD 协议客户端，真实启动
  被测 `nscd` 守护进程并经 AF_UNIX socket 取回 passwd/group 条目，覆盖四类请求的
  命中与未命中分支、两条上游错误路径以及反复连接（共 32 项断言）。
- **部署注意**：默认的 `/etc/nsswitch.conf` 与 `/var/run/nscd/socket` 在 OHOS 上
  未必存在或可写，运行时需用 `-c` / `-s` / `-p` 指向实际可写路径。

## 依赖关系

- 编译依赖：无（仅需 C 编译器与 make）
- 运行依赖：一个或多个 `libnss_<service>.so.2` 形式的 NSS 模块（由 `nsswitch.conf` 指定）

## 交付物

| 路径 | 说明 |
|------|------|
| `sbin/nscd` | NSCD 协议守护进程 |
| `include/nss.h` | NSS 模块 API 头文件（`enum nss_status`） |
| `share/man/man8/musl-nscd.8` | 手册页 |
| `licenses/COPYRIGHT` | 上游 MIT 许可证原文 |

## 参考资料

- 官网/源码: https://github.com/pikhq/musl-nscd
- License: MIT
