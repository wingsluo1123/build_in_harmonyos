# nxp-mfgtools 1.5.243 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cd $BUILD_SRC_DIR
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake
cmake --build build
cmake --install build --prefix $TEST_PREFIX
```

## 遇到的问题与解决方案

### 1. stat64/mmap64 不可用
OHOS 使用 musl libc，不支持 `stat64` 和 `mmap64` 函数。
- `buffer.cpp`: 添加 `#elif defined(__OHOS__)` 使用 `stat` 替代 `stat64`
- `buffer.h`: 添加 `__OHOS__` 到 `mmap64→mmap` 的条件定义

### 2. pkg_check_modules 依赖解析
上游使用 `pkg_check_modules` 查找系统依赖，OHOS 无 pkg-config 文件。
- 替换为 Conan `CMakeDeps` 生成的 `find_package` 调用
- 使用 cmake target (`bzip2::bzip2`, `libusb-1.0::libusb-1.0` 等) 链接库

### 3. OpenSSL 必需
`base64_encode` 函数定义在 `#ifdef UUUSSL` 块内，但在块外被使用。
必须找到 OpenSSL 并定义 `UUUSSL` 才能编译通过。

### 4. CMake imported targets 目录作用域
`find_package(bzip2)` 在 `libuuu/CMakeLists.txt` 中调用，
但 `bzip2::bzip2` target 在 `uuu/CMakeLists.txt` 中不可见。
需要在两个 CMakeLists.txt 中都调用 `find_package`。

### 5. gen_ver.sh 需要 .tarball-version
非 git 源码包缺少版本信息，需要创建 `.tarball-version` 文件。

---

**编译结束**: 2026-08-07
**最终状态**: built
