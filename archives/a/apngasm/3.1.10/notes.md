# apngasm 3.1.10 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 依赖安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libpng 1.6.43
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- boost 1.84.0
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- zlib 1.3.1

# libpng 需要重新编译带 -fPIC 和 NEON 支持
cd libpng-1.6.43 && mkdir build && cd build
cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_C_FLAGS="-fPIC -O2" \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DZLIB_ROOT=$HOME/usr/local \
  -DPNG_SHARED=OFF -DPNG_STATIC=ON -DPNG_TESTS=OFF \
  -DCMAKE_SYSTEM_PROCESSOR=aarch64
make -j2 && make install

# boost 需要编译 program_options, regex, system 库
# (pre-compiled boost package only includes headers)
b2 --with-program_options --with-regex --with-system link=static \
  cxxflags="-fPIC -O2 -std=c++20 --target=aarch64-unknown-linux-ohos --sysroot=$SYSROOT -I$CXX_HEADERS -D__OHOS__" \
  toolset=clang -j2 stage

# apngasm 编译
cd apngasm-3.1.10.work && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX -DBOOST_ROOT=$HOME/usr/local \
  -DZLIB_ROOT=$HOME/usr/local
make -j2 && make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | boost pthread_setcancelstate 未定义 | OHOS 不支持 pthread_cancel | 修改 boost/core/detail/sp_thread_sleep.hpp 添加 __OHOS__ 守卫 |
| 2 | libpng 未编译 -fPIC | pre-compiled 包未带 -fPIC | 从源码重新编译 libpng 带 -fPIC |
| 3 | libpng NEON 符号未定义 | CMake 未检测到 aarch64 平台 | 手动编译 ARM NEON 源文件并添加到静态库 |
| 4 | boost pre-compiled 包只有头文件 | cmd-pkgs boost 包不包含编译库 | 从 boost 源码编译 program_options/regex/system |

## 依赖版本

- libpng/1.6.43
- boost/1.84.0
- zlib/1.3.1

## 验证结果

```bash
$ ./bin/apngasm --version
APNG Assembler v3.1.10 (frontend v3.1.10)
```

## 注意事项

- boost pre-compiled 包只含头文件，需要从源码编译 program_options、regex、system 库
- libpng 需要手动添加 ARM NEON 源文件到静态库
- __OHOS__ 宏由编译器自动定义，Conan 构建时不需要额外 patch
---

**编译结束**: 2026-08-09 04:55
**最终状态**: built
