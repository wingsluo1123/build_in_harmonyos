# cpr 1.14.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 下载源码
python3 scripts/ohc-run.py init-build cpr 1.14.2 --url=https://github.com/libcpr/cpr/archive/refs/tags/1.14.2.tar.gz

# 2. 创建 OHOS CMake 工具链文件
cat > ohos-toolchain.cmake << 'EOF'
set(CMAKE_SYSTEM_NAME OHOS)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_C_COMPILER /data/service/hnp/bin/clang)
set(CMAKE_CXX_COMPILER /data/service/hnp/bin/clang++)
set(CMAKE_AR /data/service/hnp/bin/llvm-ar)
set(CMAKE_RANLIB /data/service/hnp/bin/llvm-ranlib)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
EOF

# 3. 构建 libcurl 8.13.0 作为依赖
# 由于 GitHub 不可访问，需从 curl.se 下载 curl 源码
# 修改 curl_config.h 禁用 HAVE_LINUX_TCP_H 解决 sockaddr_storage 重定义冲突
cmake .. -DCMAKE_TOOLCHAIN_FILE=ohos-toolchain.cmake -DHTTP_ONLY=ON -DCURL_USE_OPENSSL=OFF -DBUILD_CURL_EXE=OFF -DBUILD_SHARED_LIBS=OFF
make -j4 && make install

# 4. 构建 libcpr
cmake .. \
  -DCMAKE_TOOLCHAIN_FILE=ohos-toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DCPR_USE_SYSTEM_CURL=ON \
  -DCURL_ROOT=/path/to/curl-install \
  -DCPR_ENABLE_SSL=OFF \
  -DCPR_CURL_USE_LIBPSL=OFF \
  -DCPR_BUILD_TESTS=OFF
make -j4 && make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 无法访问，FetchContent 下载 curl/zlib-ng 失败 | 环境网络限制，无法连接 github.com | 从 curl.se 下载 curl 源码，使用 `CPR_USE_SYSTEM_CURL=ON` 复用预构建 curl |
| 2 | curl 编译时 `sockaddr_storage` 重定义 | OHOS sysroot 中 `<linux/socket.h>` 和 `<sys/socket.h>` 同时定义 `sockaddr_storage` | 编译时添加 `-D_UAPI_LINUX_SOCKET_H`，并禁用 `HAVE_LINUX_TCP_H` |
| 3 | CMake 配置时 OpenSSL 未找到 | 环境缺少 OpenSSL 开发头文件 | 当前暂用 `CPR_ENABLE_SSL=OFF` 跳过，后续可构建 OpenSSL for OHOS 后启用 |
| 4 | `/tmp` 只读 | 鸿蒙平台安全限制 | 使用 `TMPDIR=/storage/Users/currentUser/tmp` 替代 |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libcurl | 8.13.0 | 从源码构建，静态链接，无 SSL |
| OHOS clang | 15.0.4 | aarch64-linux-ohos target |
| cmake | 4.1.2 | 构建系统 |
| make | 4.4.1 | 构建工具 |

## 验证结果

```bash
# 验证库文件
file /storage/Users/currentUser/usr/local/lib/libcpr.a
# 输出: libcpr.a: ar archive

# 验证头文件
ls /storage/Users/currentUser/usr/local/include/cpr/ | wc -l
# 输出: 54

# 验证符号
/data/service/hnp/bin/llvm-nm /storage/Users/currentUser/usr/local/lib/libcpr.a | grep " T " | head -5
# 输出: cpr::AcceptEncoding, cpr::GlobalThreadPool 等
```

## 注意事项

- SSL 支持当前已禁用，后续需要配合 OpenSSL for OHOS 重新编译启用
- 因 conan 远程仓不可用，未完成 conan-verify 验证
- 建议在 conan 远程仓可用后重新执行 conan create 验证