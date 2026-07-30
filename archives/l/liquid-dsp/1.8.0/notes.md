# liquid-dsp v1.8.0 适配笔记

## 编译环境
- 构建系统: cmake (cmake_minimum_required VERSION 3.10)
- 编译日期: 2026-07-28
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64)
- cmake: 4.1.2
- make: GNU Make 4.4.1
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

```bash
# 1. CMake 配置
cd $BUILD_SRC_DIR && mkdir build && cd build
cmake ../ \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_STATIC_LIBS=ON \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_BENCHMARKS=OFF \
  -DBUILD_AUTOTESTS=OFF \
  -DFIND_FFTW=OFF \
  -DFIND_SIMD=OFF \
  -DFIND_THREADS=OFF \
  -DENABLE_SIMD=OFF \
  -DBUILD_SANDBOX=OFF \
  -DBUILD_DOC=OFF \
  -DENABLE_LOGGING=OFF

# 2. 编译
make -j2

# 3. 安装 (staging)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 检测系统 "System is unknown to cmake" | OHOS 不在 cmake 平台列表中 | 非阻塞警告，cmake 自动选择 HarmonyOS 名称，编译正常 |
| 2 | make: jobserver mkfifo: Operation not permitted | OHOS 文件系统限制 | 非阻塞警告，编译正常完成 |

## 源码修改

无。零补丁编译通过（纯数学库，无平台相关代码）。

## 依赖版本

无外部依赖。仅依赖 libc (c) 和 libm (m)，系统自带。

## 验证结果

```bash
# 验证安装产物
# libliquid.a 已安装
# header liquid.h 已安装
# cmake config 文件已安装
# pkg-config 文件已安装
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libliquid.a | ~2.1MB | 静态库 (Release, aarch64) |
| include/liquid/liquid.h | ~1.1MB | 主头文件 |
| lib/cmake/liquid-static/* | - | CMake 配置文件 |
| lib/pkgconfig/liquid-dsp.pc | - | pkg-config 文件 |

## 注意事项

- build context 标记为 autotools 但实际是 cmake 构建系统（v1.8.0 迁移到 cmake），conanfile.py 已修正为 CMake
- CMake 库名称是 `liquid`，CMake 包名是 `liquid-static`（因为 BUILD_SHARED_LIBS=OFF）
- pkg-config 名是 `liquid-dsp`
- 纯数学库，无需深度适配验证 (R40)
- 非系统同名库，默认动态链接由Conan管理 (R26)
