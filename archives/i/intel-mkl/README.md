# intel-mkl (Intel oneAPI Math Kernel Library)

## 简介

intel-mkl（oneMKL）是 Intel 的**专有闭源**高性能数学库，提供经过深度优化的
BLAS / LAPACK / FFT（MKL-DFT）/ PARDISO 稀疏求解器 / 向量数学（VM）等接口，
支持 C/C++/Fortran 调用，是 Intel oneAPI Base Toolkit 的核心组件之一。

- **官方网站**: https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html
- **License**: Intel Simplified Software License（闭源，禁止源码分发）
- **交付形态**: 仅 Windows/Linux/macOS 的 x86_64 (Intel 64) 预编译二进制 + Intel GPU 后端

## 适配版本

- **版本**: 2025.1（对应 oneAPI 2025.1 中 oneMKL 版本）
- **状态**: 无法适配（failed）
- **适配路径**: 路径 B（贡献创新）— 无法适配分析（详见 `2025.1/PATH_B_ANALYSIS.md`）

## 为什么无法适配（OHOS）

1. **无源码**：intel-mkl 是 Intel 闭源商业产品，许可证禁止源码分发，Intel 从不发布
   源码 tarball。`init-build` 实测用官方产品页 URL 下载即失败（HTTP 403 Forbidden），
   该失败本身即关键证据。
2. **无 aarch64/OHOS 二进制**：Intel 仅发布 x86_64 与 Intel GPU 预编译二进制，从未发布
   ARM/aarch64 版本，更无 HarmonyOS/OHOS 版本。
3. **架构不匹配**：本环境目标为 `aarch64-unknown-linux-ohos`，即使拿到 x86_64 二进制
   也无法加载；MKL 内核依赖 x86 SIMD（SSE/AVX/AVX-512），无法移植。
4. **制品仓无交付**：ohpcd 制品仓 `conan list "*mkl*"` / `"intel*"` 均为 0 条，
   `conan list "intel-mkl/2025.1"` 报 Recipe not found；社区 conan-center-index 亦无
   intel-mkl 源码配方。
5. **开源 oneMath 不能替代**：oneMath 只是 SYCL 接口/分发层（默认后端就是闭源
   Intel oneMKL），aarch64 后端仅商用 ArmPL 或 NETLIB/OpenBLAS（仅 BLAS/LAPACK 子集），
   且构建强制要求 SYCL/DPC++ 工具链，OHOS 无此工具链。

完整证据链见 `2025.1/notes.md`。

## 参考赛事先例

- #1990 nccl：OHOS 无 NVIDIA CUDA → 无法适配
- #1906 intel-oneapi-dpcpp：Intel 工具链高难度

## 依赖

- 编译期/运行期：无（闭源二进制交付，无开源依赖链可建）

## 参考资料

- Intel oneMKL 产品页: https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html
- oneMath（原 oneMKL Interfaces，开源接口层，非 MKL 本身）: https://github.com/uxlfoundation/oneMath
