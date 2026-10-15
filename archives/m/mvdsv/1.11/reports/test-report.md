# mvdsv 1.11 测试报告

> 测试日期：2026-10-14
> 目标环境：HarmonyOS PC aarch64，HongMeng Kernel 1.12.0，OpenHarmony-6.1.0.115
> 构建环境：HarmonyOS clang 15，Conan 2，OHOS 6.0 profile

## 测试摘要

| 类别 | 场景数 | 外部可观察断言 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|---:|
| 上游自动化测试 | 0 | 0 | 0 | 0 | 0 |
| 新增制品与行为验证 | 7 | 25 | 25 | 0 | 0 |

上游 1.11 没有测试目录、CTest 注册、`make check` 目标或测试运行器，实际上游测试分母为 0。新增测试使用 7 个场景、25 项外部可观察断言，严格多于上游实测；没有把构建成功或打印 `PASS` 计作行为测试。

## 执行结果

- OHOS AArch64 `conan create` 从官方主源码和官方 `qwprot` 固定提交开始，强制重建 `mvdsv/1.11`，打包和交叉消费者静态预检通过。
- 针对官方 CI 在 CMake 编译器探测阶段的 `/bin/sh: can't fork - try again`，真机干净复验确认 `-G Ninja` 保留并通过编译器 ABI/可用性探测，单作业完成 56 个构建步骤，CTest 1/1 与安装制品 test_package 均通过。
- 最终 `bin/mvdsv` 是 AArch64 OHOS PIE，动态依赖仅 `libc.so`，恰有一个 `.codesign` 段，无 `RPATH/RUNPATH`，不含 Conan cache 或 package folder 路径。
- 同一最终包在 HarmonyOS PC 上执行 `test_mvdsv.py`：文件/签名/路径检查、`mvdsv +quit` 退出码、1.11 版本、初始化信息、禁用 CURL 信息及系统身份断言全部通过。
- CMake 在 `CMAKE_SYSTEM_NAME=HarmonyOS` 且 `UNIX` 未定义的复现配置中选中 `sv_sys_unix.c`，没有生成 `sv_sys_win.c`/`sv_windows.c` 编译命令；`tcp_queue_test` 被构建并由 CTest 执行。
- 目标端队列测试通过可注入发送器确定性验证部分发送、`EINTR`、`EAGAIN`、fatal 与越界 fd fail-closed；真实 `svtcpstream_t` 链表和 socket 背压再验证原始滞留、空队列 128/128 次错误唤醒反例、7000/7000 字节完整有序送达及清空后 0 次额外事件。

真机最终摘要：

```text
MVDSV consumer passed: signed relocatable ELF + versioned server startup
tcp queue arms: scripted_short_write=1 scripted_eintr=1 scripted_eagain=1 scripted_fatal=1 fd_guard=1 original_stalled=1 false_fix_wakeups=128 fixed_bytes=7000 idle_wakeups=0
```

## 断言口径

- 安装制品消费者脚本：11 项制品/进程外部断言；不把 `readelf` 工具存在性这一环境前置条件计入。
- TCP 队列回归：14 个独立失败出口，覆盖注入式部分发送/`EINTR`/`EAGAIN`/fatal、fd 范围保护、socket 建立、确定性背压、原始滞留、真实流链表过滤与写集合注册、就绪排空、字节一致性以及空闲忙轮询反例。
- 7 个场景为：ELF 可执行性、签名与动态段、路径可迁移性、服务器启动、HarmonyOS 身份、TCP 队列正确推进、错误修复忙轮询反例。
- HarmonyOS 专项场景为最终签名 ELF 的目标内核执行与系统身份闭环；网络队列知识测试虽然也在真机运行，但不虚称为 HarmonyOS 独有语义。

## 测试边界

完整 QuakeWorld 地图启动和 QTV 客户端会话需要上游未分发的 Quake 数据文件。该场景没有运行，也没有记入通过数。路径 B 的生产缺陷位于 QTV TCP 队列和事件调度之间；回归直接编译并调用同一生产队列及真实 `svtcpstream_t` 链表接线实现，使用真实非阻塞 socket 背压，不依赖游戏数据。

## 证据哈希

```text
官方主源码归档      655956b207a2ac72081c1ff2633c326a51e9a06a6afdd7f2ec9a5b973c932242
官方 qwprot 归档    2dc784ffc9720434724d0afa4b088b41179fdb202e30a5f7ee11ca8dbd5ff337
最终真机 mvdsv ELF 803ccf726314468c7e6be844fa5a8680ad1f9a664352b25f2343925da77c7600
签名队列测试 ELF    fbc9507df628beec655dea7e8af710ee7364ac6b697228fe2ae4bbe0ce335e46
消费者测试脚本      6207f0f0b11bf30d5790f42e7dcd9402fe4cbbf47eb44cf65d687da1da7bc1c2
正式 W3 日志         6c380891e0751145b468025aba9f3fa1fb967997e339e9a7afb85fd06fda90f5
脱敏真机输出        665c66e7145e26bba43879f7aec7b048daa3fd864281786b36dd009a3d11c61e
```

原始构建日志、实验 ELF 和设备临时路径不提交；仓库保存可重建的配方、补丁、测试源码、命令、判定标准和本次输出哈希。
