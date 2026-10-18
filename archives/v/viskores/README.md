# Viskores

Viskores 是科学可视化的 C++ 数据并行算法框架，提供数组与网格模型、worklet 调度、
过滤器、数据源、VTK 文件读写及软件渲染。

本次 HarmonyOS PC 配置交付默认 Serial CPU 后端、所有标准库及软件渲染。
使用原始上游 CMake 导出目标，可通过 `find_package(Viskores 1.1 CONFIG REQUIRED)`
消费 `viskores::cont`、`viskores::filter`、`viskores::io`、`viskores::source`、
`viskores::rendering` 等目标。完整组件关系保留在包内，无三方 Conan 依赖。

OHOS SDK 编译器保持真实 OHOS 目标 ABI，CMake 使用 Linux 平台规则以保留 ELF
SONAME、版本链接与安装规则。模板编译显式限制 Ninja 并发，不修改共享 profile。
CUDA、Kokkos、MPI、TBB、OpenMP、ANARI、HDF5 均保持上游默认关闭；不声明这些可选能力。

上游：[Viskores](https://github.com/Viskores/viskores)。许可 BSD-3-Clause。
版本特定的测试结果、证据与重跑方法见 `1.1.1/notes.md` 及 `1.1.1/reports/`。
