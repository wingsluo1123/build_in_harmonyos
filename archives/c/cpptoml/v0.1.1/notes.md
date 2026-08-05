# cpptoml v0.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. cmake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DENABLE_LIBCXX=OFF -DCPPTOML_BUILD_EXAMPLES=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
2. make 编译: `make -j2`
3. make install: `make install DESTDIR=$TEST_PREFIX`
4. 测试验证: 所有示例程序正常运行 (parse, build_toml, conversions)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 3.1.0) 不兼容 CMake 4.x | CMake 4.1.2 移除了对 <3.5 的兼容性 | 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 (cache_variables) |
| 2 | ENABLE_LIBCXX=ON 默认开启，查找 libc++ 失败 | deps/meta-cmake 子模块未包含，FindLIBCXX 模块缺失 | 设置 ENABLE_LIBCXX=OFF |
| 3 | 源码 URL 使用 api.github.com 导致 conan 无法识别格式 | api.github.com URL 无 .tar.gz 扩展名 | 改用 github.com/archive/refs/tags/ URL |
---

**编译结束**: 2026-08-06 04:45
**最终状态**: built
