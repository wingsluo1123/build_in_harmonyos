# libkeyfinder 2.2.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: https://github.com/mixxxdj/libkeyfinder/archive/refs/tags/2.2.8.tar.gz
2. 应用补丁: 0001-CMakeLists.txt.patch (使用 conan 的 fftw cmake 配置)
3. conan install fftw/3.3.10.2 获取依赖
4. cmake 配置: -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=ON
5. make 编译
6. make install 安装
7. 二进制签名 (OHOS 平台)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(FFTW3) 找不到 fftw | libkeyfinder 使用自定义 FindFFTW3.cmake 模块，与 conan 的 CMakeDeps 生成的 fftw-config.cmake 不匹配 | 修改 CMakeLists.txt 使用 find_package(fftw) 和 fftw::fftw |
| 2 | 测试编译失败 | 上游使用 FetchContent 下载 Catch2，在 OHOS 上 git clone 失败 | 设置 BUILD_TESTING=OFF 禁用测试 |
| 3 | 测试运行时找不到 libkeyfinder.so.2 | 共享库未签名，OHOS 平台要求 ELF 签名 | 在 package() 中添加 _sign_binaries() 方法 |

## 源码修改

- CMakeLists.txt: 移除 list(APPEND CMAKE_MODULE_PATH) 和 find_package(FFTW3)，改为 find_package(fftw) 和 fftw::fftw

## 依赖版本

- fftw/3.3.10.2 (from ohpcd registry)

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# G0-G4 all PASS
# Test package: test_libkeyfinder PASS
```

## 注意事项

- 上游测试使用 Catch2 via FetchContent，在 OHOS 上无法运行，已禁用
- 共享库需要在 OHOS 上进行二进制签名
