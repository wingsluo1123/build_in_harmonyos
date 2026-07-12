# fast_float 7.0.0 HarmonyOS PC 适配笔记

## 编译环境

- 构建系统：CMake
- 编译日期：2026-07-12
- 编译器：Clang 15.0.4
- 目标平台：HarmonyOS PC arm64
- 状态：built（已通过本地验证，尚未上传制品仓）

## 适配内容

fast_float 上游是 header-only C++ 浮点解析库。本次在保留头文件和 CMake 配置交付的基础上，新增 `fast_float` 命令行工具：

```bash
fast_float --version
fast_float 3.1416
fast_float 1.5 2.75
```

适配通过 `0001-CMakeLists.txt.patch` 增加可选的 `FASTFLOAT_TOOLS` 构建目标。命令行源码由 Conan 配方通过 `export_sources()` 导出到源码树的 `tools/` 目录，不修改上游测试源码。

## Conan 配方

```bash
python3 scripts/ohc-run.py conan-verify fast_float 7.0.0
python3 scripts/ohc-run.py finish fast_float 7.0.0 built
```

配方配置：

- `FASTFLOAT_TEST=OFF`：Conan 消费者测试由 `test_package` 独立执行
- `FASTFLOAT_BENCHMARKS=OFF`
- `FASTFLOAT_INSTALL=ON`
- `FASTFLOAT_TOOLS=ON`

## 依赖

无外部 Conan 依赖。构建要求 CMake >= 3.9 和支持 C++11 的编译器。

## 验证结果

| 检查项 | 结果 |
|---|---|
| `conan create` | PASS |
| Conan G0-G4 | PASS |
| Conan L2/L4/L5 | PASS |
| W3 本地 CI 模拟 | PASS |
| `fast_float::from_chars` 消费者 API 测试 | PASS |
| `fast_float --version` | PASS |
| `fast_float 3.1416` | PASS |

`test_package` 实质调用 `fast_float::from_chars`，校验错误码、输入完整消费和解析精度；同时执行命令行工具验证版本输出与数值解析。

## 源码与补丁

- 官方源码：`https://github.com/fastfloat/fast_float/archive/refs/tags/v7.0.0.tar.gz`
- SHA256：`d2a08e722f461fe699ba61392cd29e6b23be013d0f56e50c7786d0954bffcb17`
- 补丁：`patches/0001-CMakeLists.txt.patch`，增加命令行构建和安装目标
- 新增源码：`fast_float_cli.cpp`，由配方导出到 `tools/fast_float_cli.cpp`

## 已知说明

`clean-verify` 的旧式自动检测会误判该 CMake 项目为 configure 流程并报告 exit 127；阻塞门禁使用的 Conan 干净构建及 W3 本地 CI 均已通过。软件无系统同名库冲突，交付物包括头文件、CMake 配置和命令行可执行文件。
---

**编译结束**: 2026-07-12 12:45
**最终状态**: built
