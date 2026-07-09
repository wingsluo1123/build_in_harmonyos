# libnsgif

## 简介

libnsgif 是 NetSurf 浏览器项目的 GIF 图像解码库，用于解析和解码 GIF 格式图像文件，支持静态 GIF 和动画 GIF。

## OHOS 适配

### 适配要点

- **编译器指定**: 鸿蒙环境无 `cc` 命令，编译时必须设置 `BUILD_CC=clang`
- **归档器指定**: 默认 `ar` 不可用或版本不兼容，需设置 `AR=llvm-ar`
- **install 命令**: `make install` 依赖 GNU `install` 命令，需安装 coreutils 预编译包
- **构建系统**: 使用 NetSurf 自定义 Makefile 构建系统（非 autotools/cmake/meson），需要安装 NetSurf buildsystem 到 `$DEFAULT_PREFIX/share/netsurf-buildsystem/`
- **configure 包装**: 通过补丁新增 `configure` 包装脚本，将 `--prefix` 参数翻译为 Makefile 变量，写入 `Makefile.config`
- **测试目标**: 使用 `make test` 代替 `make check`（NetSurf buildsystem 不提供 check 目标）

### 已知问题

- 鸿蒙环境缺少 CA 证书，下载源码时 SSL 验证失败，需使用 `curl -k` 绕过
- `make install` 前需确保 `install -> ginstall` 符号链接存在（coreutils 提供）

### 与 Linux 的差异

| 项目 | Linux | OpenHarmony |
|------|-------|-------------|
| 默认编译器 | `cc` 可用 | 无 `cc`，需 `BUILD_CC=clang` |
| 归档器 | `ar` 可用 | 需 `AR=llvm-ar` |
| install 命令 | 系统自带 | 需 coreutils 预编译包 |
| 测试目标 | `make check` 或 `make test` | 仅 `make test` |

## 排除与替代

无需要排除的组件。libnsgif 为纯 C 库，编译为静态库（`libnsgif.a`），无共享库依赖。

## 依赖

### 编译依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| NetSurf buildsystem | 1.10 | 共享 Makefile 框架，安装到 `$DEFAULT_PREFIX/share/netsurf-buildsystem/` |
| coreutils | 9.10 | 提供 GNU `install` 命令 |

### 运行依赖

无运行时依赖，libnsgif 编译为静态库。

## 功能验证

### 编译验证

```bash
make PREFIX=$DEFAULT_PREFIX BUILD_CC=clang CC=clang AR=llvm-ar
```
编译成功，生成静态库 `libnsgif.a` 和头文件 `nsgif.h`。

### 测试验证

```bash
make PREFIX=$DEFAULT_PREFIX BUILD_CC=clang CC=clang AR=llvm-ar test
```
输出:
```
Testing GIF decode
Tests:284 Pass:284 Fail:0 Error:0
    TEST: Testing complete
```
全部 284 个 GIF 解码测试通过，0 失败，0 错误。

### 安装验证

```bash
make PREFIX=$DEFAULT_PREFIX BUILD_CC=clang CC=clang AR=llvm-ar install DESTDIR=$TEST_PREFIX
find $TEST_PREFIX -type f
# include/nsgif.h
# lib/pkgconfig/libnsgif.pc
# lib/libnsgif.a
```

## 参考

- **项目主页**: https://www.netsurf-browser.org/projects/libnsgif/
- **源码下载**: https://download.netsurf-browser.org/libs/releases/libnsgif-1.0.0-src.tar.gz
- **NetSurf buildsystem**: https://download.netsurf-browser.org/libs/releases/buildsystem-1.10.tar.gz
- **许可证**: MIT
