# sdl12-compat 1.2.68 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 状态: built
- 平台: HarmonyOS PC (aarch64)
- 源码来源: https://github.com/libsdl-org/sdl12-compat/archive/refs/tags/release-1.2.68.tar.gz

## 软件信息
- 名称: sdl12-compat
- 版本: 1.2.68
- 上游仓库: libsdl-org/sdl12-compat
- 许可证: Zlib
- 描述: SDL 1.2 compatibility layer on top of SDL2
- 产物: libSDL.a (静态库) + SDL.h (头文件)
- 依赖: SDL2/2.30.0（构建和运行时依赖）

## Conan 配方说明

本归档采用 Conan 2.x CMAKE 配方：

- `conanfile.py`: CMAKE 构建配方
  - settings = "os", "compiler", "build_type", "arch"
  - 通过 Conan 声明并传播 `SDL2/2.30.0`
  - CMake 使用 `SDL2::SDL2` 获取依赖头文件
- `conandata.yml`: 源码 URL、已验证的 SHA-256 和依赖补丁
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
| 1 | SDL2 依赖无法解析 | 原配方引用未发布的 `sdl2/2.30.10` | 改用已发布的 `SDL2/2.30.0` 和 Conan CMake target |
| 2 | 源码完整性校验 | 下载归档需要固定校验值 | 使用实测 SHA-256 `63c6e4dcc1154299e6f363c872900be7f3dcb3e42b9f8f57e05442ec3d89d02d` |

## 验证结果

test_package 使用 SDL dummy video 后端创建 64x64 surface，执行像素填充、
buffer flip，并验证 SDL 事件队列。该测试覆盖视频 surface 和事件兼容层，
但不覆盖真实显示输出、GPU 加速、音频设备或输入设备；这些能力仍需在
具有 HarmonyOS 图形和音频环境的设备上人工确认。

## 注意事项

- sdl12-compat 为依赖项范畴
- 默认静态构建（shared=False），符合系统库规则
