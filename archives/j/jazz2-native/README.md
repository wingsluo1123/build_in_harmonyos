# Jazz² Resurrection (jazz2-native)

Jazz² Resurrection 是 **Jazz Jackrabbit 2（爵士兔 2）** 的开源重制版，由
deathkiller（Dan R）用 C++17 从零重写，自带嵌入式 **nCine** 游戏引擎
（Sources/nCine），渲染走 SDL2 + OpenGL ES 2/3，音频走 OpenAL。
本仓适配上游发布版 **3.6.0**（tag `3.6.0`）。

- 上游：https://github.com/deathkiller/jazz2-native
- 许可证：GPL-3.0
- 产物：单一可执行文件 `bin/jazz2`（应用名 `Jazz² Resurrection`，CMake 目标 `jazz2`），
  另装 `share/{applications,doc,icons,jazz2}`（应用图标/文档/内容目录骨架）

## OHOS 适配要点

- **构建系统**：上游 CMake（顶层 + 嵌入式 nCine 各一份），交叉编译直接
  `CMakeToolchain` + `CMakeDeps`，无需 patch config.guess。E092 口径：
  `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`，
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
- **依赖来源**（全部走 ohpcd，禁联网拉源码）：
  `-DNCINE_DOWNLOAD_DEPENDENCIES=OFF`、`NCINE_PREFERRED_BACKEND=SDL2`、
  `NCINE_WITH_OPENGLES=ON`、`NCINE_WITH_GLEW/BACKWARD/OPENMPT=OFF`、
  `NCINE_VERSION_FROM_GIT=OFF`、`NCINE_CREATE_CONTENT_SYMLINK=OFF`、
  `NCINE_LINKTIME_OPTIMIZATION=OFF`。
- **GLES 链接**：nCine 的 ES 渲染路径调用 **ES 3.0** 入口点
  （`glBlitFramebuffer` / `glInvalidateFramebuffer` 等），sysroot 的
  `libGLESv2.so` 不导出这些符号 → 配方改用同目录的 `libGLESv3.so`，并把
  `OPENGLES2_LIBRARY` / `EGL_LIBRARY` / `OPENGLES2_INCLUDE_DIR` /
  `EGL_INCLUDE_DIR` 四个查找变量显式指向 sysroot（库目录由
  `clang -print-file-name=libm.a` 反查得到）。
- **ifunc / musl**：nCine 默认 `DEATH_CPU_USE_IFUNC=ON` 会产生 IRELATIVE
  重定位，OHOS musl 动态加载器不支持 → 二进制启动即崩；配方关闭该开关后
  正常启动（`readelf -r` 中 IRELATIVE 计数为 0）。
- **pthread 缺失符号（E211）**：OHOS musl 无 `pthread_setaffinity_np` /
  `pthread_getaffinity_np` / `pthread_cancel` → 补丁
  `0001-Sources-nCine-Threading-Thread.cpp.patch` 改走 `sched_setaffinity` /
  `sched_getaffinity`（`pid=0` 即调用线程，相对 glibc 的“指定线程句柄”为**有意的
  语义降级**：亲和性仅作性能提示、不参与正确性，详见版本目录 `notes.md`），
  取消语义按“不支持”返回（该路径仅用于强制终止工作线程，不影响主循环）。
- **SDL2 头布局**：ohpcd sdl2 把头装在 `include/SDL2/`，而
  `Sources/nCine/Backends/SdlGfxDevice.h` 在 `CMAKE_BUILD` 下直接
  `#include <SDL.h>` → 配方把 `include/SDL2` 加入包含路径（不打上游补丁）。
- **libcurl 硬依赖**：`Sources/Shared/IO/WebRequest.cpp` 在非 Windows 平台
  无条件 `#include <curl/curl.h>`（上游无开关）→ 配方 requires
  `libcurl/8.5.0`；`zlib` 钉 `1.3.1.1`，与 libcurl 的传递依赖对齐（1.3.1 会
  触发版本冲突）。
- **验证边界（GUI）**：游戏主循环需要显示/GLES 上下文，headless CI 无法作为
  gate。上游 `main()` 自带 `--version` 早退路径（`Sources/Main.cpp:2243`，
  先于任何 SDL/GL 初始化），test_package 用它验证“二进制可加载 + 共享依赖可
  解析 + ELF 已自签 + 版本字符串一致”。**真实渲染/游戏主循环未在 CI 验证**
  ——建议在带图形栈的 OHOS 设备上人工确认。
- **test_package 运行环境**：conan `run env` 列表在本环境不生效（同仓库
  acsccid 先例），改为在命令行内联 `LD_LIBRARY_PATH`；另外 application 包的
  运行时依赖在消费者图里会被标为 `Skipped binaries`（`cpp_info` 只剩相对
  `libdirs`、`package_folder` 为空），故测试包显式 `requires("openal-soft/…")`
  以解析出真实包目录（OpenAL 是本二进制唯一需要动态解析的第三方共享库，
  SDL2/zlib 由配方静态链接）。

## 依赖关系

- 直接依赖（均已在 ohpcd 发布）：`sdl2/2.30.10`、`openal-soft/1.25.2`、
  `libvorbis/1.3.7`、`libcurl/8.5.0`、`zlib/1.3.1.1`
- 传递依赖：`libogg/1.3.6`（libvorbis 依赖）
- 可选（**未启用**）：`libopenmpt`（制成品仓无配方 → `NCINE_WITH_OPENMPT=OFF`，
  仅影响 MOD 音乐播放）

## 上游测试

上游**无任何自动化测试**：全树 2 个 `CMakeLists.txt`、0 处
`enable_testing`/`add_test`、0 处 Catch2/gtest/doctest 引用，无 `tests/` 目录。
故验证以 headless 冒烟（`--version`）为准，详见版本目录 `notes.md` /
`reports/test-report.md`。
