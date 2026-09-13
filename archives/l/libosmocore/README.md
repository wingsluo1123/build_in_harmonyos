# libosmocore

## 简介

Osmocom 核心库，为 GSM/UMTS/GPRS 协议栈与电信信令提供基础 C 库集合，
包含 libosmocore、libosmovty、libosmogsm、libosmogb、libosmosim、libosmousb、
libosmoctrl、libosmocodec、libosmocoding、libosmoisdn 共 10 个库，
并提供 osmo-aka-verify、osmo-auc-gen、osmo-arfcn、osmo-config-merge 等命令行工具。

## OHOS 适配

- 使用原生 TLS（`-fno-emulated-tls`）：emutls 无法跨 DSO 传递 `osmo_ctx` 上下文，运行时段错误
- `config.guess` / `config.sub` 补齐 `aarch64-linux-ohos` 平台三元组（E007/E114）
- `sockaddr_storage` 与平台头文件重定义冲突，改用平台中立宏守卫（E091）
- musl 缺少 glibc 的 `__always_inline` 宏，`include/osmocom/core/hash.h` 改为平台中立写法
- 上游 1.11.0 tarball 缺 `src/gsm/kdf/crypto.h`，按上游同版本 tag 原文补齐
- 内核无 SCTP 能力时，上游测试用例自带跳过逻辑生效（`AT_SKIP_IF`）

## 依赖

- talloc / liburing / libmnl / pcsc-lite / libusb（均为制品仓预编译包）

## 功能验证

- 上游测试：90 项全部执行，通过 88 项，跳过 2 项（SCTP 内核不支持、io_uring 测试主动禁用）
- 鸿蒙专有测试：`test_package/test_ohos_tls.c`，验证 `osmo_ctx` 上下文经原生 TLS 跨 DSO 可正常访问

## 参考

- 上游项目：https://osmocom.org/projects/libosmocore
- 源码归档：https://downloads.osmocom.org/releases/libosmocore/libosmocore-1.11.0.tar.bz2
