# libzippp

libzippp 是 libzip 的 C++ 封装库，提供面向对象的接口用于创建、读取和修改 ZIP 归档文件。

## 功能概述

- 创建、打开、读取、修改 ZIP 文件
- 添加文件和目录条目
- 设置压缩方法（DEFLATE / STORE）
- 读取条目数据和元信息
- 进度回调支持
- 可选加密支持（LIBZIPPP_ENABLE_ENCRYPTION）

## OHOS 适配

- **无需源码修改**：libzippp 7.1 在鸿蒙平台上零补丁即可编译
- **依赖处理**：libzip 预编译包缺少 `libzip.so` 开发符号链接，需手动创建 `ln -s libzip.so.5.5 libzip.so`
- **下载注意**：GitHub 源码需通过 `codeload.github.com` 下载，直连 `github.com` 会超时
- **构建系统**：CMake，init-build 可能误检测为 autotools，需根据 CMakeLists.txt 修正

## 依赖关系

| 依赖 | 类型 | 说明 |
|------|------|------|
| libzip | 编译+运行 | ≥ 1.10.1，ZIP 归档核心库 |
| zlib | 编译+运行 | ≥ 1.3.1，libzip 的压缩后端 |

## 参考资料

- 源码仓库: https://github.com/ctabin/libzippp
- 依赖库 libzip: https://github.com/nih-at-lib/libzip
- 许可证: BSD-2-Clause
