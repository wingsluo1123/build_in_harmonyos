# kdsoap-ws-discovery-client 0.4.0 HarmonyOS 适配笔记

## 编译环境

- 目标设备：HarmonyOS PC 6.0，aarch64 原生设备
- 编译器：clang/clang++ 15.0.4
- 构建工具：CMake 4.1.2、Conan 2.29.1、Ninja/Make
- Conan 配置：`ci/conan/profiles/ohos-aarch64` 同时用作 build 与 host profile
- 日期：2026-10-11
- 状态：built；Conan G2 与 W3 本地 CI 均通过

## 编译配置

配方使用 `CMakeDeps`、`CMakeToolchain` 和 `VirtualRunEnv` 构建 Qt6、KDSoap 与 ECM 依赖，开启上游测试与共享库，关闭 QCH 和 RPATH。HarmonyOS 的 Conan OS/架构/clang 设置保持 OHOS/aarch64；`CMAKE_SYSTEM_NAME=Linux` 仅用于让 CMake 选择可用的平台模块，对应已有知识 E092。运行上游 CTest 时，环境同时包含依赖包 `lib/` 与 ECM 实际输出目录 `build_folder/bin`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | 上游 CTest 找不到 `libKDSoapWSDiscoveryClient.so.0` | ECM 将构建树共享库和测试程序放入 `build/Release/bin`，但运行环境最初只加入 `build/Release/lib` | 把 `build_folder/bin` 加入 `LD_LIBRARY_PATH`，继续关闭 RPATH；知识草稿 E545 |
| 2 | 独立消费者加载导出配置时报 `Unknown CMake command find_dependency` | 上游 CMake 配置模板调用 `find_dependency()` 前没有载入 `CMakeFindDependencyMacro` | 0001 补丁在首次调用前包含宏模块；知识草稿 E546 |
| 3 | 消费者保存收到的服务对象时编译报 `member access into incomplete type WSDiscoveryTargetServiceData` | 类含有指向前置声明数据类的 `QSharedDataPointer`，但隐式复制赋值在消费者翻译单元中实例化 | 0002 补丁声明复制赋值，并在私有数据类型完整的 `.cpp` 中默认实现；知识草稿 E547 |

## 依赖版本

- 运行依赖：`qtbase/6.11.1`、`kdsoap/2.3.0`
- 构建依赖：`extra-cmake-modules/6.29.0`

## 发现与知识

- ✅ CMake 平台模块配置沿用 E092：CMake system name 设为 Linux，Conan 目标仍为 HarmonyOS aarch64。`knowledge_ref: E092`
- ✅ ECM 的构建树库位于 `bin/`；关闭 RPATH 时 CTest 运行环境须包含该目录。`knowledge_ref: E545`
- ✅ 导出的 CMake Config 应在调用 `find_dependency()` 前包含 `CMakeFindDependencyMacro`。`knowledge_ref: E546`
- ✅ 使用前置声明 PIMPL 的 `QSharedDataPointer` 类型时，复制赋值应在数据类型完整的实现文件中定义。`knowledge_ref: E547`

## 最终验证

- `conan create`：HarmonyOS PC 6.0 aarch64 构建、安装并运行消费者测试，退出码 0。
- 上游 CTest：1/1 测试目标通过；源文件注册的 4 个 QtTest case 覆盖 Probe/Resolve 发送及 ProbeMatch/ResolveMatch 处理。
- Conan `test_package`：2/2 通过（安装后 API 消费者、HarmonyOS loopback SOAP ProbeMatches 行为测试）。
- W3 本地 CI：1/1 包通过；L0/L1/L5 通过，L2 因纯库没有 `bin/` 跳过。L4 的非阻塞扫描 warning 是把 0001 补丁上下文文件名 `KDSoapWSDiscoveryClientTargets.cmake` 中的子串 `gets` 误认为危险函数调用；补丁未调用 `gets`、`strcpy`、`sprintf` 或 `strcat`。
- 原始日志 SHA-256：`conan-create.log`=`238ec3a0ab429434d1e33462a892ae3fe643d2489e511d38c403a602719c3f01`；`w3-local-ci.log`=`e79e0d8fe661d162848de78444a25a58c36ce93d5d2541db093efe7c0474e174`。
