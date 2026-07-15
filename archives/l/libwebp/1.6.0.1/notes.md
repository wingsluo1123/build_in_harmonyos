# libwebp 1.6.0.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libwebp.so + libsharpyuv.so，供 dlopen 及作依赖。

## 适配修复 (1.6.0 → 1.6.0.1)
- 增加 `export_sources()` 方法，满足 G1 门禁要求 (R28)
- 其余配方与 1.6.0 保持一致

## 构建系统
- CMake (裸 cmake + ohos.toolchain.cmake 自发现)
- 不依赖 Conan Toolchain，直接使用 OHOS NDK 工具链

## 关键适配
- `CMAKE_INSTALL_LIBDIR=lib` — ohos.toolchain 64 位默认 lib64，强制 lib/
- `BUILD_SHARED_LIBS=ON` — 动态库
- 禁用所有命令行工具 (cwebp/dwebp/gif2webp 等) — 仅产出库文件
- `.so` 签名: 使用 binary-sign-tool 重签 (cmake/SDK-toolchain 产的自签无效)

## 状态
built — conan create + test 通过 (2026-07-15)
---

**编译结束**: 2026-07-15 14:31
**最终状态**: built
