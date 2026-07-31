# libxslt 1.1.45.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 `ohc-run.py init-build libxslt 1.1.45.2` 初始化构建环境并下载源码
2. 使用标准 CMake 构建系统，通过 `CMakeToolchain` 生成工具链配置
3. 关键 cmake 选项：
   - `-DBUILD_SHARED_LIBS=OFF` — 静态构建（系统同名库隔离，R26）
   - `-DLIBXSLT_WITH_PROGRAMS=ON` — 启用 xsltproc 命令行工具构建
   - `-DLIBXSLT_WITH_CRYPTO=OFF` — 禁用加密支持
   - `-DLIBXSLT_WITH_PYTHON=OFF` — 禁用 Python 绑定
   - `-DLIBXSLT_WITH_TESTS=OFF` — 禁用上游测试
4. 执行 `cmake.configure() → cmake.build() → cmake.install()` 完成构建和安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS SDK 缺少 `llvm-ranlib` | OHOS SDK 工具链不包含 `llvm-ranlib`，导致 CMake 静态库归档失败 | 在 `CMakeToolchain` 中显式指定 `-DCMAKE_RANLIB` 指向 OHOS SDK 的 `llvm-ranlib` |
| 2 | 旧版本 conanfile.py 使用手动 toolchain 解析和 ELF 签名 | 非标准方式，不符合规范化要求 | 使用标准 `CMake` class + `CMakeToolchain` 替代，移除手动 toolchain 解析和 ELF 签名逻辑 |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- libxml2/2.15.3

## 验证结果

```
conan create archives/l/libxslt/1.1.45.2/conanfile.py --build=missing
# 构建成功，test_package 通过
```

## 注意事项

- 此版本为 1.1.45 的规范化适配修复版本（1.1.45.1 → 1.1.45.2）
- 核心改进：将手动 toolchain 解析和 ELF 签名逻辑替换为标准 `CMake` + `CMakeToolchain` 模式
- 构建产出 `xsltproc` 可执行文件，已在 `commands.json` 中注册
- 静态构建，避免系统同名库动态链接污染 `/lib`、`/lib64`
---

**编译结束**: 2026-07-30 20:20
**最终状态**: built
