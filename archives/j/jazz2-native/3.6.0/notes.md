# jazz2-native 3.6.0 适配笔记

## 编译环境

- 构建系统: cmake（上游顶层 CMakeLists + 嵌入式 nCine 的 CMakeLists，共 2 份）
- 编译日期: 2026-10-07
- 编译器: clang / clang++ 15.0.4（OHOS SDK 26.0.0.18 sysroot，`aarch64-linux-ohos`）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: published

## 上游测试清点（R51 申报表）

| 项 | 清点方法 | 结果 |
|----|---------|------|
| `tests/` / `test/` 目录 | `find <src> -maxdepth 3 -type d -iname '*test*'` | **0** |
| ctest 注册 | `grep -rn 'enable_testing\|add_test(' --include=CMakeLists.txt --include=*.cmake` | **0** |
| 测试框架引用 | `grep -rln 'Catch2\|catch2\|gtest\|doctest'` | **0** |
| 文件名含 test 的源文件 | `find <src> -iname '*test*' -type f` | 6 个，全部为误匹配（`GLDepthTest.*` / `GLScissorTest.*` / `DeflateStream.*`），非测试用例 |
| CMakeLists 总数 / 源文件数 | `find` | 2 / 399 个 .cpp |

结论：**上游确无自动化测试**（附上表清点证据）。可运行验证退化为 headless 冒烟：
上游 `main()` 自带 `--version` 早退路径（`Sources/Main.cpp:2243` → `PrintVersion` @ `:2196`），
先于任何 SDL/GL 初始化，因此无需打补丁即可在无显示环境验证二进制可加载。

## 编译步骤

```bash
# 源码
#   https://github.com/deathkiller/jazz2-native/archive/refs/tags/3.6.0.tar.gz
#   sha256 3df80d28d1e4495af832b854e87bdd3098dbc2d1d8227b72d052a9bdf8c2721e

# 依赖（全部已在 ohpcd 制品仓）
#   sdl2/2.30.10、openal-soft/1.25.2、libvorbis/1.3.7、libcurl/8.5.0、zlib/1.3.1.1

# 构建（配方 CMakeToolchain + CMakeDeps，一条命令走完编译/打包/冒烟）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方关键开关（详见 `conanfile.py::generate()`）：

```
-DNCINE_DOWNLOAD_DEPENDENCIES=OFF       # 禁联网拉 SDL2/OpenAL 源码，改用 conan 依赖
-DNCINE_PREFERRED_BACKEND=SDL2 -DNCINE_WITH_OPENGLES=ON
-DNCINE_WITH_GLEW=OFF -DNCINE_WITH_BACKWARD=OFF -DNCINE_WITH_OPENMPT=OFF
-DNCINE_VERSION_FROM_GIT=OFF -DNCINE_CREATE_CONTENT_SYMLINK=OFF -DNCINE_LINKTIME_OPTIMIZATION=OFF
-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64
-DDEATH_CPU_USE_IFUNC=OFF               # OHOS musl 不支持 IRELATIVE，见下表 #4
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pthread_setaffinity_np` / `pthread_getaffinity_np` / `pthread_cancel` 未定义符号（E211） | OHOS musl 未实现 Linux glibc 的这三个 pthread 扩展 | 补丁 0001 改 `sched_setaffinity` / `sched_getaffinity`；`pthread_cancel` 路径返回“未支持” |
| 2 | `fatal error: 'SDL.h' file not found` | ohpcd sdl2 把头装在 `include/SDL2/`，而 `Sources/nCine/Backends/SdlGfxDevice.h` 在 `CMAKE_BUILD` 下直接 `#include <SDL.h>` | 配方把 `<sdl2>/include/SDL2` 加入包含路径（不打上游补丁） |
| 3 | 链接期 22 个 ES 3.0 符号未定义（`glBlitFramebuffer` / `glInvalidateFramebuffer` / `glTexStorage2D` …） | nCine 的 ES 渲染路径调用 ES 3.0 入口点，sysroot 的 `libGLESv2.so` 不导出 | 改用同目录 `libGLESv3.so`；并把 4 个 GLES/EGL 查找变量显式指向 sysroot（库目录由 `clang -print-file-name=libm.a` 反查） |
| 4 | 二进制编译/链接通过，运行立刻崩溃（`Error relocating …: symbol not found` 之后进程异常终止） | nCine 默认 `DEATH_CPU_USE_IFUNC=ON`，为 `memcpy` 等生成 **IRELATIVE** 重定位；OHOS musl 动态加载器不支持 | 配方关 `DEATH_CPU_USE_IFUNC`（`cmake/ncine_helpers.cmake` 提供的开关）→ 二进制可运行，`readelf -r` 中 IRELATIVE 计数为 **0** |
| 5 | test_package 冒烟 `exit 127`，加载器报 `alSourcef` / `crc32` / `adler32` 等符号缺失 | ①application 包的运行时依赖在消费者/测试图中被标 **Skipped binaries**（`cpp_info` 只剩相对 `libdirs`、`package_folder` 为空），VirtualRunEnv 只注入 libvorbis/libogg/libcurl 三个目录，漏掉 OpenAL；②conan `run(env=[...])` 列表在本环境不生效 | ①测试包显式 `requires("openal-soft/1.25.2")` 使依赖被解析出真实包目录（SDL2/zlib 由配方静态链接，无需运行库）；②命令行内联 `LD_LIBRARY_PATH`（同仓库 acsccid 先例） |
| 6 | 首次链接报目标名不匹配 | 上游 CMake 目标名为大写/自定义，CMakeDeps 导出为小写命名 | 配方按 CMakeDeps 实测导出名对齐目标名 |
| 7 | `clang` 不在 PATH | 本机 clang 位于 `/data/service/hnp/bin/` | 配方在 `generate()` 中对编译器路径做绝对路径回退 |

