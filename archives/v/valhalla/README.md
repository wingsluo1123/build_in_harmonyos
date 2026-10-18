# valhalla

Valhalla 是面向 OpenStreetMap 数据的 C++20 路网路由引擎：从 OSM PBF 构建分层瓦片图
（mjolnir），提供双向 A*/Dijkstra、矩阵、等时圈、地图匹配、时间依赖路由
（thor/meili/loki），并以多种格式序列化路线（tyr/odin）。库内自带 Gurka 测试框架，
可用内联 OSM PBF 在进程内构建瓦片并直接跑路由请求。

- 上游：<https://github.com/valhalla/valhalla>
- 许可：MIT

## OHOS 适配

- **构建系统**: CMake（clang 15 / OHOS 6.0 aarch64，`BUILD_SHARED_LIBS=ON`）。
- **C++ 标准**: profile 为 `cppstd=17`；配方 `configure()` 对本库强制 C++20。
- **子模块**: 上游 release tarball 不含 `third_party/`（rapidjson/date/googletest/
  libosmium/protozero/microtar/cpp-statsd-client/cxxopts/just_gtfs/tz/
  unordered_dense/vtzero），`source()` 按 3.8.2 tag 的 gitlink commit 逐个下载。
- **libc++**: OHOS libc++ 默认关闭 C++20 ranges/format（`_LIBCPP_HAS_NO_INCOMPLETE_*`）；
  定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 后 `std::views`/`std::format` 可用，但
  `libc++.so` 未导出 `std::format_error` 关键符号（库内补定义），且无 chrono
  formatter（日志时间戳改 `strftime`）。
- **平台识别**: 未设 `CMAKE_SYSTEM_NAME` 时 CMake 认不出 `HarmonyOS`，共享库无 SONAME、
  依赖记录相对 NEEDED、无 RPATH；设 `CMAKE_SYSTEM_NAME=OHOS` 修复。
- **关闭项**: `ENABLE_SERVICES`（缺 `libprime_server`）、Python/Node 绑定、GeoTIFF。
- **测试**: `test/gurka/test_*.cc`（134 个用例）在 `build()` 中构建并运行；依赖在线
  时区库（`spatialite`/`spatialite_tool` CLI，本制品仓无）的少量时间依赖用例受限。

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| boost | 1.84.0 | 头文件工具 + iostreams/program_options/regex/filesystem |
| protobuf | 21.12 | proto 生成与序列化（MODULE 模式） |
| geos | 3.13.1 | 几何运算 |
| sqlite3 | 3.49.1 | 瓦片/管理/时区数据库 |
| libspatialite | 5.1.0.2 | 空间 SQL（传递 proj/librttopo/libxml2） |
| curl | 8.15.0.1 | HTTP 客户端（可选） |
| zlib / lz4 | 1.3.1.1 / 1.10.0 | PBF 压缩 |
| expat / openssl | 2.8.5 / 3.5.6.1 | XML/加密 |
| luajit-openresty | 2.1-20260311 | Lua 标签转换脚本 |

## 产物

| 路径 | 说明 |
|------|------|
| `lib/libvalhalla.so*` | 路由引擎共享库 |
| `include/valhalla/**` | 公共头（含 `third_party/{rapidjson,date}`） |
| `lib/pkgconfig/libvalhalla.pc` | pkg-config 元数据 |
