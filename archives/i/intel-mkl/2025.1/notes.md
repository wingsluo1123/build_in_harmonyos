# intel-mkl 2025.1 适配笔记

## 结论

**判定：无法适配（failed），适配路径：路径 B（贡献创新）— 无法适配分析**。intel-mkl
（Intel oneAPI Math Kernel Library / oneMKL）是 Intel **闭源商业二进制产品**，无公开源码
可编译；Intel 仅发布 x86_64 (Intel 64) 与 Intel GPU 的预编译二进制，**无 aarch64/ARM
版本、无 HarmonyOS/OHOS 交付**。OHOS 交叉工具链可用，但「无源码可交叉编译」是硬性前提
缺失，与编译器能力无关。完整路径 B 分析见 `PATH_B_ANALYSIS.md`。

## 编译环境

- 构建系统: 无（闭源二进制交付，无源码构建入口）
- 编译日期: 2026-08-10
- 编译器: aarch64-unknown-linux-ohos-clang 15.0.4（已确认可用，无源码可编译）
- 状态: failed
- Conan: 2.29.1（OHOS 适配版）
- profile: ci/conan/profiles/ohos-aarch64

## 上游交付形态（事实来源）

1. intel-mkl 许可证为 **Intel Simplified Software License**，属闭源商用软件，Intel 从不发布源码。
2. Intel 官方产品页：https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html
   该页面仅为产品信息页，非下载地址。
3. Intel 支持的硬件：**Intel 64 (x86_64) CPU 与 Intel GPU**（Arc / Iris Xe / Data Center GPU），
   Linux/Windows/macOS。官方系统需求**不含 ARM/aarch64、不含 HarmonyOS/OHOS**。
4. 全球开源打包体系佐证：conan-center-index（社区最大 recipe 集）**不存在 intel-mkl recipe**
   （1000 个目录中仅 intel-ipsec-mb / intel-neon2sse / clblast 与 Intel 相关），即业界从未把
   intel-mkl 作为源码包打包——因为它根本没有源码。

## init-build 实测记录（关键证据）

```bash
python3 scripts/ohc-run.py init-build intel-mkl 2025.1 \
  --url=https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html
```

输出（截断）：

```
ℹ️ 🚀 初始化编译: intel-mkl 2025.1
ℹ️   下载: https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html
❌   下载失败 (https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html): HTTP Error 403: Forbidden
❌ 下载失败
```

- 上游不存在可下载的源码包（产品页 HTTP 403，且 Intel 从不发布 MKL 源码 tarball）。
- 完整日志备份：`$HOME/tmp/intel-mkl-init-build.log`。
- 未生成 `.build-context-intel-mkl-2025.1`（下载失败早于上下文生成），无残留构建文件。

## 制品仓查询证据（W0）

| 查询 | 结果 |
|------|------|
| `conan list "*mkl*" -r=ohpcd` | 0 recipes（无匹配配方） |
| `conan list "intel*" -r=ohpcd` | 0 recipes |
| `conan list "intel-mkl/2025.1" -r=ohpcd` | ERROR: Recipe 'intel-mkl/2025.1' not found |
| 仓库 `archives/` | 无 intel-mkl 目录（本次新建 failed 归档） |
| `scripts/software-registry.yaml` | 无 mkl 条目 |
| `knowledge/graph/index.tsv` 及知识库 | 无 mkl/oneMath 条目 |

## 架构不匹配论证

- 本环境交叉工具链目标三元组：`aarch64-unknown-linux-ohos`（clang 15.0.4）。
- intel-mkl 仅提供 x86_64 预编译二进制。x86_64 ELF 与 aarch64-unknown-linux-ohos **架构不匹配**，
  无法加载/链接运行。
- MKL 内核深度依赖 x86 SIMD 指令集（SSE/AVX/AVX-512）与 Intel 专有微架构优化，不存在可移植的
  aarch64 源码实现（Intel 未开源、未移植）。
- 结论：①无源码；②无 aarch64 二进制；③无 OHOS 交付——三个前提全部缺失，交叉编译无从谈起。

## 轻量路径排除：oneMath 接口层为何不能替代 intel-mkl

oneMath（原 oneMKL Interfaces，UXL Foundation，Apache-2.0，https://github.com/uxlfoundation/oneMath）
**不能**作为 intel-mkl 的替代交付：

