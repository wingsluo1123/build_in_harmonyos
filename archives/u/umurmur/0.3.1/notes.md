# umurmur 0.3.1 适配笔记

## 当前阶段

已完成源码、语言、唯一性及依赖制品准入检查，并建立 Conan/CMake 配方。上游 v0.3.1 未提供自动化测试；AArch64 OHOS 预检、HarmonyOS PC 真机完整协议闭环及路径 B 三臂实验均已通过。

## 构建配置

- 构建系统：CMake
- 编译器：HarmonyOS clang 15
- TLS 后端：OpenSSL
- 共享内存监控接口及两个子模块工具：关闭

## 依赖版本

- `libconfig/1.8`
- `protobuf-c/1.5.1`
- `openssl/3.5.8.1`

## 已确认的构建问题

- 上游 `FindProtobufC.cmake` 返回 `include/protobuf-c`，而生成代码包含 `<protobuf-c/protobuf-c.h>`，导致重复目录；补丁改为查找完整相对路径并返回 include 根目录。
- Conan 的 OpenSSL 配置导出 `openssl::openssl` 目标，而上游只消费旧式变量；补丁优先使用导入目标，同时保留系统 OpenSSL 的变量回退路径。
- 官方 `v0.3.1` 标签中的 `src/version.h` 仍为 `0.3.0`；补丁同步版本字符串，避免 CLI 与 Mumble Version 帧错报。
- 非阻塞 TLS 握手前排队的 `Version` 首帧不会触发 `POLLOUT`，握手完成后也没有排空点；客户端若遵循服务器先发 Version 的顺序会与服务器互等。补丁在 `SSLready` 状态转换后立即排空发送队列，并复用同一队列排空函数。该最小补丁使用零上下文差异；配方显式调用 `git apply --unidiff-zero`，避免 patch-ng 把相邻的闭合括号错配。
- CMake 安装出的目标 ELF 没有 `.codesign`，即使文件模式允许执行，HarmonyOS PC 仍以 `EACCES` 拒绝加载；配方对最终安装文件原位签名并检查恰有一个 `.codesign` 段，避免签名中间产物而漏签交付文件。

## 测试状态

### 上游测试清点（R51）

对官方 `v0.3.1` 源码树逐项检索并检查构建系统注册信息：

| 清点项 | 数量 | 证据 |
|---|---:|---|
| `test/`、`tests/` 目录 | 0 | 源码树中不存在自动化测试目录 |
| CTest 注册 | 0 | 顶层及子目录 CMake 文件没有 `enable_testing()` 或 `add_test()` |
| `make check` 目标 | 0 | CMake 生成目标中没有 `check` 测试目标 |
| 上游测试运行器 | 0 | 源码树中不存在可执行测试入口 |
| 上游实际运行 | 0/0 | 无可运行的上游测试；没有以“缺环境”为由跳过任何项目 |

- 官方 `conan-verify` 退出码为 0；G0-G3 实际执行通过。生成报告中的 G4 标注未定位 package ID，L2/L4/L5 因此跳过；最终 ELF 的架构、动态闭包、签名、路径可迁移性及版本由消费者和真机检查补足。
- HarmonyOS PC 真机已通过 12 个端到端场景、31 项外部可观察断言：前台启动、服务端首帧、TLS 握手、最小合法 Protobuf-C 认证帧、同一 TLS 会话的 OCB 加密 UDP 回环、UDP 状态查询、异常帧拒绝、前台及守护模式 SIGTERM 与 PID 文件清理。其中 4 类是 HarmonyOS 目标端专项验证，不与其余场景重复计数。
- 路径 B 三臂实验已由仓库内复现脚本重跑：上游臂握手完成但首帧超时；将待发队列直接映射为 `POLLOUT` 的错误修复臂仍超时并产生空闲忙轮询；仅在 TLS-ready 转换点显式排空队列的修复臂正确发送首帧，空闲连接 1 秒测量为 0 CPU tick。单纯测试方法不作为知识，知识边界限定为非阻塞 TLS 状态转换与应用层发送队列调度契约。
- 默认配置从可执行文件位置解析为相邻的 `../etc/umurmur/umurmur.conf`，避免把构建机 Conan package folder 固化进二进制；同时关闭安装 RUNPATH，并在签名前剥离调试路径，保证包搬迁后仍可使用默认配置。
---

**编译结束**: 2026-10-12 16:37
**最终状态**: built
