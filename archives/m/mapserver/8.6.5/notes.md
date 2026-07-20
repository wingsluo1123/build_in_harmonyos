# mapserver 8.6.5 适配笔记

## 范围

本次适配 MapServer 8.6.5，作为积分赛高难任务 `mapserver` 的正式库提交。

保留：

- `libmapserver`
- `mapserv`
- `map2img`
- `shptree`
- `coshp`
- `shptreevis`
- `sortshp`
- `legend`
- `scalebar`
- `msencrypt`
- `tile4ms`
- `shptreetst`
- WMS 基础能力

关闭：

- FastCGI
- GEOS
- PostGIS
- GIF
- protobuf-c/vector tile
- libxml2/WFS/WCS/OGCAPI
- Cairo
- FriBidi/HarfBuzz
- Curl client stacks
- PCRE2
- 语言绑定和 fuzz/unit tests

## 高难原因

MapServer 上游 CMake 强制依赖 PNG、JPEG、Freetype、PROJ、GDAL，其中 GDAL 自身又牵引 PROJ、SQLite/GPKG、TIFF、PNG、JPEG 等地理空间依赖。上游默认还会尝试 FastCGI、GEOS、PostGIS、libxml2/WFS/WCS/OGCAPI、protobuf-c/vector tile、Cairo、FriBidi/HarfBuzz、Curl 客户端、语言绑定和 fuzz/unit test 等服务端、数据库、渲染、文本布局和测试数据链条。全量验证依赖真实地图数据、OGC 服务行为和多 CLI/CGI 入口，OpenHarmony 上一次性拉满闭包与测试成本极高，因此首轮采用核心库+核心工具+WMS 的可验证子集。

## 测试

上游发布包内 CMake 注册 1 个 `unit_test`，本次关闭上游测试以避免交叉运行测试数据和依赖闭包。

新增 `test_package/test_mapserver.c`，编译并链接 `libmapserver`，检查：

- `msGetVersion()` 返回版本字符串。
- 版本字符串包含 `MapServer version`。
- `msGetVersionInt()` 返回 `80605`。

非交叉环境下额外运行 `mapserv -v`。

## 本地验证

- 已校验官方源码 SHA256。
- 当前 Windows 工作站没有 OHOS Conan 环境，`conan create mapserver/8.6.5` 等待远端 OHOS CI 验证。
