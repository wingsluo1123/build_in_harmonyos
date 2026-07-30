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

## 补丁说明

无上游源码修改，无 patches/ 目录。最初提交的 `0001`（空 stub）和 `0002`（OHOS-as-Android）补丁均已在审查后移除：
- `0001`：空 if 块，无实质逻辑
- `0002`：将 OHOS 挂入 Android NDK 路径（PIE/PIC、bionic 链接、Android 私有头文件），与 OHOS musl 工具链不兼容

OHOS 构建沿用标准 Linux aarch64 代码路径，musl libc 由工具链 sysroot 提供。

## 测试说明 (R40)

按照 R40 规则，图形/渲染类库的完整适配验证需要人工确认渲染管线行为。本 `test_package` 仅覆盖最小化冒烟测试：

1. `blender --version` — 二进制可执行性 + 版本输出
2. `blender --help` — CLI 参数解析与模块初始化（无需 GUI）
3. `blender -b --factory-startup` — 无头工厂模式启动（验证动态链接完整性）

**未覆盖**：
- 实际 .blend 文件渲染（需完整运行时环境：图像库、OpenEXR 等）
- Cycles 引擎功能（已禁用）
- GPU 渲染路径（OHOS 不可用）

需在 CI 上跑通真实场景后，再将 `manifest.yaml` 中的 `status` 从 `pending` 改为 `built`，并将 `requires_manual_verification` 改为 `false`。

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
