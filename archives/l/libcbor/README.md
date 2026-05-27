# libcbor

CBOR (Concise Binary Object Representation) protocol implementation for C.

## 简介

libcbor 是一个轻量级的 CBOR 编解码库，支持 RFC 8949 标准。CBOR 是一种二进制数据序列化格式，设计用于替代 JSON，在物联网和受限设备中广泛使用。

## 版本信息

- 当前版本: 0.11.0 (2024-02-04)
- 主页: https://github.com/PJK/libcbor

## 依赖

无外部依赖（纯 C 实现）。

## OpenHarmony 适配要点

1. **构建系统**: CMake
2. **编译为静态库**: 默认构建静态库 (BUILD_SHARED_LIBS=OFF)
3. **CMake 4.x 兼容**: 需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
4. **跳过单元测试**: WITH_TESTS=OFF（需要 CMocka）

## 版本列表

| 版本 | 状态 | 发布日期 |
|------|------|----------|
| 0.11.0 | built | 2024-02-04 |

## 使用方法

```bash
# 使用 pkg-config
pkg-config --cflags libcbor
pkg-config --libs libcbor

# CMake 集成
find_package(libcbor REQUIRED)
target_link_libraries(your_target PRIVATE libcbor)
```
