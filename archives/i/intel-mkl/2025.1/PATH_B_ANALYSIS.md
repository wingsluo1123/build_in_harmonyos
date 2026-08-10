# intel-mkl 2025.1 路径 B 无法适配分析

更新日期：2026-08-10

- 路径 B 类型：无法适配
- 认领 Issue：#2004（intel-mkl 鸿蒙PC适配申请）
- 路径 B Issue：#2004
- 对应 PR：待提交
- 当前结论：intel-mkl（Intel oneAPI Math Kernel Library / oneMKL）为 Intel 闭源商业二进制
  产品，无公开源码可编译；Intel 仅发布 x86_64 (Intel 64) CPU 与 Intel GPU 预编译二进制，
  无 aarch64/ARM 版本、无 HarmonyOS/OHOS 交付，判定在 OHOS PC 平台无法适配。

## 已完成范围

无。intel-mkl 未进入编译流程：上游不存在可下载源码包（`init-build` 实测下载返回
HTTP 403 Forbidden），Intel 亦从未发布 aarch64/OHOS 预编译二进制，故无任何可交付产物。

## 根因分析

intel-mkl 的核心价值在于为 BLAS/LAPACK/FFT/PARDISO/向量数学等提供经过 Intel 微架构
深度优化的内核。上游关键特性直接依赖：

- Intel 专有闭源实现（Intel Simplified Software License 禁止源码分发）；
- x86_64 指令集（SSE/AVX/AVX-512）与 Intel 专有微架构优化；
- 仅 Windows/Linux/macOS 平台的 x86_64 CPU + Intel GPU 二进制交付。

HarmonyOS PC（aarch64）SDK 不提供这些二进制，Intel 亦无 aarch64/OHOS 发布物；MKL 内核
依赖的 x86 SIMD 优化不存在可移植的 aarch64 源码实现。这些覆盖的正是该库的全部核心
功能，不是可通过少量条件宏替换的边缘代码。

## 已尝试方案及结果

1. 直接构建上游源码：`init-build intel-mkl 2025.1 --url=<Intel 产品页>` 在下载阶段
   返回 HTTP 403 Forbidden——上游不存在可下载源码包（日志备份于
   `$HOME/tmp/intel-mkl-init-build.log`）。
2. 制品仓查询：ohpcd 制品仓 `conan list "*mkl*"` / `"intel*"` 均为 0 条；
   conan-center-index 亦无 intel-mkl recipe（仅 intel-ipsec-mb / intel-neon2sse /
   clblast）——全球开源打包体系中不存在 intel-mkl 源码包。
3. 架构验证：目标交叉工具链为 `aarch64-unknown-linux-ohos`（clang 15.0.4，可用），
   但 x86_64 ELF 二进制与 aarch64 目标架构不匹配，即使获得二进制也无法加载。
4. 开源替代评估（oneMath，原 oneMKL Interfaces）：仅是 SYCL 接口/分发层（selector），
   默认后端就是闭源 Intel oneMKL 本身；aarch64 后端仅商用 ArmPL 或 NETLIB/OpenBLAS
   （仅 BLAS/LAPACK 子集，无 FFT/PARDISO/VM）；构建强制要求 SYCL/DPC++ 工具链
   （OHOS 无，对应赛事先例 #1906 intel-oneapi-dpcpp）；Host API 为 `syql::queue`
   C++ 模板接口，非经典 BLAS Fortran-C ABI，无法 drop-in 替代。
5. 提供空桩：会令数学内核功能全部静默失效，违反实质适配和测试要求（R6/R40）。

## 测试边界

- 上游自动化功能测试：0 个（闭源产品，Intel 不发布源码与测试套件）。
- 上游数学内核行为：无 aarch64/OHOS 二进制可执行，无法运行或声明通过。
- 新增测试：0 个（无源码、无二进制，无任何产物可测试）。
- 未验证且不可伪记为通过：BLAS/LAPACK/FFT/PARDISO/向量数学全部内核。

## 解除条件

只有在以下任一条件满足时，intel-mkl 才可能在 OHOS 平台继续适配：

1. Intel 发布 aarch64/OHOS 版本的 oneMKL 二进制（当前无任何官方计划/发布物）；
2. 赛事明确允许以「oneMath 接口层 + 开源后端（OpenBLAS/NETLIB）」重新定义交付形态
   （此时应作为新软件 oneMath 单独适配，而非 intel-mkl 产品本身）；
3. 鸿蒙生态先行引入 SYCL/DPC++ 工具链（对应 #1906 intel-oneapi-dpcpp 高难度方向），
   并选择 OpenBLAS/NETLIB 作为 oneMath 后端——工作量与价值不成比例，不建议。

当前提交不把任何测试通过写成数学内核通过，如实判定无法适配。
