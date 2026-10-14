# vkbasalt 0.3.2.10 适配笔记

## 编译环境
- 构建系统: meson（`meson.build` project('vkBasalt', ['c','cpp'], c_std=c11, cpp_std=c++2a)）
- 编译日期: 2026-10-13
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，musl）
- 状态: published（conan-verify 全绿）

## 编译步骤

conan create（标准流程）：
```bash
conan create archives/v/vkbasalt/0.3.2.10 \
  -pr:h=ohos-aarch64-local -pr:b=ohos-aarch64-local \
  --build=missing --build=vkbasalt
```
- meson setup（MesonToolchain 生成 native 文件，--prefix=/）
- meson build → libvkbasalt.so（shared_library）+ libreshade.a（静态）+ shader 头（glslangValidator 编译）
- meson install → lib/libvkbasalt.so + share/vulkan/implicit_layer.d/vkBasalt.json

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `vulkan/vk_layer.h` file not found | vkBasalt 不通过 `dependency('vulkan')` 获取头，裸 include；conan 不注入 vulkan-headers include | generate() 中把 vulkan-headers include 注入 MesonToolchain `c_args`/`cpp_args` |
| 2 | `spirv/unified1/spirv.hpp` file not found | reshade 模块需 SPIRV-Headers | 增加 `requires("spirv-headers/vulkan-sdk-1.3.290.0")` 并注入 include |
| 3 | `X11/Xlib.h` file not found | `keyboard_input_x11` static_library 不挂 x11_dep（dep 只挂 shared_library） | 增加 libx11 + xorgproto requires 并注入 include（X11/X.h 来自 xorgproto） |
| 4 | dlopen 报 `Permission denied`（文件权限 750 正常） | OHOS ELF 代码签名：.codesign 段零填充的 .so 加载被拒（EACCES） | `_self_sign_elfs()` 用 binary-sign-tool self-sign；工具路径双探测（CI `/data/service/hnp/bin`、本地 `usr/local/bin`） |
| 5 | MesonToolchain 无 cflags 属性 | Conan 2 MesonToolchain 的属性是 `c_args`/`cpp_args` | 改用 `tc.c_args`/`tc.cpp_args` |
| 6 | test_package 运行时找不到 libvkbasalt.so | 产物 750 权限非 owner 不可读 + sysroot libc++_shared.so 不在 conanrun 库目录 | package() chmod 755；test() 注入被测包 lib + sysroot lib 到 LD_LIBRARY_PATH |
| 7 | test 符号检查失败 | layer 导出的是 `vkBasalt_GetInstanceProcAddr`/`vkBasalt_GetDeviceProcAddr`（带前缀） | test_vkbasalt.cpp 按实际符号名 dlsym |

## 源码修改

无源码补丁（patches 为空）。所有 OHOS 适配都在配方层完成：
- include 路径注入（vulkan-headers/spirv-headers/libx11/xorgproto）
- glslangValidator 显式注册到 MesonToolchain binaries
- 绝对 binutils 路径（llvm-ar/llvm-ranlib 派生自编译器位置）
- ELF self-sign + 权限修复

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| vulkan-headers | vulkan-sdk-1.4.357.0 | vulkan/vulkan.h + vulkan/vk_layer.h（header-only） |
| spirv-headers | vulkan-sdk-1.3.290.0 | spirv/unified1/spirv.hpp（header-only） |
| libx11 | 1.8.13.1 | X11/Xlib.h + libX11 链接 |
| xorgproto | 2025.1 | X11/X.h 等核心协议头 |
| glslang | vulkan-sdk-1.3.290.0 | glslangValidator（shader 编译，tool） |
| meson / ninja / pkgconf | 1.11.0 / 1.12.1 / 3.0.5 | 构建工具（tool） |

## 验证结果

```bash
conan create archives/v/vkbasalt/0.3.2.10 -pr:h=ohos-aarch64-local -pr:b=ohos-aarch64-local --build=missing --build=vkbasalt
# 退出码 0
# test_package: PASS: all 4 vkBasalt checks passed
#   - dlopen libvkbasalt.so（验证 OHOS ELF 签名可加载）
#   - dlsym vkBasalt_GetInstanceProcAddr
#   - dlsym vkBasalt_GetDeviceProcAddr
#   - vkBasalt.json implicit layer 配置存在

conan-verify vkbasalt 0.3.2.10 --profile ohos-aarch64-local
# G1/G0/G2/G3/G4/L2/L4/L5 全 PASS，可标记 published
```

## 上游测试用例清点（R51）

上游 vkBasalt 0.3.2.10 **无任何测试套件**：
- 无 `test/` 目录（源码树仅 src/config 两个子目录）
- `meson.build` / `src/meson.build` 均无 `test()` 定义
- 上游仓库 README 也未声明测试目标

因此：上游用例数 = 0，通过率按 100%（0/0 无失败）；鸿蒙特有测试由 test_package 提供（4 项检查，见上）。

## 鸿蒙特有测试

test_package/test_vkbasalt.cpp 针对 HarmonyOS PC 平台特性设计：
1. **dlopen layer**：验证 ELF 代码签名后 .so 可被动态加载（OHOS 特有：未签名 .so 报 EACCES）
2. **layer 入口符号**：dlsym `vkBasalt_GetInstanceProcAddr` / `vkBasalt_GetDeviceProcAddr`（implicit layer 注册必需）
3. **层配置**：校验 `share/vulkan/implicit_layer.d/vkBasalt.json` 随包安装（Vulkan loader 启用 layer 依赖此文件）

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libvkbasalt.so | Vulkan implicit layer（已 self-sign） |
| share/vulkan/implicit_layer.d/vkBasalt.json | layer 注册配置（implicit_layer.d 安装目录） |
| licenses/LICENSE | Zlib 许可 |

## 注意事项

- vkBasalt 是运行时由 Vulkan loader dlopen 的 layer，**不链接 libvulkan**（VK_NO_PROTOTYPES + dispatch table），因此 vulkan-loader 制品缺失不阻塞
- OHOS ELF 签名是硬性要求：未签名的 .so 在任何 dlopen 场景都会 EACCES，签名工具路径按 CI/本地双探测
- shader 由 glslangValidator 在 configure 期编译为 .h 内嵌（generator），无需运行时 shader 文件
---

**编译结束**: 2026-10-13 17:01
**最终状态**: published
