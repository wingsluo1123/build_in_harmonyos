# libnsgif 1.0.0 适配笔记

## 编译环境
- 构建系统: NetSurf 自定义 Makefile 构建系统（非 autotools/cmake/meson）
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载并安装 NetSurf buildsystem 1.10 到 `$DEFAULT_PREFIX/share/netsurf-buildsystem/`
   - buildsystem 是 NetSurf 项目共享的 Makefile 框架，包含 Makefile.tools、Makefile.top 等文件
   - libnsgif 的 Makefile 通过 `NSSHARED ?= $(PREFIX)/share/netsurf-buildsystem` 引用它

2. 编译命令（无 ./configure 脚本，直接 make）：
   ```bash
   make PREFIX=$DEFAULT_PREFIX BUILD_CC=clang CC=clang AR=llvm-ar
   ```
   - `PREFIX=$DEFAULT_PREFIX`：指定安装前缀，同时让 Makefile 找到 buildsystem
   - `BUILD_CC=clang`：系统没有 `cc` 命令，需显式指定 build 编译器
   - `AR=llvm-ar`：使用 llvm-ar 替代默认 ar

3. 安装到 staging（DESTDIR 模式，R20）：
   ```bash
   make PREFIX=$DEFAULT_PREFIX BUILD_CC=clang CC=clang AR=llvm-ar install DESTDIR=$TEST_PREFIX
   ```

4. 测试：
   ```bash
   make PREFIX=$DEFAULT_PREFIX BUILD_CC=clang CC=clang AR=llvm-ar test
   ```
   - NetSurf buildsystem 没有 `make check`，使用 `make test` 代替
   - 结果：Tests:284 Pass:284 Fail:0 Error:0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败，无法下载源码 | 鸿蒙环境缺少 CA 证书 | 使用 curl -k 下载后手动放置到 `$TMPDIR/builds/` |
| 2 | `make` 失败：找不到 `Makefile.tools` | 缺少 NetSurf buildsystem 依赖 | 下载 buildsystem-1.10 并安装到 `$DEFAULT_PREFIX/share/netsurf-buildsystem/` |
| 3 | `make` 失败：`cc` 命令不存在 | `BUILD_CC` 默认为 `cc`，鸿蒙环境未提供 | 传入 `BUILD_CC=clang` |
| 4 | `make install` 失败：`install: No such file or directory` | 系统没有 `install` 命令 | 安装 coreutils 9.10 预编译包（R18），创建 `install -> ginstall` 符号链接 |
| 5 | `make check` 失败：No rule to make target 'check' | NetSurf buildsystem 不使用 `check` 目标 | 使用 `make test` 代替 |

## 源码修改

libnsgif 1.0.0 的 C 源码逻辑无需任何适配即可在 OpenHarmony 平台上编译。但有 2 个构建系统层面的补丁用于适配鸿蒙环境：

| 补丁文件 | 修改内容 | 类型 |
|----------|----------|------|
| 0001-Makefile.patch | 修改 Makefile，添加 `-include Makefile.config`，使 Makefile 能读取 configure 包装脚本生成的配置 | 构建系统适配（非 C 源码修改） |
| 0002-configure.patch | 新增 `configure` 包装脚本，将 `--prefix` 参数翻译为 Makefile 变量（PREFIX、BUILD_CC、AR），写入 `Makefile.config` | 构建系统适配（新增文件） |

> 说明：这两个补丁是构建系统适配，不涉及任何 C 源码逻辑修改。libnsgif 的 GIF 解码源码（`src/libnsgif.c` 等）在 OpenHarmony 上无需修改即可编译。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| NetSurf buildsystem | 1.10 | 共享 Makefile 框架，安装到 `$DEFAULT_PREFIX/share/netsurf-buildsystem/` |
| coreutils | 9.10 | 提供 `install` 命令（预编译包） |

## 验证结果

```bash
# Staging 验证
$ find $TEST_PREFIX -type f
include/nsgif.h
lib/pkgconfig/libnsgif.pc
lib/libnsgif.a

# 测试结果
$ make test
Testing GIF decode
Tests:284 Pass:284 Fail:0 Error:0
TEST: Testing complete
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libnsgif-1.0.0-ohos-aarch64.tar.gz | 35 KB | 预编译包（静态库 + 头文件 + pkg-config） |

## 注意事项

- libnsgif 使用 NetSurf 自定义 Makefile 构建系统，不使用 autotools/cmake
- 编译时必须设置 `BUILD_CC=clang`（或创建 `cc` 符号链接），否则 `BUILD` 平台检测失败
- 编译时必须设置 `AR=llvm-ar`，默认 `ar` 可能不可用或版本不兼容
- `make install` 需要 GNU `install` 命令，通过安装 coreutils 预编译包解决
- 测试使用 `make test` 而非 `make check`
- buildsystem 不是预编译包，需手动下载安装到 `$DEFAULT_PREFIX/share/netsurf-buildsystem/`
---

**编译结束**: 2026-06-25 11:46
**最终状态**: built
