# Manifold

Manifold 是一个专注于拓扑鲁棒性的 C++17 三维几何库，用于创建和操作「流形三角网格」（manifold triangle meshes），保证布尔运算等操作的数值稳定与拓扑正确。广泛用于 3D 打印/几何内核场景。

## 功能概述

- **网格布尔运算**：Union / Difference / Intersection 等布尔操作（Add/Subtract/Intersect/Split），保证输出拓扑流形（manifold）
- **CrossSection（2D）**：二维多边形裁剪与偏置（基于 Clipper2），支持 2D/3D 互转
- **Minkowski 操作**：MinkowskiSum / MinkowskiDifference（凸-凸 / 非凸-非凸）
- **SDF 建模**：从符号距离场（SDF）构造网格
- **凸包 / 平滑 / 属性插值 / 网格修复** 等几何处理能力
- **C FFI 绑定（manifoldc）**：提供 C 接口（含 execution context API），便于其他语言/API 集成

## OHOS 适配

- **构建系统**：cmake（C++17）。已在 HarmonyOS aarch64 环境验证，设备上原生构建。
- **依赖注入**：上游默认通过 FetchContent git clone 拉取 GTest / Clipper2，但 OHOS 真机无法从 GitHub git clone，因此配方关闭 `MANIFOLD_DOWNLOADS`，改由 Conan 提供依赖（并通过 `find_package` 命中）。上游 `find_package(... QUIET)` + FetchContent 回退的设计使 3.5.2 可零补丁接入；3.4.1 曾需补丁补 `include(GoogleTest)` 等构建细节。
- **可选特性**：`MANIFOLD_PAR`（TBB 并行）、`MANIFOLD_PYBIND`（Python/nanobind）、TRACY、ASSIMP、FUZZ 在 OHOS 上全部关闭，只构建核心库 + CrossSection + C 绑定 + 测试。
- **系统名**：不强制 `CMAKE_SYSTEM_NAME`（区别于 clipper2）：manifold 用 `gtest_discover_tests` 在构建期运行测试二进制，强制系统名会误判为交叉编译而禁用用例发现。
- **上游测试**：`MANIFOLD_TEST=ON`，`gtest_discover_tests` 将 GTest 用例注册为 ctest 条目，在配方 `build()` 内通过 ctest 完整执行并产出 `HMBS_UPSTREAM_TEST_RESULT` 证据。3.4.1 真机注册 318 条；3.5.2 为 427 个唯一 gtest 用例，static/shared 两种形态分别完整跑通（427 × 2 = 854，零修改零跳过），test_package 另附真实 API 消费测试与 OHOS ABI 专项检查（M0-M10）。
- **hmdfs 完整性**（3.5.2）：共享库变体启用 `CMAKE_SKIP_RPATH=ON`，规避 hmmac=use_task 对 install 期 RPATH 改写的拒载问题（详见 [knowledge/DRAFT-manifold-3.5.2-hmmac-so-rewrite-reject-skip-rpath.md](../../knowledge/DRAFT-manifold-3.5.2-hmmac-so-rewrite-reject-skip-rpath.md)）。

## 依赖关系

- **编译/运行依赖**：无第三方运行时依赖（libmanifold.so 仅依赖 libc / libc++_shared）；CrossSection 编译期链接 Clipper2（PRIVATE，pimpl 隔离，公共头不暴露 Clipper2）
- **测试依赖**：gtest（仅构建/测试期；3.4.1 用 gtest/1.17.0.2，3.5.2 用 gtest/1.17.0）
- **构建工具**：cmake（>= 3.18）、C++17 编译器（clang）

## 详细文档

- 3.4.1 版本笔记: [3.4.1/notes.md](3.4.1/notes.md)
- 3.5.2 版本笔记: [3.5.2/notes.md](3.5.2/notes.md)
- 3.5.2 上游测试声明: [3.5.2/test_package/MANIFEST.yml](3.5.2/test_package/MANIFEST.yml)

## 参考资料

- 官网/文档：https://manifoldcad.org
- 源码仓库：https://github.com/elalish/manifold
- 许可证：Apache-2.0
