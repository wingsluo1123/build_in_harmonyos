# falcosecurity-libs 0.25.4 适配笔记

## 编译环境

- 构建系统: CMake 3.24+
- 编译日期: 2026-07-20
- 目标平台: OHOS 6.0 AArch64
- 编译器配置: Clang 15、libc++、C++17
- 状态: built

## 适配方案

仅构建 libscap 和 libsinsp 用户态库。CMake 配置关闭 Linux 内核驱动、现代 BPF、示例、基准测试和交叉编译期间不可运行的上游测试目标，并启用 `MUSL_OPTIMIZED_BUILD`。

第三方依赖使用上游 CMake 模块提供的固定版本及 SHA256，以 bundled 模式构建，避免依赖未发布的 Conan 包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初始化器误判为 Autotools | codeload URL 不带 `.tar.gz` 后缀 | 在 manifest 中明确指定 CMake 和 tar.gz |
| 2 | Conan `get()` 报 `BadZipFile` | 无扩展名 URL 被识别为 ZIP | 为 `get()` 显式指定 `falcosecurity-libs.tar.gz` 文件名 |
| 3 | 本地 G2 无法进入编译 | 当前 macOS 环境没有 CMake，也没有 `/data/service/hnp/bin/clang` OHOS 工具链 | 保留 partial 状态，需在 OHOS 构建环境继续运行 conan-verify |

## 源码修改

应用 `0001-ohos-use-non-linux-platform-stubs.patch`。OHOS Clang 同时定义 `__linux__`，而 CMake 平台名是 `HarmonyOS`；补丁让 libscap 在该组合下使用非 Linux 用户态平台桩，避免引用未参与构建的 Linux platform 实现。

应用 `0002-musl-shared-build-without-static-flag.patch`。上游 musl 优化默认全局加入 `-static`，会导致共享引擎链接动态 `scap_event_schema` 失败；共享构建保留 musl 兼容源码，但不再加入静态链接参数。

## Bundled 依赖

- oneTBB 2022.1.0
- jsoncpp 1.9.5
- RE2 2022-06-01
- valijson 1.0.2
- uthash 1.9.8
- zlib 1.3.1

## 验证结果

```text
G0: PASS
G1: PASS
G2: BLOCKED - /bin/sh: cmake: command not found
```

Conan 已成功完成配方导出、源码下载与 SHA256 校验、源码解压、工具链文件和 CMake 参数生成。消费者测试覆盖 API 版本兼容性、事件信息表和系统调用元数据三个断言。

## 后续验证

在具备 CMake 3.24+ 和 OHOS Clang 工具链的环境执行：

```bash
python3 scripts/ohc-run.py conan-verify falcosecurity-libs 0.25.4
```
