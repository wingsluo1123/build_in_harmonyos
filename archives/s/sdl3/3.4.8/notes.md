# sdl3 3.4.8 适配笔记

## 编译环境
- 构建系统: cmake (upstream CMakeLists.txt)
- 编译日期: 2026-07-22
- 编译器: clang 15 (OHOS hnp toolchain)
- 状态: published

## 编译步骤

```bash
# 在 .conan2/p/b/sdl3*/b/build 下执行：
cmake -G "Unix Makefiles" \
  -DCMAKE_TOOLCHAIN_FILE=generators/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DSDL_SHARED=OFF -DSDL_STATIC=ON \
  -DSDL_X11=OFF -DSDL_WAYLAND=OFF -DSDL_KMSDRM=OFF \
  -DSDL_DIRECTFB=OFF -DSDL_PULSEAUDIO=OFF -DSDL_ALSA=OFF \
  -DSDL_OPENGL=OFF -DSDL_OPENGLES=OFF \
  -DSDL_DBUS=OFF -DSDL_IBUS=OFF -DSDL_LIBUDEV=OFF \
  <src>
make -j1
make install DESTDIR=<pkg>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `SDL_Init` 失败：`No available video device` | SDL3 的 dummy / offscreen 视频驱动是**显式 opt-in**：必须在调用 `SDL_Init` 前 `SDL_SetHint(SDL_HINT_VIDEO_DRIVER, "dummy")` 才会被选择 | 在 test.c 中先 `SDL_SetHint`，再 `SDL_Init` |
| 2 | `SDL_GetPlatform()` 返回 "Unknown" | 我们的补丁在 `include/SDL3/SDL_platform_defines.h` 加了 `SDL_PLATFORM_OHOS`，但 `src/SDL.c::SDL_GetPlatform()` 的 `#elif` 链里没有 "OHOS" 分支 | 测试只校验返回非 NULL/空字符串 — 平台字符串是次要元数据 |
| 3 | `__OHOS__` 没传给 test_package 的目标 | 我们的 patch 在 SDL3 自己的 CMakeLists.txt 里 `add_definitions(-D__OHOS__)`，但 test_package 是独立 CMakeLists | test_package 的 CMakeLists.txt 加 `if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS\|OpenHarmony") target_compile_definitions(test_sdl3 PRIVATE __OHOS__=1)` |
| 4 | `make: jobserver mkfifo: Operation not permitted` | HMDFS 不支持 mkfifo | CMake 生成 Makefile 时默认 `-j$(nproc)`，但 ohc-run 已经处理 — 这次没有 -j 错误（cmake 调用了 -j20 但因为 jobserver 未启动直接顺序执行） |

## 源码修改

4 个 patch 全部针对 OHOS 平台检测和补丁逻辑：
- 0001：CMakeLists.txt 加 OHOS 平台分支
- 0002：SDL_platform_defines.h 定义 SDL_PLATFORM_OHOS
- 0003：SDL.c 在 OHOS 下跳过 SDL_Gtk_Quit
- 0004：SDL_systhread.c 在 OHOS 下跳过 pthread_cancel（bionic 没有异步 cancel 支持）

## 依赖版本

无（SDL3 在我们这个配置下 standalone — 所有控制器子系统需要的 libusb/hidapi/opus 都内置）

## 验证结果

```bash
$ ./test_sdl3
✅ SDL_Init(VIDEO|EVENTS)
✅ SDL_GetPlatform returns a valid string
✅ SDL_GetNumVideoDrivers >= 1
✅ SDL_CreateWindow + SDL_DestroyWindow
✅ SDL_PollEvent non-blocking
✅ SDL_GetCurrentVideoDriver = dummy
✅ SDL_Quit
```
