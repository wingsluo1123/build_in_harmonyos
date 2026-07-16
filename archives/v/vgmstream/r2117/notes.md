# vgmstream r2117 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 使用 Conan CMakeToolchain 生成构建配置
2. cmake configure + build (静态库，禁用可选依赖)
3. conan create 验证配方自包含性

关键 CMake 选项:
- BUILD_SHARED_LIBS=OFF (R26: 静态链接)
- BUILD_CLI=ON (构建命令行工具)
- 所有可选编解码器依赖关闭 (USE_FFMPEG=OFF, USE_MPEG=OFF 等)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G2 失败: "Library 'vgmstream' not found in package" | vgmstream 的 CMakeLists.txt 没有为静态库 target (libvgmstream) 添加 install() 规则，cmake.install() 只安装了 CLI 二进制 | 在 conanfile.py package() 中用 conan.tools.files.copy() 手动复制 libvgmstream.a 到 lib/，复制所有 .h 头文件到 include/ |
| 2 | manifest.yaml 模板占位符未替换 | 自动生成的 manifest 模板未填充 | 手动修复: software=vgmstream, build_system=cmake, build.system=cmake, sha256 填入实际值 |
| 3 | test_package 编译找不到头文件 | package() 未安装头文件 | 在 package() 中递归复制 src/*.h 到 include/ |

## 源码修改

无补丁。仅修改 conanfile.py 的 package() 方法添加手动文件复制。

## 依赖版本

无外部依赖（所有可选编解码器库均关闭）。

## 验证结果

conan-verify 8 道门禁全部通过 (G0-G4 + L2/L4/L5)。

## 注意事项

- vgmstream 的 CMakeLists.txt 中静态库 target 名为 `libvgmstream`，输出文件为 `libvgmstream.a`
- CMake 的 install() 规则只覆盖了 CLI 二进制和共享库（当 BUILD_SHARED_LIBS=ON 时），静态库和头文件需要手动安装
- 头文件位于 src/ 目录及其子目录中，需要递归复制以保持 include 路径结构
---

**编译结束**: 2026-07-16 11:57
**最终状态**: built
