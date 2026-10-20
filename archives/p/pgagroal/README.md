# pgagroal

PostgreSQL 高性能连接池（A high performance connection pool for PostgreSQL）。

## 功能概述

pgagroal 在客户端与 PostgreSQL 服务端之间维护连接池，降低建连开销并提供连接复用、鉴权与 TLS 卸载。
本包交付共享库与五个命令行工具：

| 组件 | 说明 |
|------|------|
| `libpgagroal.so` | 连接池核心库（本包 `package_type = "shared-library"`） |
| `pgagroal` | 连接池守护进程 |
| `pgagroal-cli` | 运行时管理工具（启停、重载配置、查看状态） |
| `pgagroal-admin` | 管理工具（用户/密钥、配置文件生成） |
| `pgagroal-vault` | Vault 密码管理后端 |
| `pgagroal-config` | 配置生成器 |

## OHOS 适配要点

- 上游 CMake 的依赖探测只覆盖 Linux/Darwin/FreeBSD：以 `if (CMAKE_SYSTEM_NAME STREQUAL "Linux")`
  选择事件循环后端，而 Conan 把 OHOS 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，故配方显式补
  `-DHAVE_LINUX=1` 走 epoll/eventfd/timerfd 分支（OHOS 无 BSD 的 `sys/event.h`）。
- CMake 4.x 的 `FindOpenSSL` 只定义单数 `OPENSSL_INCLUDE_DIR`，而上游非 Linux 分支读复数
  `OPENSSL_INCLUDE_DIRS`，配方两者都注入。
- man 手册依赖 `rst2man`（OHOS 无 python3-docutils）：补丁让手册优雅跳过，其余行为与上游一致。
- 制品仓中 zlib/bzip2/lz4/OpenSSL 只提供 PIC 静态库，上游的静态库拒绝检查由可选开关
  `PGAGROAL_ALLOW_STATIC_DEPS` 放开（默认保持上游严格行为）。
- musl 无 glibc 扩展 `secure_getenv()`，按 `__GLIBC__` 特性宏回退 `getenv()`。
- io_uring / systemd / libatomic 只在上游的 Linux 分支探测，OHOS 上自动跳过，不构成本包依赖。

## 依赖关系

`zlib/1.3.2.1`、`bzip2/1.0.8.2`、`zstd/1.5.6`、`lz4/1.10.0.3`、`openssl/3.5.8.1`（均已在 ohpcd 制品仓发布），
系统库 `pthread`。

## Versions
- 2.1.0: Conan-adapted for HarmonyOS PC (aarch64)

## 参考资料

- 上游项目：<https://pgagroal.github.io/pgagroal/>
- 适配笔记：`2.1.0/notes.md`（含 6 处构建问题的根因与修法）
