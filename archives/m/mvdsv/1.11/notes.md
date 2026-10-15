# mvdsv 1.11 适配笔记

## 状态

已完成官方源码固定、语言与唯一性准入、OHOS AArch64 干净构建、Conan 消费者预检、HarmonyOS PC 真机运行及路径 B 三臂验证。当前状态为 `built`；尚未通过 release 上传，因此不标为 `published`。

## 源码与依赖

- 主源码：官方提交 `11166a7f2a12838198ba253baa316c215271e357`，SHA256 `655956b207a2ac72081c1ff2633c326a51e9a06a6afdd7f2ec9a5b973c932242`。
- 子模块：官方 `qwprot` 提交 `07a728526ebddb93804bb34d295872cc0e8128b7`，SHA256 `2dc784ffc9720434724d0afa4b088b41179fdb202e30a5f7ee11ca8dbd5ff337`。
- 上游声明无外部构建依赖；PCRE 源码随项目构建，`qwprot` 使用固定的官方子模块源码。
- 主体语言预检为 C，共 53 个 C 源文件，属于任务允许的 C/C++ 语言族。

官方 release 的 `source-with-submodules` ZIP 使用 CRLF，无法满足补丁零模糊应用门禁；配方改用同一 1.11 标签指向的官方提交归档，并单独固定官方子模块提交。两项来源均为上游官方 HTTPS 地址，不使用镜像或个人 fork。

## 构建与打包

- 构建系统：CMake。
- 编译器：HarmonyOS clang 15，目标 `aarch64-linux-ohos`。
- 官方 Worker 对用户进程数量限制较严；`Unix Makefiles` 生成器在 CMake 编译器探测中会经过递归 `make` 和 shell，曾在尚未编译项目源码时稳定失败于 `/bin/sh: can't fork - try again`。配方显式使用 Worker 已提供的 Ninja，并以单作业构建限制峰值进程数；没有跳过 CMake 编译器可用性探测。
- 上游以 CMake 内建 `UNIX` 选择平台源码；官方 worker 的 `CMAKE_SYSTEM_NAME=HarmonyOS` 不设置该变量。补丁定义 `MVDSV_POSIX` 为 `UNIX OR HarmonyOS`，并统一用于平台源码、CTest 注册和系统库选择，避免误编译 Windows 的 `sv_sys_win.c`/`sv_windows.c`。
- 禁用未提供的可选 CURL；使用上游内置 PCRE。
- 最终只打包 `bin/mvdsv` 与许可证。
- 最终 ELF 原位签名，恰有一个 `.codesign` 段；动态依赖仅为 `libc.so`，无 `RPATH/RUNPATH`，不包含 Conan cache 或 package folder 路径。

## 生产缺陷与修复

上游 `NET_SendTCPPacket_SV()` 在非阻塞 TCP 短写或 `EAGAIN` 后会保存 `outbuffer/outlen`，但事件循环 `NET_Sleep()` 只监听标准输入和 UDP 可读事件。若最后一个业务帧产生积压且之后不再入队，即使对端恢复读取，尾部也没有新的调度机会。

修复保留首次入队时的乐观发送；仅当队列仍非空时把该 TCP fd 加入写集合，写就绪后继续排空，清空即取消监听。排空函数对 `EINTR` 重试、对 `EAGAIN/EWOULDBLOCK` 保留队列、对其他错误标记连接失败。负 fd 或 POSIX 下 `fd >= FD_SETSIZE` 不进入 `FD_SET`，而是 fail-closed 标记连接待关闭。不能无条件监听通常可写的 socket，否则空队列会持续唤醒形成忙轮询。

QTV 握手采用发送不完整即终止连接的 fail-closed 策略，不经过待发队列，不属于本知识触发条件，也未用它替代队列回归。

## 上游测试清点（R51）

| 清点项 | 数量 | 证据 |
|---|---:|---|
| `test/`、`tests/` 目录 | 0 | 官方 1.11 源码没有自动化测试目录 |
| CTest 注册 | 0 | 上游 CMake 文件没有 `enable_testing()`、`include(CTest)` 或 `add_test()` |
| `make check` 目标 | 0 | 上游未提供 Make/Autotools 测试目标 |
| 上游测试运行器 | 0 | 源码树中没有可执行测试入口 |
| 上游实际运行 | 0/0 | 无适用上游测试，不存在以环境原因跳过的项目 |

## 新增验证

- 新增 7 个验证场景、25 项外部可观察断言，严格多于上游实测 0 项。
- `tcp_queue_test` 直接编译生产 `net_tcp_queue.c` 与 `net_tcp_stream.c`。可注入发送器确定性覆盖部分发送、`EINTR`、`EAGAIN`、fatal 和 fd 范围保护；真实非阻塞 `socketpair` 再完成原始滞留、错误修复忙轮询和正确修复三臂，验证 7000 字节不丢失、不重复、不重排。
- 测试构造真实 `svtcpstream_t` 链表，并直接调用 `NET_Sleep()` 复用的生产写集合注册和就绪排空函数。`NET_Sleep()` 中的两个调用点由源码审查与完整服务器目标编译覆盖；测试没有虚称直接执行整个 `NET_Sleep()`，也不声称只回退调用点会触发现有运行时断言。
- 安装制品消费者验证签名、可迁移 ELF 和 `mvdsv +quit` 启动输出。
- HarmonyOS 专项验证包括签名 ELF 被目标内核执行以及 `const.ohos.fullname` 身份断言。
- 完整地图加载和 QTV 客户端会话需要上游未分发的 Quake 数据；本次不把缺少授权数据的场景伪报为已运行。核心知识回归不依赖该数据，并调用同一生产队列及真实流链表事件接线实现。

详细结果和哈希见 `reports/test-report.md` 与 `reports/path-b-evidence.md`。
---

**编译结束**: 2026-10-14 18:46
**最终状态**: built
