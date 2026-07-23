# boost 1.90.0 适配笔记

## 编译环境
- 构建系统: b2 (Boost.Build, 自引导)
- 编译日期: 2026-07-24
- 编译器: /data/service/hnp/bin/clang++ (Clang 15.0.4, target aarch64-linux-ohos)
- 状态: published

## 编译步骤

1. 下载并解压 boost_1_90_0.tar.bz2
2. `./bootstrap.sh --with-toolset=clang` 引导 b2
3. 创建 user-config.jam，配 OHOS clang++ 跨编译
4. `./b2 --user-config=user-config.jam toolset=clang-ohos --with-regex -j4 variant=release link=static cxxflags="--sysroot=... -target aarch64-linux-ohos" linkflags="--sysroot=..."`
5. 产物: `stage/lib/libboost_regex.a` (706KB, ELF64 AArch64)
6. `conan create .` → conan 配方验证通过 + test_package 编译链接运行通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | b2 编译找不到 assert.h | b2 的 clang-linux.jam 追加 `--target=arm64-pc-linux` 覆盖了 `-target aarch64-linux-ohos` | `cxxflags` 中传入 `--sysroot=<OHOS_SYSROOT>` 修正头文件查找路径 |
| 2 | CMakeDeps 找不到 boost::regex 目标 | CMakeDeps 不单独生成组件目标，boost_regex 库是 boost::boost 目标的一部分 | CMakeLists.txt 只链接 `boost::boost`，其内部已含 `libboost_regex.a` |

## 源码修改

无源码修改，仅修改 conanfile.py 配方。

## 依赖版本

- boost 1.90.0（仅构建 Boost.Regex 子库）
- OHOS SDK 26.0.0.18
- Clang 15.0.4 / libc++

## 验证结果

```bash
# test_package: 编译+链接+运行
[ 50%] Building CXX object CMakeFiles/test_boost.dir/test.cpp.obj
[100%] Linking CXX executable test_boost
[100%] Built target test_boost
1/1 Test #1: test_boost .......................   Passed    0.02 sec
100% tests passed, 0 tests failed out of 1
```

消费者测试包括: boost::regex_search (boost::regex 真实库调用)、boost::optional、boost::lexical_cast、以及 10+ 头文件可包含性检查。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libboost_regex.a | 706 KB | Boost.Regex 静态库 (ELF64 AArch64) |
| 头文件 | ~15534 个 | 完整 Boost 1.90.0 头文件 |

## 注意事项

- 当前只构建了 Boost.Regex 一个子库；其他需要编译的子库可按相同模式扩展 b2 的 `--with-<lib>` 参数。
- b2 构建时需要 `--sysroot` 参数，即使 `-target aarch64-linux-ohos` 被 b2 覆盖也能正确找到 OHOS SDK 头文件。
---

**编译结束**: 2026-07-24
**最终状态**: published
