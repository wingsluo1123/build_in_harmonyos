# MapServer

## 简介

MapServer 是 OSGeo 旗下的地理空间服务与制图引擎，可发布栅格、矢量和 OGC 服务，也提供 `mapserv`、`map2img`、`shptree` 等命令行工具。

## OHOS 适配

- 上游 CMake 强制查找 PNG、JPEG、Freetype、PROJ 和 GDAL。
- 首轮适配保留核心 MapServer 动态库、WMS 基础能力和命令行工具。
- 关闭 FastCGI、PostGIS、GEOS、protobuf-c/vector tile、libxml2/WFS/WCS/OGCAPI、Cairo、FriBidi/HarfBuzz 等可选链条，降低交叉编译和远端 CI 依赖风险。

## 依赖

- `gdal/3.9.2`
- `proj/9.3.1`
- `libpng/1.6.58`
- `libjpeg-turbo/3.2.0`
- `freetype/2.14.3`

## 验证

`test_package` 编译并链接 `libmapserver`，调用 `msGetVersion()` 和 `msGetVersionInt()`；非交叉环境下额外执行 `mapserv -v`。

## 参考

- 官网: https://mapserver.org/
- 上游仓库: https://github.com/MapServer/MapServer
