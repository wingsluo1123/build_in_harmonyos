# lksctp-tools for HarmonyOS

lksctp-tools 1.0.21 是 Linux SCTP 用户空间工具集与 libsctp 库（sctp_darn/sctp_test/checksctp 工具 + SCTP socket API 客户端库），本归档将其适配至 HarmonyOS PC（arm64）。

## 功能概述

- `libsctp`：SCTP socket API 用户空间库（`sctp_opt_info`、`sctp_bindx` 等扩展接口）
- `sctp_darn`：SCTP 诊断与测试命令行工具
- `sctp_test`：SCTP 功能与压力测试工具
- `checksctp`：检查系统 SCTP 可用性的小工具

## OHOS 适配

- **头文件冲突（E091）**：OHOS musl `sys/socket.h` 与 linux UAPI `linux/socket.h` 均定义 `sockaddr_storage`，在 `src/include/netinet/sctp.h.in` 与 func_tests 中加入 define-guard（patch 0012 与 0001-0011）
- **自举（bootstrap）**：GitHub archive tarball 不含 configure，配方用 tool_requires automake/libtool + `autoreconf` 自举
- **configure 平台识别**：config.guess 无法识别 HarmonyOS（uname -s=HarmonyOS），配方显式指定 `--build/--host=aarch64-unknown-linux-musl`（与知识库 E007/E011 forbid_1_pattern 的适用性对照见同版草稿 DRAFT-lksctp-tools-1.0.21-config-guess-explicit-triplet）
- **HMDFS 权限（E011）**：configure/config.status 中 `umask 077` 改写为 `umask 022`（HMDFS UID 映射导致 0700 临时目录不可写）

## 依赖关系

- 编译依赖：无第三方 Conan requires（仅系统 libc/libc++）；tool_requires automake/1.18、libtool/2.5.4
- 运行依赖：OHOS 系统 libc/libc++；内核 SCTP 模块（可选，仅 func_tests 运行需要；OHOS 默认无 `/proc/net/sctp`）

## 参考资料

- 上游仓库：https://github.com/sctp/lksctp-tools
- 上游版本：v1.0.21（commit 37d5f122，2024-09-26）