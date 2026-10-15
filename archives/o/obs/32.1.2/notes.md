# obs 32.1.2 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-10-14
- 编译器: clang / clang++ 15.0.4（OHOS SDK 26.0.0.18，target aarch64-linux-ohos）
- 状态: built

## 适配范围

OBS Studio 是一个 Qt6 + FFmpeg 的直播/录制应用。本配方构建其**核心库栈**：

| 产物 | 说明 |
|------|------|
| `libobs.so.30` | OBS 引擎（视频/音频、source、encoder、output、properties、obs_data、插件 ABI） |
| `libobs-opengl.so` | OpenGL/EGL 渲染后端（运行时由 libobs dlopen 加载） |
| `libobs-frontend-api.so` | 面向插件的前端 API 库 |
| `share/obs/libobs/*.effect` | libobs 运行时需要的 shader |

Qt 前端（`obs-studio` 可执行文件）与插件集**未启用**，原因见「遇到的问题」第 5 条。

## 编译步骤

```bash
# 依赖（全部命中制品仓预编译包，无需本地构建）
#   ffmpeg/7.1.5 simde/0.8.4-rc3 zlib/1.3.1.1 uthash/2.4.0 jansson/2.15.1.1
#   libuuid/2.42.2 libx11/1.8.13.1 libxcb/1.17.0.1 xorgproto/2025.1 libdrm/2.4.133
#   gl4es/1.1.6 extra-cmake-modules/6.29.0 cmocka/2.0.2
conan create archives/o/obs/32.1.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方 `generate()` 注入的关键 CMake 变量（详见 conanfile.py 内注释）：

- `CMAKE_SYSTEM_NAME=Linux`：OHOS 目标是 aarch64-linux-ohos ABI；CMake 默认取
  `CMAKE_HOST_SYSTEM_NAME`（=「HarmonyOS」），会让 `$<PLATFORM_ID:Linux,...>`
  选择器全部落空、静默丢掉 Linux 源文件。
- `CMAKE_SKIP_RPATH=ON`：见「遇到的问题」第 1 条。
- `ENABLE_UI/FRONTEND/PLUGINS/SCRIPTING=OFF`，`ENABLE_PULSEAUDIO/WAYLAND=OFF`。
- `ENABLE_UNIT_TESTS=ON` + `BUILD_TESTS=OFF`：构建并执行上游 cmocka 测试。
- `ECM_MODULE_PATH` / `CMAKE_REQUIRED_INCLUDES` / CMOCKA / OpenGL(gl4es) 变量：见第 3、4 条。
- 命令行为 `-DOBS_VERSION_OVERRIDE=32.1.2`（见第 2 条）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 安装后的 `libobs.so.30` dlopen 报 `Permission denied`（EACCES），构建树副本却正常 | CMake 会在构建期写入 RPATH、并在装包时**原地改写 ELF** 剥离 RPATH；OHOS 的 musl 加载器拒绝改写后的文件（程序头与 `.note.ohos.ident` 与构建副本逐字节一致，仅 `.dynamic` 少一条 RUNPATH） | `CMAKE_SKIP_RPATH=ON`：构建期不写 RPATH，装包期也不改写；运行期由 conan run 环境提供路径 |
| 2 | `obs_get_version_string()` 返回 `0.0.1` | 源码来自 release tarball，无 `.git`，OBS 回退到默认版本；且 toolchain 的 cache 变量在此处不可见——OBS 顶层第 3 行 `include(bootstrap)`（含解析版本的 versionconfig）而 `project()` 在第 4 行，CMake 只在 `project()` 时才读取 toolchain 文件 | 用命令行 `-D OBS_VERSION_OVERRIDE=32.1.2` 传入（`cmake.configure(cli_args=...)`），并写成平台补丁无关的上游机制 |
| 3 | `find_package(Uthash/Libdrm/...)` 解析到 conan config 包，`Uthash::Uthash`/`Libdrm::Libdrm`/`XCB::XCB` 目标缺失 | conan 的 CMakeToolchain 默认 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`，绕过 OBS 自带的 `cmake/finders` | toolchain 生成后追加 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)`，让 module 模式优先 |
| 4 | `find_package(X11_XCB REQUIRED)` 找不到 `FindX11_XCB.cmake`；`X11/X.h`、`xf86drm.h`、`uuid/uuid.h` 找不到 | 这三个 finder 由 extra-cmake-modules 提供（其 `share/ECM/find-modules`），但 conan 生成的 `ECMConfig.cmake` 不设置 `ECM_MODULE_PATH`；且 xorgproto / libdrm / libuuid 的头文件在 conan 缓存中独立存在，CMake 的 FindX11 / OBS 的 FindLibdrm 不会去找 | 显式设 `ECM_MODULE_PATH`；把 xorgproto、libdrm 的 include 目录加进 `extra_cflags/extra_cxxflags`；把 libuuid 的 include 加进 `CMAKE_REQUIRED_INCLUDES` |
| 5 | Qt 前端与插件无法构建 | OHOS 侧无 X11/Wayland 桌面栈、无 libv4l2/CEF；GitHub 归档 tarball 中 `plugins/obs-browser`、`plugins/obs-websocket` 为空占位（子模块不含在 tarball 里），而 `plugins/CMakeLists.txt` 在 Linux 分支对这些子模块是 FATAL_ERROR | 关闭 `ENABLE_UI/ENABLE_FRONTEND/ENABLE_PLUGINS`；OpenGL 用仓库既有 `gl4es/1.1.6` 满足 `deps/glad` 的 `find_package(OpenGL REQUIRED)` |
| 6 | `conan create` 复制源码到构建目录失败（`Errno 13 Permission denied`） | tarball 内含符号链接（`.github/scripts/build-macos`、`build-aux/run-clang-format` 等），HMDFS 上复制符号链接元数据会触发 chmod 失败 | 配方设 `no_copy_source = True`，直接在解压源码树构建；OBS 禁止 in-source build 且 `cmake_layout` 另置构建目录，仍为 out-of-source |
| 7 | 上游 4 个 cmocka 单元测试从不被构建 | 上游顶层 CMakeLists.txt 只 `add_subdirectory(test/test-input)`，从未 `add_subdirectory(test)`，`test/CMakeLists.txt`（含 `ENABLE_UNIT_TESTS` 门控）是死代码 | `patches/0001` 在 `ENABLE_UNIT_TESTS=ON` 时补 `enable_testing()` + `add_subdirectory(test)` |
| 8 | `os_set_thread_name()` 在 OHOS 上是空实现并触发 `-Werror,-Wunused-parameter` | 实现只有 `__APPLE__`/`__FreeBSD__`/`__GLIBC__` 分支，OHOS 为 musl 派生不定义 `__GLIBC__` | `patches/0003` 将 `__OHOS__` 并入 glibc 分支（OHOS 导出同签名 `pthread_setname_np`），有实质逻辑 |

## 源码修改（patches/）

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001 | `CMakeLists.txt` | `ENABLE_UNIT_TESTS=ON` 时 `enable_testing()` + `add_subdirectory(test)`，让上游 cmocka 测试真正参与构建 |
| 0002 | `cmake/common/osconfig.cmake` | HarmonyOS → `OS_LINUX`（复用 `cmake/linux` 模块集） |
| 0003 | `libobs/util/threading-posix.c` | `os_set_thread_name()` 增加 `__OHOS__` 分支（`pthread_setname_np`） |

## 依赖版本

`ffmpeg/7.1.5`、`simde/0.8.4-rc3`、`zlib/1.3.1.1`、`uthash/2.4.0`、`jansson/2.15.1.1`、
`libuuid/2.42.2`、`libx11/1.8.13.1`、`libxcb/1.17.0.1`、`xorgproto/2025.1`、`libdrm/2.4.133`、
`gl4es/1.1.6`、`extra-cmake-modules/6.29.0`、`cmocka/2.0.2`

## 验证结果

上游单元测试（配方 `build()` 内 ctest，随 `conan create` 自动执行）：

```text
1/4 Test #1: test_serializer ..................   Passed
2/4 Test #2: test_darray ......................   Passed
3/4 Test #3: test_bitstream ...................   Passed
4/4 Test #4: test_os_path .....................   Passed
100% tests passed, 0 tests failed out of 4
```

`test_package`（消费者视角 + 鸿蒙特有测试）：

```text
libobs 32.1.2 consumer test (HarmonyOS)
[ PASS] obs_get_version_string() reports 32.1.2
[ PASS] obs_initialized() is false before obs_startup()
[ PASS] os_set_thread_name() sets the thread name on HarmonyOS (__OHOS__ pthread_setname_np path)
[ PASS] os_set_thread_name() truncates long names instead of failing
[ PASS] obs_data serialises to JSON / parses its own JSON output / 字段往返
[ PASS] os_get_path_extension() on a HarmonyOS sandbox path
All HarmonyOS-specific checks passed.
```

## 注意事项

- `CMAKE_SKIP_RPATH=ON` 是本包能在 OHOS 加载的前提，不要移除；否则安装后的 `.so`
  无法被 dlopen（EACCES）。
- 消费方包含 `<obs.h>` 需要 `-I<prefix>/include/obs`（配方 `package_info` 已声明），
  并且 `simde` 为公开头依赖（`transitive_headers=True`）。
- 若后续要启用 Qt 前端/插件，需要另行适配 X11/Wayland 桌面栈、libv4l2/CEF，并提供
  obs-browser/obs-websocket 子模块源码。
---

**编译结束**: 2026-10-14 01:27
**最终状态**: built
