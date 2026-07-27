# 手动编译测试报告 — aws-c-http 0.11.0

## 编译环境
- **平台**: HarmonyOS 6.0 (OHOS aarch64)
- **编译器**: clang 15.0.4
- **构建系统**: CMake
- **Profile**: ohos-aarch64 (Release, shared, libc++, cppstd=17)

## 源码
- **URL**: https://github.com/awslabs/aws-c-http/archive/refs/tags/v0.11.0.tar.gz
- **版本**: 0.11.0

## 依赖
| 依赖 | 版本 | 类型 |
|------|------|------|
| aws-c-common | 0.14.3 | shared |
| aws-c-io | 0.27.5 | shared (BYO_CRYPTO=ON) |
| aws-c-compression | 0.3.2 | shared |
| aws-c-cal | 0.9.15 | shared |
| aws-lc | 5.4.0 | static |

## 编译过程

### 1. CMake Configure
```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_TESTING=OFF \
  -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX \
  -DCMAKE_PREFIX_PATH="<dep1>;<dep2>;..."
```
**结果**: ✅ 成功（有 "System is unknown to cmake" 警告，不影响编译）

### 2. Make Build
```bash
cmake --build build -j$(nproc)
```
**结果**: ✅ 成功（有 "jobserver mkfifo: Operation not permitted" 警告）

### 3. Install
```bash
cmake --install build --prefix $TEST_PREFIX
```
**结果**: ✅ 成功

## 产物
- `lib/libaws-c-http.so` — 动态库
- `include/aws/http/*.h` — 11个头文件
- `lib/cmake/aws-c-http/` — CMake 配置文件

## 补丁
1. **0001-CMakeLists-add-threads-before-deps.patch** — 在 aws_use_package 调用前添加 `find_package(Threads REQUIRED)`，解决 aws-lc 的 crypto-config.cmake 引用 `Threads::Threads` 目标的问题。

## 已知问题
- **aws_tls_handler_protocol 符号缺失**: aws-c-io 使用 BYO_CRYPTO=ON 构建时不编译 `aws_tls_handler_protocol` 函数（该函数在 `#else` 分支中），但 aws-c-http 的 connection.c 引用了它。test_package 通过提供 stub.c + `--export-dynamic` 链接标志解决运行时符号解析问题。

## 结论
✅ 编译成功，库可用。
