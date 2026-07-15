# stk latest 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 状态: built
- 平台: HarmonyOS PC (aarch64)
- 源码来源: https://github.com/thestk/stk/archive/refs/heads/master.tar.gz

## 软件信息
- 名称: stk
- 版本: latest
- 上游仓库: thestk/stk
- 许可证: MIT
- 描述: The Synthesis ToolKit in C++ - audio synthesis library
- 产物: libstk.a (静态库) + Stk.h (头文件)
- 依赖: 无外部依赖（纯 C++ 库，可选依赖 ALSA/JACK 用于实时音频）

## Conan 配方说明

本归档采用 Conan 2.x CMAKE 配方：

- `conanfile.py`: CMAKE 构建配方
  - settings = "os", "compiler", "build_type", "arch"
  - OHOS 平台删除 shared 选项（HarmonyOS 仅支持静态库）
  - exports_sources = "patches/*"
- `conandata.yml`: 源码 URL + sha256（留空，CI 校验）
- `test_package/`: 测试包，编译链接测试程序验证库核心功能

## 编译步骤

1. Conan 下载源码：`get(self, **self.conan_data["sources"], strip_root=True)`
2. 生成工具链：`CMakeToolchain`
3. 配置：`cmake.configure()`
4. 构建：`cmake.build()`
5. 安装：`cmake.install()`

## 遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 平台不支持动态库 | HarmonyOS PC 当前仅支持静态链接 | config_options 中 OHOS 平台 rm_safe("shared") |
| 2 | sha256 暂未填入 | CI 环境校验 | conandata.yml 中 sha256 留空，由 CI 下载校验后回填 |

## 验证结果

test_package 验证 stk 核心功能，编译链接测试程序验证库核心功能。

## 注意事项

- stk 为依赖项范畴
- 默认静态构建（shared=False），符合系统库规则
