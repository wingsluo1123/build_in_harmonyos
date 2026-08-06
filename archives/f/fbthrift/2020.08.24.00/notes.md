# fbthrift 2020.08.24.00 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang/clang++ (15.0.4)
- 状态: built (compiler + thrift-core library)

## 编译步骤

### 1. 依赖安装
预编译包安装 (cmd-pkgs):
- openssl 1.1.1w, zlib 1.3.1, zstd 1.5.6, gflags 2.2.2, glog 0.7.1
- boost 1.84.0 (header-only), libevent 2.1.12, libsodium 1.0.22
- lz4 1.10.0, snappy 1.2.2, abseil-cpp 20260107.1, fast_float 7.0.0

从源码编译:
- fmt 11.2.0 (cmake, 无依赖)
- double-conversion 3.3.0 (cmake, 无依赖)
- folly v2024.11.18.00 (cmake, 8个补丁, header-only Boost)
- fizz v2024.11.18.00 (cmake, FindSodium.cmake 修复)
- wangle v2024.11.18.00 (cmake)

### 2. fbthrift 配置和编译
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_PREFIX_PATH=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_CXX_FLAGS="-DGLOG_USE_GLOG_EXPORT -D__OHOS__" \
  -DCMAKE_CXX_STANDARD=17
make -j2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | FindBoost 模块缺失 | cmake 4.1.2 移除了 FindBoost | 手动设置 Boost 路径 | ✅ |
| 2 | boost::filesystem 链接失败 | Boost 仅安装头文件 | 替换为 std::filesystem (C++17) | ✅ |
| 3 | FOLLY_INLINE_VARIABLE 未定义 | folly v2024.11.18.00 移除此宏 | 添加宏定义到 CPortability.h | ✅ |
| 4 | FOLLY_GNU_ENABLE_ERROR 未定义 | folly v2024.11.18.00 移除此宏 | 添加宏定义到 CPortability.h | ✅ |
| 5 | GLOG_USE_GLOG_EXPORT 缺失 | glog 0.7+ 需要 | 添加到 CXX_FLAGS | ✅ |
| 6 | folly::SharedMutex::ReadHolder 缺失 | API 版本差异 | 需要匹配的 folly 版本 | ❌ |
| 7 | QueueObserver.h 缺失 | folly 版本差异 | 从旧版 folly 源码复制 | ✅ |
| 8 | FindSodium.cmake 不支持平台 | HarmonyOS 未识别为 UNIX | 添加 GCC 兼容回退 | ✅ |
| 9 | fizz-config.cmake ZLIB::ZLIB 缺失 | FindZLIB 未创建 imported target | 在 fizz-config.cmake 中手动创建 | ✅ |

## 编译产物

| 文件 | 说明 |
|------|------|
| bin/thrift1 | Thrift 编译器 (完整功能) |
| lib/libthrift-core.a | Thrift 核心库 |
| lib/libcompiler_*.a | 编译器支持库 (4个) |
| lib/libmustache_lib.a | 模板库 |

## 未完成部分

concurrency/protocol/async 库因 folly::SharedMutex API 版本差异未能编译。
需要使用 folly v2020.08.24.00 (与 fbthrift 同期版本) 重新编译。

## 依赖版本

- openssl: 1.1.1w (cmd-pkgs)
- boost: 1.84.0 (cmd-pkgs, header-only)
- fmt: 11.2.0 (from source)
- double-conversion: 3.3.0 (from source)
- folly: v2024.11.18.00 (from source, 8 patches)
- fizz: v2024.11.18.00 (from source)
- wangle: v2024.11.18.00 (from source)
- gflags: 2.2.2, glog: 0.7.1, zlib: 1.3.1, zstd: 1.5.6 (cmd-pkgs)

---
**编译结束**: 2026-08-06
**最终状态**: built (compiler + thrift-core)
---

**编译结束**: 2026-08-06 11:47
**最终状态**: failed