## 源码修改

`patches/0001-Sources-nCine-Threading-Thread.cpp.patch`（`ohc refresh-patch --auto` 生成）

- 文件：`Sources/nCine/Threading/Thread.cpp`
- 内容：线程亲和性走 `sched_setaffinity` / `sched_getaffinity`（OHOS musl 无 `pthread_*affinity_np`）；
  `pthread_cancel` 分支返回“未支持”（该路径仅用于强制终止工作线程，不影响主循环）
- 平台相关，未引入新的平台宏空壳：分支用 `__GLIBC__` 做特征判断，其余平台仍走原实现
- **语义边界（如实说明）**：musl 分支用 `sched_*(0, …)`，POSIX 里 `pid=0` 表示**调用线程**，
  而 glibc 原实现 `pthread_*affinity_np(_sharedBlock->_handle, …)` 作用于**指定线程句柄**，
  两者仅在“对本线程操作”时一致。nCine 提供这两个线程亲和性接口（**本应用源码中未检索到
  调用点**：全树 `grep -i affinity` 仅命中 Thread.cpp/.h 的定义处），其语义为性能提示、
  不参与正确性判定，故以“对本线程读取/设置”的降级映射替代未实现的接口，属**有意的语义降级**
  而非等价替换。
  若需严格等价，需先把句柄映射为 tid（musl 无 `pthread_getthreadid_np`，须用 `gettid()`），
  再传 `sched_*(tid, …)`；本次以“编译可过 + 运行不崩 + 亲和性仅提示”为准，未引入该映射。
- 补丁内 `pthread_cancel` 与 `pthread_*affinity_np` 之外无其他改动（`refresh-patch --auto` 只追踪到
  本文件 1 处变更：12 增 / 3 删）

## 依赖版本

| 包 | 版本 | 说明 |
|----|------|------|
| sdl2 | 2.30.10 | 窗口/输入后端（制品仓该包为 **static-only**：`libSDL2.a`） |
| openal-soft | 1.25.2 | 音频（运行时唯一需动态解析的第三方库：`libopenal.so.1`） |
| libvorbis | 1.3.7 | OGG/Vorbis 解码 |
| libogg | 1.3.6 | libvorbis 传递依赖 |
| libcurl | 8.5.0 | `Sources/Shared/IO/WebRequest.cpp` 非 Windows 平台硬依赖 |
| zlib | 1.3.1.1 | 钉该版本与 libcurl 传递依赖对齐（1.3.1 触发版本冲突）；static-only |

可选未启用：`libopenmpt`（制品仓无配方 → `NCINE_WITH_OPENMPT=OFF`，仅影响 MOD 音乐播放）。

## 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
jazz2-native/3.6.0: Package '618ae02fbbea59868ca63fae232dca605764ff2a' created
...
[test] 1/2 二进制存在且可执行
[test] 2/2 --version 早退路径（不初始化 SDL/GL，headless 可跑）
Jazz² Resurrection 3.6.0
[test] PASS: jazz2-native 3.6.0 冒烟通过
```

- 编译：全绿（0 error）
- 冒烟：`bin/jazz2 --version` → `Jazz² Resurrection 3.6.0`（退出码 0）
- 产物：`bin/jazz2`（4.6 MB，已自签）、`share/{applications,doc,icons,jazz2}`

GUI 验证边界：真实渲染/游戏主循环需要显示 + GLES 上下文，headless CI 无法作为
gate（上游 `main()` 对无显示环境无容错），**未在 CI 验证**；建议在带图形栈的 OHOS
设备上人工确认。

## 注意事项

- 本仓 `sdl2/2.30.10` 与 `zlib/1.3.1.1` 均为 **static-only** 包，故运行时只需 OpenAL
  与 curl 的动态库；若上游包策略改为 shared，test_package 的 `LD_LIBRARY_PATH`
  构造会自动包含相应目录（按依赖图逐个解析），无需改脚本。
- 内容文件（音乐/音效/关卡）不在包内：上游 `Content/` 仅为骨架，实际数据来自
  用户自备的 Jazz Jackrabbit 2 原版数据。
---

**编译结束**: 2026-10-07 18:10
**最终状态**: published
