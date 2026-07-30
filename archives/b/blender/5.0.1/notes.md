# Blender 5.0.1 OHOS 适配笔记

## 适配日期
2026-07-30

## 适配版本
Blender 5.0.1

## 项目复杂度评估

**复杂度**: ★★★★★ (极高)

Blender 是当前收录软件中复杂度最高的项目之一。

### 依赖项分析

Blender 依赖 100+ 个外部库，包括:
- 图形库: OpenGL, EGL, OSMesa
- 图像库: PNG, JPEG, TIFF, OpenEXR, OpenImageIO
- 视频编解码: FFmpeg, x264, x265, Ogg, Vorbis
- 3D 格式: Alembic, USD, OpenVDB
- 渲染引擎: Cycles (CUDA/HIP/OptiX/EMBREE/OSL)
- Python 集成
- 数十个其他库

### 适配策略

由于依赖项过多，采用了**最小化配置**策略:

1. **无头模式**: `WITH_HEADLESS=ON` - 禁用所有 GUI
2. **禁用 GPU**: 禁用 CUDA/HIP/OpenCL/OptiX/EMBREE/OSL
3. **禁用 Python**: 避免 Python 兼容性问题
4. **核心功能保留**: PNG/JPEG/TIFF/OpenEXR 图像格式支持

### 已知问题

1. **编译时间**: Blender 完整编译可能需要数小时
2. **内存需求**: 编译需要大量内存 (建议 16GB+)
3. **依赖链**: 需要先适配多个下游依赖库

### 建议

1. **仅服务器用途**: Blender OHOS 版本仅适合命令行渲染
2. **考虑预编译库**: Blender 提供预编译依赖库，可下载使用
3. **逐步完善**: 初始版本功能受限，后续可逐步添加

## 源码修改

无上游源码修改。最初提交的 `0002` 补丁将 OHOS 挂入 Android 路径会被 Blender 的 Android NDK 专用设置所拖累（`-fPIE`、Android 特定头文件、bionic 链接等均不适用于 OHOS musl 环境）。本次审查后彻底移除该补丁，OHOS 构建遵循标准 Linux aarch64 代码路径。

## 补丁说明

### 0002-disable-gpu-features-for-headless.patch
- ~~将 OHOS 添加为 Android 类似平台处理~~
- ~~禁用 GPU 相关功能~~
- **状态**: 已删除 — 避免 OHOS 走 Android NDK 路径（musl libc 兼容性、PIE/PIC 等 Android 专属设置会与 OHOS 工具链冲突）

## 待验证项

- [ ] 源码下载完整性
- [ ] CMake 配置成功
- [ ] 编译通过
- [ ] blender --version 运行正常
- [ ] 基本渲染功能

## 参考资料

- Blender 官方构建文档: https://wiki.blender.org/wiki/Building_Blender
- Blender 构建环境: `build_files/build_environment/`
- 依赖版本: `build_files/build_environment/cmake/versions.cmake`
