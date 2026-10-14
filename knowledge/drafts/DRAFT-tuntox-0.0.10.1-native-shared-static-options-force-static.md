# DRAFT-tuntox-0.0.10.1-native-shared-static-options-force-static
> 上游 CMake 自带 ENABLE_SHARED/ENABLE_STATIC 使 -DBUILD_SHARED_LIBS=OFF 失效、误链共享库触发运行期 stale_runtime_library 时改用项目原生选项强制静态并加安装后防御校验

## 问题特征（真实日志片段/标记）
真机 preflight 的 test_package 阶段，`tuntox -h` 的前两条断言（help banner / options）持续 FAIL，而 ELF aarch64 校验通过。第 12 轮加入 `[debug] help_out=` 取证后，日志暴露真正症状：

    [debug] help_out=Error loading shared library libtoxcore.so: (needed by .../p/bin/tuntox)
    Error relocating .../p/bin/tuntox: tox_callback_friend_lossless_packet: symbol not found
    Error relocating .../p/bin/tuntox: tox_iteration_interval: symbol not found
    Error relocating .../p/bin/tuntox: tox_iterate: symbol not found
    Error relocating .../p/bin/tuntox: tox_friend_get_connection_status: symbol not found

同时 CMake 构建日志中可见共享库被同时构建：

    [ 18%] Building C object CMakeFiles/toxcore_shared.dir/toxcore/events/group_join_fail.c.obj

HMBS 平台据此给出 `[stale_runtime_library]` 诊断：测试进程加载的是系统旧动态库，而非当前构建产物。

## 根因
c-toxcore 不用 CMake 通用变量控制库类型，而是自带选项：`cmake/ModulePackage.cmake` 中 `option(ENABLE_SHARED ON)`、`option(ENABLE_STATIC ON)`，两者默认都开。因此 `-DBUILD_SHARED_LIBS=OFF` 对 c-toxcore 无效，构建同时产出 `libtoxcore.so` 与 `libtoxcore.a`。tuntox 以 `-ltoxcore` 链接时优先挑中共库，生成的 ELF 对 `libtoxcore.so` 形成动态依赖。真机 OHOS loader 按运行库搜索顺序加载了系统内的旧版 `libtoxcore.so`，其符号集与当前构建头文件不匹配，`tox_*` 全部 reloc 失败，`tuntox -h` 输出为空导致断言失败。这是「错误选中共库」而非缺符号或缺 RPATH，因此禁用 LD_PRELOAD、嵌入 DT_RPATH 等既有手段均不适用。

## 修复方案（rec）
1. 在 toxcore 的 CMake 配置阶段改用项目原生选项强制只产静态库：在配方 `build()` 配置命令追加 `-DENABLE_SHARED=OFF -DENABLE_STATIC=ON`。
2. 确认构建产物只含 `libtoxcore.a`，不再生成 `CMakeFiles/toxcore_shared.dir` 与 `libtoxcore.so`。
3. 在安装后增加防御校验：对打包的 `tuntox` 二进制检查动态依赖，确认没有 `libtoxcore.so` 的 `NEEDED` 项（例如 `readelf -d`），保证 tuntox 完全静态链接 toxcore/sodium，运行期不再依赖 `libtoxcore.so`。
4. 同步更新 `notes.md`，记录根因、原生选项来源与校验方式。
5. 保留 `[debug] help_out=` 取证输出，作为后续同类问题的判定依据。

## 禁止策略
- 禁止仅设置 `-DBUILD_SHARED_LIBS=OFF` 即判定通过：当上游以原生 `ENABLE_SHARED` 覆盖通用变量时该设置无效，仍会产出 `libtoxcore.so`。
- 禁止在日志仍出现 `CMakeFiles/toxcore_shared.dir` 或产物仍含 `libtoxcore.so` 时放行。
- 禁止把本问题误判为 shell/getcwd 问题并反复切换 HNP bash 与 /bin/sh；`[debug] help_out=` 已证明是运行期动态库解析问题。

## 与相近条目的边界（查重）
- E346 / gdal / ccmake / libogg / aws-lc-tools：Ninja generator 规避 CMake try-compile 递归 make 的 EAGAIN；本条的 Ninja 规避属已覆盖范式，非本条新增内核。
- E672：`__gnu_cxx`/`copy_n` 扩展头缺失，为编译期头文件根因，不同。
- daw：clang15 前端 ICE；gcc9：dejagnu torture 段错误；均为不同根因的编译错误。
- libnxt：涉及静态库/符号，但失败在归档成员引用悬空与传递链接闭包缺符号；本条失败在「错误选中共库」。
- paperjam：涉及运行期库解析，但方案是禁用 LD_PRELOAD 与嵌入 DT_RPATH；本条既非缺符号也非缺 RPATH，而是误链共享库。
- 本条真正新增内核：上游项目原生 `ENABLE_SHARED`/`ENABLE_STATIC` 覆盖通用 `BUILD_SHARED_LIBS`，可迁移到任意「通用 CMake 变量被项目原生选项覆盖」的库。

## 适用判断
当下游链接上游 CMake 库时，若目标库的 CMakeLists 以自定义 `ENABLE_SHARED`/`ENABLE_STATIC`（或同类原生选项）控制库类型，而配方只设置了通用 `BUILD_SHARED_LIBS`，则应怀疑误链共享库。典型表现：同时产出 .so/.a、`-l<lib>` 挑中共库、真机 loader 加载系统旧库、运行期出现成片的 `symbol not found` reloc 失败。处置：改用项目原生选项强制静态，并在安装后加防御校验确认产物不对目标 .so 形成动态依赖。
