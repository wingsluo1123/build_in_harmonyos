# OHOS aarch64 CMake toolchain for hashlink exploration
# Used during manual build exploration phase; conan recipe generates its own.

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(CMAKE_C_COMPILER /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang)
set(CMAKE_CXX_COMPILER /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++)
set(CMAKE_AR /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ar)
set(CMAKE_RANLIB /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ranlib)
set(CMAKE_STRIP /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-strip)

set(CMAKE_SYSROOT /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot)

# Cross-compile defaults: target aarch64-linux-ohos
set(CMAKE_C_COMPILER_TARGET aarch64-linux-ohos)
set(CMAKE_CXX_COMPILER_TARGET aarch64-linux-ohos)

# Find libraries/headers ONLY in sysroot; never in host paths
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Allow additional include/lib prefixes from user-local prefix
list(APPEND CMAKE_FIND_ROOT_PATH /storage/Users/currentUser/usr/local)