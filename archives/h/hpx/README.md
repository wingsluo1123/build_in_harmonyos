# hpx

## 简介

HPX（The C++ Standards Library for Parallelism and Concurrency）是一个通用的
C++ 并行与分布式运行时系统，为任何规模的并行/分布式应用提供统一的编程模型
（轻量级线程、futures、AGAS 全局地址空间、并行算法等）。

- 主页: https://hpx.stellar-group.org/
- 源码: https://github.com/TheHPXProject/hpx （原 STEllAR-GROUP/hpx 已迁移）

## OHOS 适配（1.11.0，路径 C 高难度挑战）

本版本为 HPX 在 HarmonyOS PC（aarch64，OHOS 6.0，clang 15 / libc++ / C++17）上的首次适配：

- **协程上下文切换后端重路由**：aarch64 上 HPX 默认启用 Boost.Context，但 OHOS 无可用
  Boost.Context（registry boost 包显式排除 context，且无 OHOS aarch64 asm）。
  适配改用上游现成的 POSIX ucontext 后端，并由 `libucontext/1.5.2` 提供 OHOS musl
  缺失的 ucontext 实现（含 unprefixed 弱符号）。4 个平台补丁仅改变 OHOS 行为
  （上下文选择分支 + musl 缺失声明 + 跳过 x86 汇编单元 + 栈大小定义同步到 POSIX 分支）。
- **Asio 官方源注入**：HPX 无条件依赖 standalone Asio（≥1.12），registry 暂无 asio 包；
  经 conandata 下载官方 `chriskohlhoff/asio` tag 归档（`asio-1-21-0`，与 HPX
  `HPX_WITH_ASIO_TAG_DEFAULT` 对齐），以 `FETCHCONTENT_SOURCE_DIR_ASIO` 本地源注入，
  configure 阶段零网络访问。
- **Boost 选型**：选用 `boost/1.85.0` —— registry 中唯一提供完整 Boost 头文件树的包
  （HPX 需要 accumulators/spirit/phoenix/parameter；1.90/1.91 组件构建缺这些头）。
- **zlib 版本统一**：hwloc 子树与 boost 对 zlib 版本要求不一致，按 R37 统一到修复版
  `zlib/1.3.1.1`（同上游源码，ABI 一致，两包已发布二进制保持有效）。
- **pkgconfig**：HPX 1.11 的 pkgconfig 生成与 CMake ≥4 不兼容（`file(GENERATE)` 中的
  目标上下文相关生成器表达式），`HPX_WITH_PKGCONFIG=OFF`；OHOS 消费者经 CMake/Conan 使用。

## 依赖

- boost/1.85.0
- hwloc/2.14.0
- libucontext/1.5.2
- zlib/1.3.1.1
- asio-1-21-0（官方 tag 归档，经 conandata `deps:` 注入，非 conan 依赖）

## 功能验证

```bash
# 消费者测试（真实 HPX runtime：hpx::async / future continuation /
# promise + hpx::thread 挂起恢复；R53 鸿蒙断言：AArch64 ELF + runtime 启动）
conan create archives/h/hpx/1.11.0 --build="hpx/*"
```

上游测试（CTest，约 1300 个测试源文件 / 约 1180 条注册）：完整套件超出 CI 预算，
在 HarmonyOS PC 上执行与本次适配直接相关的模块子集，逐项归因见
`archives/h/hpx/1.11.0/reports/test-report.md`（R51 三步法）。

## 许可

BSL-1.0