1. **oneMath 只是接口/分发层（selector），不是数学内核实现**。CMake 默认开启
   `ENABLE_MKLCPU_BACKEND=ON`——它默认的后端**就是闭源 Intel oneMKL 二进制本身**。
   真正执行 BLAS/LAPACK 计算的是后端库。
2. **aarch64 后端选项不可行**：
   - ArmPL（Arm Performance Libraries）：商用闭源，仅 ARM Linux，无 OHOS 支持；
   - NETLIB LAPACK / OpenBLAS：开源，但仅覆盖 BLAS（及部分 LAPACK）子集，**不含 FFT、
     PARDISO 稀疏求解器、向量数学（VM）等 MKL 核心功能**。
3. **构建强制要求 SYCL/DPC++ 工具链**：oneMath 官方构建说明明确要求 Intel oneAPI DPC++
   （`icpx`/`icx`）或 AdaptiveCpp；其 Host API 基于 `sycl::queue` 的 C++ 模板接口。
   OHOS **无任何 SYCL/DPC++ 工具链**（对应赛事先例 #1906 intel-oneapi-dpcpp，Intel 工具链高难度）。
4. **ABI 不兼容**：oneMath 提供的是 SYCL 队列式 C++ API，不是经典 BLAS/LAPACK Fortran-C ABI，
   无法作为现有链接 MKL 的应用的 drop-in 替代。

综上，oneMath 既无法在 OHOS aarch64 上构建（缺 SYCL 工具链），即便构建也只是接口壳，
无法提供 intel-mkl 的数学内核功能，不能作为替代交付。

## 赛事先例

| 先例 | 结论 | 与本库相似点 |
|------|------|--------------|
| #1990 nccl | OHOS 无 NVIDIA CUDA → 无法适配 | 上游闭源/受限分发 + 目标硬件平台缺失 |
| #1906 intel-oneapi-dpcpp | Intel 工具链高难度 | Intel 专有工具链在 OHOS 上不可用 |

intel-mkl 与两者同类：**闭源 + 仅 x86 交付 + OHOS/aarch64 无对应产物** → 判定无法适配。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 HTTP 403 | 上游无源码 tarball，产品页非下载地址 | 判定无法适配，按 failed 归档（本记录） |
| 2 | 制品仓无 mkl 配方 | Intel 闭源，全球无源码打包 | 无需修复；作为 W0 证据归档 |
| 3 | OHOS 无 aarch64 二进制 | Intel 不发布 aarch64/OHOS 版本 | 判定无法适配；记录缺失项 |

## 验证结果

- 无源码、无 OHOS/aarch64 二进制 → **无任何产物可测试**，测试数 0（skipped）。
- 无 conanfile.py / conandata.yml：ARCHIVE-SPEC 要求 conandata.yml 含源码 URL + SHA256，
  而 intel-mkl **不存在源码 URL/SHA256**，故无法生成可构建的 Conan 配方（与 prefixsuffix
  不同——后者有真实源码只是 configure 失败；intel-mkl 连源码都不存在）。
- 未提交 git、未 push（按任务要求仅做本地归档）。

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/i/intel-mkl/manifest.yaml` | 软件级元数据 + 版本索引（status: failed） |
| `archives/i/intel-mkl/README.md` | 软件描述 + 无法适配说明 |
| `archives/i/intel-mkl/2025.1/manifest.yaml` | 版本级编译元数据（含 failure_reason） |
| `archives/i/intel-mkl/2025.1/notes.md` | 本文档 |
| `archives/i/intel-mkl/2025.1/reports/test-report.md` | 测试报告（skipped，0 用例） |

## 下一步建议

1. 若鸿蒙生态需要 BLAS/LAPACK/FFT 高性能数学库，建议适配**开源替代**：
   - OpenBLAS（BSD 许可，aarch64 原生支持，BLAS/LAPACK）
   - NETLIB LAPACK（BSD 风格，参考实现）
   - pocketfft（FFT）
   - Eigen（C++ 模板库，头文件，aarch64 无压力）
2. 若坚持要 oneMath 分发层：需先移植 SYCL/DPC++ 工具链到 OHOS（对应 #1906 高难度方向），
   并选择 OpenBLAS/NETLIB 后端——工作量与价值不成比例，不建议。
3. 知识图谱：可考虑新增 E-entry 记录「闭源仅 x86 二进制产品（无源码）在 OHOS 的判定流程」
   供后续同类软件（如 NVHPC、cuDNN 等闭源变体）复用。
