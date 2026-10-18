# liggghts

LIGGGHTS®-PUBLIC —— 离散元法（DEM）颗粒仿真引擎，用于颗粒流、粉体、颗粒-流体耦合的
工业级数值模拟。支持 MPI 并行、多种接触模型（Hertz / Hooke / 黏结 / 热传导 / 磨损等）、
球形/多球/超二次曲面颗粒、网格壁面（STL/Tri/Tet）与颗粒插入（insert/pack、insert/stream）。

| 项 | 值 |
|---|---|
| 上游 | https://github.com/CFDEMproject/LIGGGHTS-PUBLIC |
| 许可证 | GPL-2.0-or-later |
| 构建系统 | 手写 Makefile（LAMMPS 风格 src/Makefile + src/MAKE/Makefile.mpi） |
| 已适配版本 | 3.8.01（上游 3.8.0 的适配修订） |
| 产物 | `bin/lmp_mpi`（MPI 并行 DEM 求解器，可单进程运行） |

## 版本说明

上游公开版本号是 **3.8.0**（`src/version_liggghts.txt`、`release-notes.txt` 均为 3.8.0，
GitHub 上也没有 3.8.01 标签）。平台任务（id 8465）指定版本号为 `3.8.01`，
因此本配方按 R37 以「上游版本 + 适配修订」发布为 `liggghts/3.8.01`。

## 适配要点

- 手写 Makefile：构建变量由 Conan 显式提供（编译器取 `tools.build:compiler_executables`，
  依赖参数取各依赖的 `cpp_info`），不依赖 shell 环境变量。
- `SHELL` 显式传给 make：`src/Makefile` 写死了 `/bin/bash`（OHOS 镜像无该路径）。
  配方优先取 `CONFIG_SHELL`，未设置时按存在性挑选可用 shell，取不到则显式报错（R33）。
- 模型包通过编译宏开启（`SUPERQUADRIC_ACTIVE_FLAG`/`NONSPHERICAL_ACTIVE_FLAG`），
  与上游 `Makefile.auto` 的默认配置一致；超二次曲面需要 boost 头文件。
- 未启用 VTK 输出：已发布的 OHOS `vtk/9.4.1` 未启用 MPI，缺少 `vtkMPIController`
  （ParallelMPI 模块），而 LIGGGHTS 的 `dump custom/vtk` 等样式依赖它。
  详见 `3.8.01/notes.md` 的证据与影响分析。

## 目标平台

HarmonyOS PC / OHOS 6.0 / aarch64 / clang 15 / libc++，原生构建（CI worker 上 build = target）。