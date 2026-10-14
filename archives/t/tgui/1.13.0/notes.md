# tgui 1.13.0 适配笔记

## 概述

TGUI 是跨平台的现代 C++ GUI 库。本次适配使用 **SDL_RENDERER** 后端（原计划的 SFML_GRAPHICS 因依赖链断裂而切换），面向 OpenHarmony PC aarch64。

## 构建方式

- **构建系统**：CMake
- **生成器**：Ninja（`-G Ninja`）。OHOS 沙盒拒绝 make 的硬编码 `SHELL=/bin/sh`，Makefiles 生成器会在 CMake 配置阶段的编译器 try_compile 处报 `Check for working CXX compiler ... broken`（E346）；Ninja 直接 exec 编译器，配置与编译均通过。
- **后端**：SDL_RENDERER（SDL2 窗口 + SDL2_ttf 字体）
- **主要依赖**：
  - sdl2/2.30.10
  - sdl2_ttf/2.24.0（字体渲染）
  - freetype/2.14.3.1

## CMake 选项

```cmake
-DTGUI_BACKEND=SDL_RENDERER
-DTGUI_USE_X11=OFF            # 禁用 X11（仅影响鼠标光标显示）
-DTGUI_BUILD_TESTS=OFF
-DTGUI_BUILD_EXAMPLES=OFF
-DTGUI_BUILD_GUI_BUILDER=OFF
```

## 补丁说明

### patches/0001-cmake-Config.cmake.patch

在 `cmake/Config.cmake` 的 `elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")` 之后新增：

```cmake
elseif(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    set(TGUI_OS_LINUX 1)  # HarmonyOS uses Linux-compatible layer
```

**原因**：上游 `cmake/Config.cmake` 只识别 Windows/Android/Linux/BSD/Darwin/iOS/MINGW，本平台 `CMAKE_SYSTEM_NAME` 为 `HarmonyOS`，若不补分支则 `TGUI_OS_*` 全部为空，配置阶段直接失败。

**可达性（重要）**：配方**不再**覆盖 `CMAKE_SYSTEM_NAME`（曾用 `-DCMAKE_SYSTEM_NAME=Linux` 绕过）。本机实测 `CMAKE_HOST_SYSTEM_NAME` 与 `CMAKE_SYSTEM_NAME` 均为 `HarmonyOS`（见 `reports/conan-create.log` 与 work 构建目录 `build/CMakeCache.txt`），因此该补丁分支在本平台真实命中并置 `TGUI_OS_LINUX`；消费端用例 2 断言 `TGUI_SYSTEM_LINUX` 已定义，可反向证明补丁生效（空操作补丁会失败）。

## 后端选择经历

1. **初始方案**：SFML_GRAPHICS
   - **问题**：制品仓 sfml/2.6.1.1 仅为 partial 配方（System + Network 模块），缺少 Graphics/Window 模块
   - **失败原因**：SFML Graphics 需要完整窗口系统支持（X11/OpenGL），当前环境不具备

2. **最终方案**：SDL_RENDERER
   - **优势**：SDL2 和 SDL2_ttf 均有完整的 armv8 预编译包
   - **权衡**：禁用 X11 支持（`-DTGUI_USE_X11=OFF`），部分鼠标光标可能无法正确显示

## 测试

### 上游测试（实跑，未跳过任何用例）

- 上游测试源 83 个（root 30 / Loading 6 / Widgets 47），全部编译通过；
- 框架宏 `--list-tests` 声明 87 个用例，SDL_RENDERER 后端实际注册 82 个（5 个按后端条件编译排除）；
- 实跑结果：**82 个用例中 37 通过 / 45 失败**，断言 `10178 / 10314`，进程以 exit 136 终止；
- 失败根因统一：headless worker 无法创建可用的 SDL renderer/window（`tgui::CanvasSDL` 内部纹理为空）→ 触摸/鼠标事件无法注入 → 纹理加载连锁失败。属环境能力限制（无显示服务/虚拟帧缓冲），非构建或配方缺陷；
- 本次适配**未跳过、未禁用、未修改任何上游用例与断言**，失败结果如实记录于 `reports/test-report.md`。

### test_package（消费者集成测试）

6 个用例 / 13 条断言，全部通过（`SUCCESS (0 failure(s))`）：

1. 编译期后端选择（SDL_RENDERER + SDL window + SDL_ttf font，`TGUI_USE_SDL3=0`）
2. 平台宏 `TGUI_SYSTEM_LINUX`（HarmonyOS 经 Linux ABI 层命中）
3. `tgui::String`
4. `tgui::Layout`
5. `tgui::Color`
6. 运行期链接（`libtgui.so`、`libc++_shared.so`、FreeType 已映射）

## 平台经验（本包沉淀）

1. **CMake 不识别 `HarmonyOS` 系统名**：`CMAKE_SYSTEM_NAME` 取 HarmonyOS（CMake 无 `Platform/HarmonyOS.cmake`，配置期提示 `System is unknown to cmake`），上游里 `STREQUAL "Linux"` 的平台判定不会命中 → 正确做法是给工程补 HarmonyOS 分支，而不是 `-DCMAKE_SYSTEM_NAME=Linux` 覆盖绕过（覆盖会让补丁变空操作，属 R40 禁止的占位适配）。
2. **sdl2/sdl2_ttf 被静态链入 `libtgui.so`**：`readelf -d` 显示 `DT_NEEDED` 仅 `libc++_shared.so` 与 `libc.so`。消费端断言不得要求 SDL2/SDL2_ttf 出现在 `/proc/self/maps`（曾因此误判用例 6 失败）。
3. **freetype 制品 `cpp_info.libs` 为空**：其 `freetype::freetype` 目标不带 `-lfreetype`，消费端链接 `libtgui.so` 会因 OHOS 链接器默认 `--no-allow-shlib-undefined` 报 `FT_*` 未定义；改用 CMake 内置 `find_package(Freetype MODULE REQUIRED)` 的 `Freetype::Freetype` 即可（Conan 已把依赖 lib 目录放进 `CMAKE_LIBRARY_PATH`）。
4. **L5 SONAME 为 advisory**：`libtgui.so` 无版本后缀且无 `DT_SONAME`（CMake 不识别 HarmonyOS 系统名时上游 `VERSION/SOVERSION` 属性未产生 soname），L5 结果不影响 CI 包级通过判定，消费者按 Conan RPATH 绝对路径解析。

## 编译验证

- ✅ 库编译成功：`libtgui.so`（7.0 MB，arm64 ELF，clang 15 / libc++ / Release）
- ✅ Conan 配方验证：G0/G1/G2/G3/G4 全 PASS（`reports/conan-verify-report.md`）
- ✅ W3 本地 CI 模拟：L0 / L1 PASS，Build Summary `Total:1 Success:1 Failed:0`（L5 advisory-fail，见上）
- ✅ 消费者 test_package：6/6 用例、13/13 断言通过

## 已知限制

1. **X11 禁用**：部分高级鼠标光标不可用（`TGUI_USE_X11=OFF`）
2. **Headless worker**：45 个需要真实显示设备的图形用例无法通过（环境限制，已如实记录）
3. **后端限制**：仅适配 SDL_RENDERER，其他后端（SFML/GLFW/raylib）需各自依赖链
4. **无 SONAME**：`libtgui.so` 安装为无版本文件，L5 质量门禁报 advisory-fail（不阻塞 CI）

---

**编译结束**: 2026-10-07
**最终状态**: built
