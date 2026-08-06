# DPC++/SYCL lit 在 OHOS 的受限环境注入与工具链验证

状态：候选知识草稿。来源：intel-oneapi-dpcpp 2026.0.0_220，PR #4458。
本文记录真实已验证的方法和边界，不把未解决的评审意见或设备运行时缺口写成完成。

## 问题类别

Intel LLVM 的 SYCL 测试不是普通的父进程编译命令。生成的
sycl/test/lit.site.cfg.py 在加载主配置后，lit 以 dict(config.environment)
构造子测试进程。OHOS SDK 的 libcxx-ohos 和 sysroot 头路径若仅设置在
os.environ、extra_environment 或外层 shell，不能保证会进入每个 lit 子进程。

实际表现为 sycl/sycl.hpp 引用标准库后报：

    fatal error: algorithm file not found

该问题不能用全局 CPLUS_INCLUDE_PATH 粗暴解决。E075 已说明全局变量会使
pkg-config 将相关头路径当作系统路径过滤。这里需要的是仅影响 SYCL lit
子进程的受限环境变量。

## 可复用方案

1. 在 CMake 中引入默认空值的 SYCL_OHOS_INCLUDE，所以非 OHOS/Linux
   构建不改变行为。
2. 在 lit.site.cfg.py 的 load_config() 之后读取该变量。
3. 仅在变量非空时写入 config.environment 的 CPLUS_INCLUDE_PATH 和
   C_INCLUDE_PATH。
4. 传入 OHOS libc++、target sysroot 和通用 sysroot 的 include 序列；不要
   修改上游测试断言，也不要全局导出该变量。
5. 采用 -j1 与 --max-time 做分层运行，单独统计 PASS、FAIL、Unsupported、
   XFAIL，不能把未执行或硬件不可运行项目算作通过。

对应实现在：
archives/i/intel-oneapi-dpcpp/2026.0.0_220/patches/sycl-lit-ohos-include.patch。

## 验证数据

- include 修复前，algorithm 缺失类错误出现 51 次；受限注入后为 0。
- reduction_range_deduction 单测从 FAIL 变为 PASS。
- SYCL device compilation 从 0/2 变为 2/2 PASS。
- group_algorithms 从 0/1 变为 1/1 PASS。
- 包内 DPC++ clang++ --version 和
  -fsycl -fsycl-targets=spir64 -fsycl-device-only 均返回 0。

全量 lit 结果应继续以本库 notes.md 的 90,226 项去重总账为准：
PASS 37,667、FAIL 7,542、Unsupported 44,933、XFAIL 84。Unsupported
不是单一 GPU 原因，还包含缺少 Intel GPU/Level Zero/OpenCL runtime、
目标注册能力和测试前置条件；必须按实际类别披露。

## 关联的工具链迁移边界

| 问题 | 已采用的边界 |
|---|---|
| SYCL lit 头路径 | 仅向 config.environment 注入，不污染全局构建环境 |
| UR 的 glibc 扩展 | RTLD_DEEPBIND 不可用时降级；dlinfo 能力检测仍有评审意见，不能写成已完成的通用方案 |
| UR FetchSource/重依赖 | 已预置 tag/源码时避免不必要网络 fetch；用 FETCHCONTENT_SOURCE_DIR 和 OHOS_MIRROR 注入已核验输入 |

E217 已覆盖一般 CTest/GTest 与 FetchContent 测试迁移；本草稿补充的是
LLVM/SYCL 生成 lit 配置、设备阶段编译和 OHOS SDK 头路径的组合。E075
覆盖全局 include 环境变量与 pkg-config 的冲突；本草稿明确避免该做法。
musl-glibc-full-comparison-iso-posix.md 覆盖 RTLD_DEEPBIND 的能力差异；
本草稿不重复登记其接口表。

## 复用条件和限制

适用于 LLVM 派生项目、SYCL 测试或任何把 config.environment 复制到
lit 子进程的 OHOS C++ 测试场景。调用方必须提供实际 SDK libc++/sysroot
路径，并验证变量确实由 site 配置传给子进程。

它不提供 Intel GPU、Level Zero driver 或 OpenCL runtime；需要真实设备
运行时的 E2E 测试仍应标为 Unsupported/skip。它也不替代源码版本映射：
本库仍使用 Intel intel/llvm 的 nightly-2026-07-30 固定 commit
9084ec7d34d89b9b63613665f5bf8b9757566c58，Intel 尚未公开其与赛事
产品号 2026.0.0_220 的一一映射。
