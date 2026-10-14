# uMurmur

uMurmur 是一个兼容 Mumble 协议的轻量语音通信服务器。它使用 TLS 承载控制消息，使用 Protobuf-C 编解码协议帧，并为语音数据提供 UDP 通道。

## 功能概述

- 提供 Mumble 控制协议的 TLS/TCP 服务。
- 使用 Protobuf-C 编解码认证、会话和通道消息。
- 使用认证加密的 UDP 通道承载实时数据，并在同一端口提供状态查询。
- 支持前台运行、守护进程、PID 文件与信号退出。

## HarmonyOS 适配

- 使用 HarmonyOS clang 和 Conan CMake 工具链构建 `umurmurd`。
- 使用制品仓中已发布的 `openssl`、`libconfig` 与 `protobuf-c`。
- 对最终安装的 ELF 原位签名，并验证交付物只包含一个 `.codesign` 段。
- 目标端验证采用非特权端口与临时配置，不依赖系统服务管理器。
- 消费者测试联合覆盖 TLS 控制连接、协议帧边界、同一会话的加密 UDP 路径、信号退出与 PID 文件清理。

## 依赖关系

- 运行与编译依赖：OpenSSL、libconfig、protobuf-c。
- 构建系统：CMake；编译器为 HarmonyOS clang。

## 参考资料

- 上游仓库：https://github.com/umurmur/umurmur
- 上游版本：https://github.com/umurmur/umurmur/releases/tag/v0.3.1
