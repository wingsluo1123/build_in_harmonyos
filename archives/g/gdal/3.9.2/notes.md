# gdal 3.9.2 适配笔记

## 本次固化范围

- 构建系统：CMake。
- 上游源码：`https://github.com/OSGeo/gdal/releases/download/v3.9.2/gdal-3.9.2.tar.gz`。
- SHA256：`c9767e79ca7245f704bfbcb47d771b2dc317d743536b78d648c3e92b95fbc21e`。
- 产物：`libgdal`、CMake/pkg-config 元数据、`gdal-config` 以及 GDAL/OGR 命令行工具。

## 依赖与选项

GDAL 是 MapServer 的强依赖。本次作为 MapServer 前置依赖，保留核心 GDAL/OGR 能力、PROJ 坐标系统支持、SQLite/GPKG、TIFF、PNG、JPEG 和命令行工具；关闭 Python 绑定、插件自动加载、Curl/OpenSSL/WebP/Arrow/Parquet/GEOS/PostgreSQL 等重型可选链条。

依赖：

- `proj/9.3.1`
- `sqlite3/3.49.1`
- `libtiff/4.7.2`
- `libpng/1.6.58`
- `libjpeg-turbo/3.2.0`

关键 CMake 选项：

- `BUILD_APPS=ON`
- `BUILD_TESTING=ON`（在可执行目标上运行 CTest；OHOS 交叉构建仅跳过执行）
- `BUILD_PYTHON_BINDINGS=OFF`
- `GDAL_BUILD_OPTIONAL_DRIVERS=OFF`
- `OGR_BUILD_OPTIONAL_DRIVERS=OFF`
- `GDAL_USE_PROJ=ON`
- `GDAL_USE_SQLITE3=ON`
- `OGR_ENABLE_DRIVER_SQLITE=ON`
- `OGR_ENABLE_DRIVER_GPKG=ON`
- `GDAL_USE_TIFF=ON`
- `GDAL_USE_PNG=ON`
- `GDAL_USE_JPEG=ON`
- `GDAL_USE_CURL=OFF`
- `GDAL_USE_OPENSSL=OFF`
- `GDAL_USE_WEBP=OFF`
- `GDAL_USE_ARROW=OFF`
- `GDAL_USE_PARQUET=OFF`
- `GDAL_USE_ARROWDATASET=OFF`
- `GDAL_USE_GEOS=OFF`

## 测试说明

官方 release tarball 中不包含 `autotest/` 目录；上游 CMake 仅在该目录存在且 `BUILD_TESTING=ON` 时注册核心测试。因此本 PR 按发布包内 CMake 注册测试计数为 0。recipe 仍启用 `BUILD_TESTING` 并在 `can_run(self)` 为真时执行 CTest，避免把零测试计数误写成未执行测试。

新增 `test_package/test_gdal.cpp`，包含 11 个实质检查：

- GDAL release version query。
- 驱动注册数量。
- MEM raster driver 获取。
- 2x2 MEM dataset 创建和尺寸校验。
- OGR WGS84 空间参考创建、设置、WKT 导出和内容校验。

## 本地验证

- 已校验官方源码 SHA256。
- 已执行 Python 语法检查、`git diff --check` 和规则扫描。
- 当前 Windows 工作站没有 OHOS Conan 环境，`conan create gdal/3.9.2` 等待远端 OHOS CI 验证。
