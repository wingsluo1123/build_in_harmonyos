# nxp-mfgtools (uuu)

## 简介
NXP Universal Update Utility (uuu) 是 NXP 的 USB 固件烧录工具，用于通过 USB 协议将固件烧录到 NXP i.MX 系列处理器。

## OHOS 适配
- 构建系统: CMake
- 依赖: bzip2, zlib, libusb, zstd, tinyxml2, openssl (均通过 Conan 管理)
- 适配补丁:
  - `stat64`→`stat`: OHOS musl libc 不支持 `stat64`
  - `mmap64`→`mmap`: OHOS musl libc 不支持 `mmap64`
  - CMake 依赖管理: `pkg_check_modules` 替换为 Conan `CMakeDeps` targets

## 依赖
- bzip2/1.0.8
- zlib/1.3.1
- libusb/1.0.27
- zstd/1.5.7
- tinyxml2/11.0.0
- openssl/3.5.6

## 参考
- https://github.com/nxp-imx/mfgtools
