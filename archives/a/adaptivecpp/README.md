# adaptivecpp — 鸿蒙 PC 适配说明

AdaptiveCpp 是一个面向 C++ 的**独立异构计算编译器**，支持三种编程模型：
SYCL、C++ 标准并行（stdpar）、HIP/CUDA。它把 C++ 代码编译成可在 CPU/GPU
上运行的代码，是社区驱动的、厂商中立的异构编程工具链。

- 上游：https://github.com/AdaptiveCpp/AdaptiveCpp
- 许可证：BSD-2-Clause
- 本次适配版本：25.10.0

## 鸿蒙 PC 适配要点

### 构建方式：真机原生编译

沿用官方仓库 clang / llvm / onetbb 等 CMake 类配方的通行做法——
**不设置 CMAKE_SYSTEM_NAME**，保持 CMAKE_CROSSCOMPILING=False，
让 llvm-tblgen 等 LLVM 宿主工具能够原生构建并运行。交叉编译模式下这些
宿主工具无法执行，是 LLVM 类项目最难绕开的障碍。

### 依赖：clang/22.1.8 提供 clang 前端库

AdaptiveCpp 的编译能力集中在一个 **Clang 插件（acpp-clang）** 中——
它负责在编译期拆解 SYCL 内核并下发到各后端。插件必须链接 clang 前端库，
因此需要能提供 `ClangConfig.cmake` 与 `libclang-cpp.so` 的依赖包。

制品仓中的 `clang/22.1.8` 正好满足：

```text
lib/libclang-cpp.so            <- 插件链接目标
lib/libLLVM.so                 <- 聚合动态库
lib/cmake/clang/ClangConfig.cmake   <- find_package(Clang) 入口
lib/cmake/llvm/LLVMConfig.cmake     <- find_package(LLVM) 入口
lib/clang/22/include/          <- clang 内置头
include/clang/                 <- clang C++ 开发头
```

> 注意：`llvm/20.1.0` **不能**作为本包的依赖——它以
> `LLVM_ENABLE_PROJECTS=""` 构建，不含任何 clang 内容。

### 后端选择：仅 CPU（OpenMP）

鸿蒙 PC 上没有 CUDA / ROCm / Level Zero 运行时，因此配方显式关闭这些后端，
只保留 CPU 后端。OHOS SDK 自带 `libomp.a` / `libomp.so` 与 `omp.h`，
OpenMP 交叉编译已实测通过，CPU 后端本身没有平台障碍。

## 版本与风险

上游对 LLVM 版本有硬性约束：主版本必须落在 15..20，高于 20 会直接报错。
制品仓中 clang/20.1.8 落在该区间但包已损坏，可用的 clang/22.1.8 超出上限，
因此配方开启 `ACPP_EXPERIMENTAL_LLVM=ON`。

**LLVM 22 与 AdaptiveCpp 25.10.0 的兼容性未经上游测试**，是本任务首要验证项，
详见 `25.10.0/notes.md` 第六节的备选路线。

## 版本列表

| 版本 | 状态 | 说明 |
|---|---|---|
| 25.10.0 | recipe_only | 配方与消费者测试已产出，构建与运行测试待真机 |
