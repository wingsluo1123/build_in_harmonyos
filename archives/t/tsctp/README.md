# tsctp

TSCTP（TSCTP - An SCTP Test Tool）是 SCTP（Stream Control Transmission Protocol）测试工具：
以客户端/服务端两种模式对 SCTP 实现做互通性与基本功能验证（消息收发、多宿、PR-SCTP、
AUTH、UDP 封装等）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.8.6 | published | CMake 源码编译（clang 15 / OHOS aarch64），依赖 lksctp-tools 1.0.21 |

## 概述

- **产物**：单一可执行文件 `tsctp`（外加 man1 手册与 bash 补全）
- **上游**：<https://github.com/dreibh/tsctp>，官网 <https://www.nntb.no/~dreibh/tsctp/>
- **许可证**：BSD-3-Clause AND GPL-3.0-or-later
- **依赖**：`lksctp-tools/1.0.21`（提供 `netinet/sctp.h` 与 `libsctp`，对应 Debian
  `libsctp-dev >= 1.0.5`）；`Threads` 为系统 libc pthread

## 用法

```bash
# 服务端：绑定所有 IPv4/IPv6 地址，监听 1234
tsctp -L :: -L 0.0.0.0 -p 1234

# 客户端：连到 127.0.0.1:1234，发送 4096 字节消息，10 秒后停止
tsctp -L :: -L 0.0.0.0 -n 10 -l 1000 -p 1234 127.0.0.1
```

## 构建方式

- **类型**：源码编译（CMake）
- **来源**：GitHub tag 归档 `tsctp-0.8.6`（sha256 `c4defcd5…3785`）
- **补丁**：`patches/0001-CMakeLists.txt.patch` —— 把 `HarmonyOS` 加入
  `CMAKE_SYSTEM_NAME` 白名单（Conan OHOS profile 映射值，不是 `OHOS`），并让
  `FIND_LIBRARY(SCTP_LIB sctp REQUIRED)` 对 HarmonyOS 与 Linux 走同一分支
- **依赖注入**：`generate()` 用 `CMAKE_REQUIRED_INCLUDES` / `CMAKE_LIBRARY_PATH` /
  `extra_cflags(-I)` 把 lksctp-tools 的头与库喂给上游自带的 CMake 探测逻辑

## 测试

- **上游自动化测试**：无（`ctest -N` → `Total Tests: 0`；无 tests/ 目录）。上游真实功能测试入口
  是 `src/batch`、`src/batchLoop` 两个需要真实 SCTP 协议栈的端到端驱动脚本。
- **test_package**（消费者用例，3 项）：CLI 用法横幅、SCTP 服务端 socket 路径（无崩溃）、
  产物内静态链入 libsctp 符号。
- **test_ohos/run_ohos_test.sh**（鸿蒙专项，5 项）：aarch64 ELF、宿主路径泄漏、libsctp 符号、
  SCTP 协议栈能力探测、CLI 横幅。

## 已知限制

HarmonyOS（HongMeng Kernel 1.12.0）内核未内置 SCTP 协议栈：`socket(IPPROTO_SCTP)` 返回
`EPROTONOSUPPORT(93)`，因此 tsctp 的端到端 SCTP 收发功能在无 SCTP 内核的设备上不可用
（编译期适配完整；在有 SCTP 栈的内核/机器上可直接使用）。
