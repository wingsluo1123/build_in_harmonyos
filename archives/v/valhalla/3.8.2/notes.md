# valhalla 3.8.2 — OHOS 适配笔记

## 结论

- 配方：`archives/v/valhalla/3.8.2/`，`package_type=library`（默认 shared）。
- 依赖：boost/1.84.0、protobuf/21.12、geos/3.13.1、sqlite3/3.49.1、
  libspatialite/5.1.0.2、curl/8.15.0.1、zlib/1.3.1.1、lz4/1.10.0、expat/2.8.5、
  openssl/3.5.6.1、luajit-openresty/2.1-20260311（全部在 ohpcd 制品仓，有 OHOS 二进制）。
- 关闭：`ENABLE_SERVICES`（缺 libprime_server）、Python/Node 绑定、GeoTIFF、ccache。
- 构建：clang 15 / OHOS 6.0 aarch64，`-std=gnu++20`，`-D_LIBCPP_ENABLE_EXPERIMENTAL`，
  `CMAKE_SYSTEM_NAME=OHOS`。

## 关键适配点（按踩坑顺序）

1. **上游 tarball 缺 git 子模块**：`third_party/` 全是空目录。`source()` 按 3.8.2 tag
   内 gitlink 记录的 commit 逐个下载（rapidjson/date/googletest/libosmium/protozero/
   microtar/cpp-statsd-client/cxxopts/just_gtfs/tz/unordered_dense/vtzero）。
   `third_party/tz` 参与构建（`make leapseconds` + 编译成 `date_time_*.h`），
   googletest/microtar 供测试。

2. **C++ 标准**：profile `cppstd=17`，本库需 C++20 → `configure()` 里
   `self.settings.compiler.cppstd = "20"`，并在 toolchain 里显式
   `CMAKE_CXX_STANDARD=20`（VariablesBlock 在 CppStdBlock 之后写，能覆盖）。

3. **protobuf 走 MODULE 模式**（补丁 0003）：制品仓 `protobuf/33.6.1` 的
   `protobuf-config.cmake` 依赖 `absl::*` 目标，而 `abseil-cpp` 只导出
   `abseil-cpp::abseil-cpp`；且 `protobuf_generate_cpp()` 在 CONFIG 模式下不提供。
   改用 `find_package(Protobuf MODULE)` + 显式 `Protobuf_INCLUDE_DIR/LIBRARY/
   PROTOC_EXECUTABLE` 提示，并选 **protobuf/21.12**（无 abseil 依赖）。

4. **Boost 的 ZLIB::ZLIB**（补丁 0004）：`pkg_check_modules(ZLIB ...)` 设 `ZLIB_FOUND`，
   使 CMakeDeps 的 `BoostConfig` 跳过 `find_dependency(ZLIB)` → `ZLIB::ZLIB` 未定义。
   在 `find_package(Boost)` 前加 `find_package(ZLIB CONFIG REQUIRED)`。

5. **CMake 不认 HarmonyOS**：未设 `CMAKE_SYSTEM_NAME` 时 CMake 回退到 `uname -s`
   = `HarmonyOS`（"System is unknown"），平台链接旗标缺失 → 共享库无 SONAME、
   依赖记录**相对 NEEDED 路径**、无 RPATH（测试二进制因此无法加载库）。
   设 `CMAKE_SYSTEM_NAME=OHOS`（走 `Platform/OHOS.cmake` → `Platform/Linux`）后，
   `-Wl,-soname,libvalhalla.so.3` 与绝对 `-Wl,-rpath` 正常生成。

6. **libc++ 的 C++20 ranges/format**（补丁 0005）：
   - `_LIBCPP_HAS_NO_INCOMPLETE_RANGES/_FORMAT` 默认定义 → `std::views`/`std::format`
     不可见；`tc.extra_cxxflags.append("-D_LIBCPP_ENABLE_EXPERIMENTAL")` 打开。
   - 但 `libc++.so` 未导出 `std::format_error` 的析构/vtable/typeinfo（key function），
     在 `src/midgard/logging.cc` 内补定义 `format_error::~format_error()`。
   - chrono formatter 仍缺失（`std::formatter<time_point>` 被 delete）→
     日志时间戳改用 `strftime`。

7. **缺 include / libc++ 严格性**（补丁 0006）：
   - `valhalla/filesystem_utils.h` 用 `std::stringstream` 未 `#include <sstream>`。
   - `ostream::tellp()` 返回 `pos_type`，与 `int64_t` 相减在 libc++ 下二义 →
     显式 `static_cast<int64_t>`。

8. **std::pmr 缺失**（补丁 0007）：OHOS libc++ 无 `<memory_resource>`（只有
   `std::experimental::pmr` 且缺 `unsynchronized_pool_resource`）→
   `src/thor/costmatrix.cc` 的 `ReachedMap` 去掉 pmr 池分配，改用默认分配器
   （仅放弃池优化，语义不变）。

## 测试

- `test/gurka/test_*.cc` 共 **134** 个可执行（Gurka 框架，进程内构建瓦片 + 路由请求，
  纯 CPU 无外网）。配方 `build()` 构建 `gurka` 目标并逐个运行。
- 结果见 `reports/gurka-results.txt`（打包进 `reports/`）。
- 受限项：上游 `test/gurka/CMakeLists.txt` 原本给每个 Gurka 测试加
  `build_timezones` 依赖（在线构建 `tz.sqlite`，需 `spatialite`/`spatialite_tool`
  CLI，制品仓无）→ 补丁 0002 去掉该依赖；依赖时区库的时间依赖用例受限。

## 复现

```sh
conan create archives/v/valhalla/3.8.2 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```
