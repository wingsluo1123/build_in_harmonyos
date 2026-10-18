# oRTP：检查真实测试框架产物，补齐 CMake target 后运行原始 tester

状态：待审核知识草稿。来源 [PR !15662](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15662)，修复候选 `fb71955932916f66582fcb0a73773d42e8319f8d`。

## 问题与修复

旧 CI #92908 测试 `90261cae` 并通过 consumer，但没有执行原始 ortp_tester。真实检查 bctoolbox/5.3.115 包后发现，`libbctoolbox-tester.a` 与 tester.h 已存在，缺的是 CMakeDeps 导出的测试 target，不能继续以“测试框架不可用”为由关闭上游测试。

本版 0005 补丁在 `bctoolbox-tester` 不存在时创建 `UNKNOWN IMPORTED` target，IMPORTED_LOCATION 指向实际归档，INTERFACE_INCLUDE_DIRECTORIES 传递真实头文件路径列表，INTERFACE_LINK_LIBRARIES 使用 `bctoolbox;bcunit::bcunit`。BCUnit 为真实依赖 bcunit/5.3.113，不是 stub。缺失的 advisory compile-flags 宏沿用 ENABLE_STRICT=OFF 的兼容处理，不替换测试断言。

开启 ENABLE_UNIT_TESTS，构建后运行原始 ortp_tester。执行环境必须同时包含本轮 `build/src` 的 libortp.so 和所有依赖库路径；只加入依赖包会漏掉当前构建的 DSO。测试非零直接失败。src/tests 的网络收发工具仍关闭，不计为已执行。

## 真实证据及覆盖边界

HarmonyOS 6.1.0.117 arm64、Clang 15、OHOS Conan 2.29.1、Release 默认共享配置。完整原始上游 tester **1 通过、0 失败、0 跳过**；安装后 API consumer **1 通过、0 失败、0 跳过**。上游唯一用例 FEC/first 只断言 NULL 指针，不能声称覆盖 FEC 算法。consumer 调用初始化、调度器、会话配置、本地回环绑定与销毁，不证明 RTP 收发互通。

原始 W3 日志 SHA256 `2d92a85b0878b89dd531527e94a4ee891ffbd2cb6a735571498d6425b57ada2a`；正向 Conan 日志 SHA256 `18ff954a0b87515cf39f6f293cacf474654bb1ee6d0cc433c16b098c0d1b1af0`，原件在维护工作区 `.tmp/pr-monitor/ortp-w3-evidence/evidence/`。补丁顺序、CMake include 列表、漏掉 build/src 的失败尝试也保留，未混入通过数。破坏产物的负向检查按预期失败，不算额外上游用例。

## 区分 CI 环境与代码回归

后续 CI #93364 测试 `fb719559`，在 CMake 最小编译器探测阶段报 `/bin/sh: Resource temporarily unavailable`，尚未构建或运行 tester。此记录只能说明远端节点启动进程失败，不能撤销原生证据；仅凭该失败构建也不能宣称新提交远端 CI 已通过。旧提交绿灯同样不能证明新 head 通过。制品仓查询错误不能证明测试框架未发布。

## 查重

检索正式图谱与草稿的 bctoolbox-tester、BCTOOLBOX_TESTER_LIBRARY、BCUnit，未见本精确元数据缺口的修复案例。E298 覆盖显式运行时环境，E327 覆盖测试计数边界；本例引用这两条，不另造运行时路径或测试分母通用条目。

## 补充案例：远端 CI95092 实际执行原始 tester

2026-10-16，[CI95092](https://ohpcd.atomgit.com/ci?id=95092) / Buildbot109411 在 CI-028 成功完成（exit 0）。请求修订为 `1fb7f327d385ecf6b7eed77604810b426827dcec`，包含源修复 `fb71955932916f66582fcb0a73773d42e8319f8d`。日志实际构建并运行原始 ortp_tester：FEC/first **1 通过、0 失败、0 跳过**；安装后 consumer **1 通过、0 失败、0 跳过**，破坏包的负向依赖检查也通过。L0/L1/L4/L5 通过；L2 CLI 检查跳过，与上游测试计数分开。Conan 的“Skipped binaries: bcunit”不是跳过测试。

完整原始日志：维护工作区 `pipeline_logs/pr15662-conan-build-test-20261016-build95092-full.log`，SHA256 `52e5d7954784d9be477e1ce116c9b060b1d4118c1421cfd4904a8804f9449af1`。这次独立 CI 验证补充本条 imported target 方案的证据，不再创建重复条目；仍建议与本草稿合并，运行时环境及计数边界分别关联 E298、E327。

证据边界：Buildbot 的 ci_revision 表示请求 SHA；worker 应用实时 PR diff，没有完整检出内容摘要，不能把它冒充源内容校验和。该 CI 成功不证明制品已发布；制品仓仍需独立查询。此次仅补文档，未重新运行本地代码测试；上述结果属于 CI95092 的请求修订，不自动赋给后续文档提交。FEC/first 的占位断言、静态构建及 RTP 收发互通限制仍有效。
