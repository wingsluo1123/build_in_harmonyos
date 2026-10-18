# Universal Update Utility

> NXP i.MX 芯片镜像部署工具（mfgtools 3.0 命令行工具）

## 简介

uuu（Universal Update Utility）是 NXP 为 i.MX 系列芯片提供的镜像部署工具，
由 MFGTools 演进而来（mfgtools 3.0）。它通过 USB（SDPS、SDP、Fastboot、HID
等协议）与芯片 Boot ROM 通信，完成 bootloader 与系统镜像的烧录。

uuu 在 Linux 与 Windows 上用法一致，同一脚本可在双平台运行。本配方构建
上游 `uuu_1.5.243` 标签的命令行工具，产物为单个 `uuu` 可执行文件。

## OHOS 适配要点

- CMake 构建：顶层 `CMakeLists.txt` 仅 `add_subdirectory(libuuu)` 与
  `add_subdirectory(uuu)`，捆绑的 zlib/zstd/tinyxml2/libusb/bzip2 子模块
  不参与构建，全部由系统 Conan 依赖提供。
- 依赖经 `CMakeDeps` + `PkgConfigDeps` 提供：上游 `libuuu` 用
  `pkg_check_modules` 找 libusb-1.0/libzstd/tinyxml2，用
  `find_package` 找 BZip2/OpenSSL；`uuu` 另用 `pkg_check_modules` 找 zlib。
- `FindBZip2` 模块与 `CMakeDeps` 生成的小写包名不匹配，配方在
  `generate()` 中显式设置 `BZIP2_INCLUDE_DIR` / `BZIP2_LIBRARIES`。
- `libuuu/gen_ver.sh` 优先读取源码根 `.tarball-version`（无需 git），
  配方在 `build()` 前写入版本号，`uuu` 无参输出的版本字符串稳定。
- OHOS 产物签名：`bin/uuu` 为 ELF 可执行文件，经
  `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`
  自签后方可运行。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| bzip2 | 1.0.8 | libuuu FindBZip2（显式路径提示） |
| libusb | 1.0.27 | libuuu/uuu USB 传输（pkg-config libusb-1.0） |
| openssl | 1.1.1w | libuuu OpenSSL 加密（find_package） |
| tinyxml2 | 10.0.0 | libuuu XML 解析（pkg-config tinyxml2） |
| zstd | 1.5.6 | libuuu zstd 解压（pkg-config libzstd） |
| zlib | 1.3.1 | uuu/zip inflate（pkg-config zlib） |

## 功能验证

```bash
uuu | head -5
uuu -h | head -10
uuu -udev | head -5
```

## 参考

- [官方仓库](https://github.com/nxp-imx/mfgtools)
- [1.5.243 发布页](https://github.com/nxp-imx/mfgtools/releases/tag/uuu_1.5.243)
- [NXP UUU 文档](https://docs.nxp.com/bundle/UG10163/page/topics/downloading_uuu.html)
