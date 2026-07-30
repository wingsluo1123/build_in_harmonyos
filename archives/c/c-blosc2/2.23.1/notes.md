# c-blosc2 2.23.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-31
- 编译器: clang
- 状态: built

## 编译步骤
```bash
cmake -B build -S . \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=OFF \
  -DBUILD_FUZZERS=OFF \
  -DBUILD_BENCHMARKS=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_PLUGINS=OFF \
  -DBUILD_STATIC=ON \
  -DBUILD_SHARED=OFF \
  -DPREFER_EXTERNAL_LZ4=OFF \
  -DPREFER_EXTERNAL_ZLIB=OFF \
  -DPREFER_EXTERNAL_ZSTD=OFF
cmake --build build -j1
cmake --install build
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | BUILD_BENCHMARKS 编译失败 | clock_gettime/CLOCK_MONOTONIC 在 OHOS 不可用 | 设置 BUILD_BENCHMARKS=OFF |
| 2 | 无需 CMAKE_POLICY_VERSION_MINIMUM | c-blosc2 使用 cmake_minimum_required(3.16.3)，CMake 4.x 兼容 | 无需处理 |

## 源码修改
无补丁。

## 依赖版本
无外部依赖（内置 LZ4, zlib-ng, ZSTD 编解码器）。

## 交付物
- libblosc2.a / libblosc2.so
- blosc2.h, b2nd.h, blosc2/ 目录
- lib/cmake/Blosc2/Blosc2Config.cmake
- lib/pkgconfig/blosc2.pc

## 与 c-blosc v1 的差异
- 库名: blosc → blosc2
- API: blosc_compress → blosc2_compress（新增 srcsize/destsize 参数）
- CMake config: c-blosc → Blosc2
- 目标名: c-blosc::c-blosc → Blosc2::blosc2
- c-blosc2 无 snappy 支持，新增 plugins 支持
