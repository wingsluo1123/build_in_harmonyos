# zug 0.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18)
- 状态: built

## 编译步骤

1. 下载 release tarball: `curl -kL -o zug-0.1.1.tar.gz https://github.com/arximboldi/zug/archive/refs/tags/v0.1.1.tar.gz`
2. 解压源码到工作目录
3. 安装依赖: Catch2 2.13.10 (header-only), Boost 1.84.0 (header-only, partial install)
4. 修改 CMakeLists.txt: C++14 → C++17 (避免 boost/variant 依赖)
5. 修改 test CMakeLists.txt: 添加 Catch2::Catch2 链接
6. 修改 random_sample.cpp: 添加 result_type typedef (C++17 URNG 要求)
7. cmake 配置:
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         -Dzug_BUILD_TESTS=ON \
         -DCMAKE_CXX_FLAGS="-Wno-error" \
         -DCMAKE_PREFIX_PATH=$HOME/usr/local ..
   ```
8. make check -j1 (编译+测试)
9. make install DESTDIR=$TEST_PREFIX (staging)
10. make install (安装到 DEFAULT_PREFIX)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL CERTIFICATE_VERIFY_FAILED | OHOS curl 缺少 CA 证书 | 使用 curl -kL 下载 |
| 2 | boost/variant.hpp 依赖 | zug 默认 C++14 使用 boost::variant | 切换 C++17 使用 std::variant |
| 3 | -Werror 导致编译失败 | std::result_of 在 C++17 中 deprecated | 添加 -DCMAKE_CXX_FLAGS="-Wno-error" |
| 4 | Catch2 链接缺失 | inline_var_tests 未链接 Catch2 | 添加 target_link_libraries(... Catch2::Catch2) |
| 5 | random_sample 编译失败 | deterministic_engine 缺少 result_type | 添加 using result_type = std::uint64_t |
| 6 | HMDFS 文件复制丢失 | cp -r/tar 在 HMDFS 上不可靠 | 使用 Python shutil.copytree |

## 源码修改

1. **CMakeLists.txt**: `set(CMAKE_CXX_STANDARD 14)` → `set(CMAKE_CXX_STANDARD 17)`
2. **test/__inline_var_tests/CMakeLists.txt**: 添加 `Catch2::Catch2` 到 target_link_libraries
3. **test/transducer/random_sample.cpp**: 添加 `using result_type = std::uint64_t;` 到 deterministic_engine

## 依赖版本

- boost 1.84.0 (header-only, 部分安装)
- catch2 2.13.10 (header-only)

## 验证结果

```
100% tests passed, 0 tests failed out of 50
Total Test time (real) =   1.61 sec
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/zug-0.1.1-ohos-prebuilt.tar.gz | 263743 bytes | 预编译包 (header-only + cmake config) |

## 注意事项

- zug 是 header-only 库，预编译包仅包含头文件和 CMake config 文件
- C++17 模式避免了大部分 Boost 依赖 (仅 boost/variant.hpp 在 C++14 模式下需要)
- G0 clean-build-verify 失败是因为脚本尝试运行 ./configure (autotools)，但 zug 使用 cmake
---

**编译结束**: 2026-06-26 17:32
**最终状态**: built
