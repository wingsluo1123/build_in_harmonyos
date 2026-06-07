#!/bin/bash
# abseil-cpp 20260107.1 构建提示脚本
# 用于 G0 干净构建验证

set -e

# 创建 toolchain 文件
cat > toolchain-ohos.cmake << 'EOF'
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)
set(CMAKE_EXE_LINKER_FLAGS "-fuse-ld=bfd")
set(CMAKE_SHARED_LINKER_FLAGS "-fuse-ld=bfd")
set(CMAKE_MODULE_LINKER_FLAGS "-fuse-ld=bfd")
EOF

# CMake 配置
cmake -B build \
  -DCMAKE_TOOLCHAIN_FILE=toolchain-ohos.cmake \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_CXX_STANDARD_REQUIRED=ON \
  -DABSL_BUILD_TESTING=OFF

# 编译
make -j4

# 安装
make install DESTDIR=$TEST_PREFIX