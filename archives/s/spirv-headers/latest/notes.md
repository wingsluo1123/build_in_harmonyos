# spirv-headers latest 适配笔记

## 适配信息
- 软件名: spirv-headers
- 版本: latest (对应上游 tag vulkan-sdk-1.3.296.0)
- 上游仓库: KhronosGroup/SPIRV-Headers
- 源码 URL: https://github.com/KhronosGroup/SPIRV-Headers/archive/refs/tags/vulkan-sdk-1.3.296.0.tar.gz
- 源码 sha256: 1423d58a1171611d5aba2bf6f8c69c72ef9c38a0aca12c3493e4fda64c9b2dc6
- 适配日期: 2026-07-15

## 构建系统
header-only（纯头文件库，无需编译）。spirv-headers 仅包含 SPIR-V 规范的机器可读头文件，
被 spirv-tools、glslang 等 SPIR-V 工具链依赖，本身不产生任何二进制产物。

## Conan 配方说明
- package_type = "header-library"
- no_copy_source = True（源码无需拷贝到构建目录）
- settings 仅做平台白名单校验（Linux/OHOS/FreeBSD/Macos/Windows）
- build() 为空（header-only 无编译步骤）
- package() 将源码 include/ 下的 *.h / *.hpp 复制到包的 include/ 目录
  （保留 spirv/unified1/、spirv/1.0/ 等子目录结构）
- package_info: cpp_info.libs = []，仅暴露 include 目录

## 头文件布局
源码解压后 include/spirv/ 下包含：
- unified1/spirv.h（主头文件，SPIR-V 1.6 unified）
- 1.0/spirv.h、1.1/spirv.h、1.2/spirv.h（历史版本）
- 各扩展头文件（GLSL.std.450.h、OpenCL.std.h 等）

## test_package
通过 CMake 编译并运行 test_package.c，验证：
- 头文件 spirv/unified1/spirv.h 能被正常包含
- 基本常量 SpvMagicNumber(0x07230203) 与 SpvVersion(>0) 定义正确

## 依赖
无外部依赖（header-only）。

## 备注
- 该包为【依赖项】，主要服务于 spirv-tools / glslang 的 SPIR-V 工具链构建。
- 上游 tag 实际名称为 vulkan-sdk-1.3.296.0（带 .0 后缀），
  任务描述中的 vulkan-sdk-1.3.296 不存在（GitHub 返回 404），已修正为真实 tag。
- test_package.c 使用真实存在的常量 SpvMagicNumber / SpvVersion；
  原始描述中的 SpvVersion_1_0 在该头文件中不存在，已更正以保证测试可编译。
