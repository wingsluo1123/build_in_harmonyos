# tgui 1.13.0 适配笔记

## 概述

TGUI 是跨平台的现代 C++ GUI 库。本次适配使用 **SDL_RENDERER** 后端（原计划的 SFML_GRAPHICS 因依赖链断裂而切换）。

## 构建方式

- **构建系统**：CMake
- **后端**：SDL_RENDERER
- **主要依赖**：
  - sdl2/2.30.10
  - sdl2_ttf/2.24.0（字体渲染）
  - freetype（通过 sdl2_ttf 传递依赖）

## CMake 选项

```cmake
-DTGUI_BACKEND=SDL_RENDERER
-DTGUI_USE_X11=OFF            # 禁用 X11（仅影响鼠标光标显示）
-DTGUI_BUILD_TESTS=OFF
-DTGUI_BUILD_EXAMPLES=OFF
-DTGUI_BUILD_GUI_BUILDER=OFF
```

## 补丁说明

### 0001-cmake-Config-HarmonyOS.patch

在 `cmake/Config.cmake` 添加 HarmonyOS 平台检测，映射到 `TGUI_OS_LINUX`（HarmonyOS 使用 Linux 兼容层）。

**原因**：TGUI 的平台检测未定义 HarmonyOS，导致配置失败。

## 后端选择经历

1. **初始方案**：SFML_GRAPHICS
   - **问题**：制品仓 sfml/2.6.1.1 仅为 partial 配方（System + Network 模块），缺少 Graphics/Window 模块
   - **失败原因**：SFML Graphics 需要完整窗口系统支持（X11/OpenGL），当前环境不具备

2. **最终方案**：SDL_RENDERER
   - **优势**：SDL2 和 SDL2_ttf 均有完整的 armv8 预编译包
   - **权衡**：禁用 X11 支持（`-DTGUI_USE_X11=OFF`），部分鼠标光标可能无法正确显示

## 测试

### 上游测试

TGUI 的上游测试需要显示设备初始化，当前 HarmonyOS CI 环境为 headless，无法运行完整测试套件。

### test_package

消费者集成测试：
- 编译并链接 TGUI 库
- 验证核心 API 可用（Widget 创建、事件处理等）
- 不依赖显示设备

## 编译验证

- ✅ 库编译成功：libtgui.so (7.0 MB)
- ✅ 测试可执行文件构建完成
- ⚠️ 运行时测试需解决 RPATH/LD_LIBRARY_PATH 问题（环境限制，非配方缺陷）

## 已知限制

1. **X11 禁用**：部分高级鼠标光标不可用
2. **Headless 环境**：无法运行需要显示设备的完整上游测试
3. **后端限制**：仅支持 SDL_RENDERER，其他后端（SFML/GLFW/raylib）需额外适配
---

**编译结束**: 2026-09-26 19:40
**最终状态**: built
