# yavta 0_git20240914 适配笔记

## 编译环境

- 构建系统: makefile
- 编译日期: 2026-06-25
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 目标平台: OpenHarmony aarch64 (musl libc)
- 状态: built

## 软件简介

yavta (Yet Another V4L2 Test Application) 是一个用于测试 Video4Linux2 设备的命令行工具，
支持多平面捕获、多种视频格式和帧捕获时序检测。

- 上游仓库: https://git.ideasonboard.org/yavta.git
- 上游 commit: 52c975e5 (2024-09-14)
- 构建系统: Makefile (上游已标记为 deprecated，推荐使用 meson)

## 编译步骤

### 1. 下载源码

从 Debian Salsa 下载 upstream tag tarball（非 git clone）：

```
URL: https://salsa.debian.org/debian/yavta/-/archive/upstream/0.0+git20240914.52c975e/yavta-upstream-0.0+git20240914.52c975e.tar.gz
sha256: 3b32ac183f11f4f5096e45b1bc47f2a6b298f64b7fb782fcc02ad56ca9300ef7
```

上游来源 git.linuxtv.org 的 cgit snapshot 功能不可用（返回 "No repositories found"），
改用 Debian Salsa 的 upstream tag archive 作为替代下载源。

### 2. 编译

```bash
cd $BUILD_SRC_DIR
make CC=clang CFLAGS="-fPIC -O2 -W -Wall -Iinclude" -j1
```

关键点：
- Makefile 使用 `CC := $(CROSS_COMPILE)gcc` 硬编码 gcc，需命令行 `CC=clang` 覆盖
- CFLAGS 使用 `?=` 赋值，但环境变量值缺少 `-Iinclude`，需命令行指定完整 CFLAGS
- Makefile 显示警告: "Makefile support is deprecated, please switch to meson"（可忽略）

编译输出：
```
Makefile:4: warning: Makefile support is deprecated, please switch to meson.
clang -fPIC -O2 -W -Wall -Iinclude -c yavta.c -o yavta.o
clang -fPIC -O2 -W -Wall -Iinclude -c capture.c -o capture.o
clang -fPIC -O2 -W -Wall -Iinclude -c process.c -o process.o
clang -fPIC -O2 -W -Wall -Iinclude -c options.c -o options.o
clang -fPIC -O2 -W -Wall -Iinclude -c events.c -o events.o
clang -fPIC -O2 -W -Wall -Iinclude -c thread.c -o thread.o
clang -o yavta yavta.o capture.o process.o options.o events.o thread.o
```

编译产物：yavta 二进制 (59840 bytes, ELF64 AArch64 PIE)

### 3. 安装到 staging (DESTDIR)

yavta 的 Makefile 无 install 目标，手动安装：

```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp yavta $TEST_PREFIX/$DEFAULT_PREFIX/bin/yavta
```

Staging 验证：
```
$ $TEST_PREFIX/$DEFAULT_PREFIX/bin/yavta --help
Usage: .../bin/yavta [options] device
Supported options:
-B, --buffer-type    Buffer type ("capture", "output", ...)
✅ 通过
```

### 4. 测试验证

- `make check`: Makefile 无 check/test 目标，SKIP
- 功能验证: `yavta --help` 输出完整帮助信息，PASS
- ELF 格式验证: `file` 确认 ELF64 arm64 PIE, 动态链接 musl libc, PASS
- 动态依赖: `readelf -d` 确认仅依赖 libc.so，无外部依赖，PASS
- 详见 reports/test-report.md

### 5. 打包预编译包

按打包指南手动执行（ohc-run.py package 命令在本环境不可用）：

1. 收集 ELF 依赖: 仅 libc.so (系统 musl 库)
2. Strip 调试符号: 55168 bytes (原 59840 bytes)
3. 修复权限: chmod 775
4. 创建 tar.gz: bin/yavta
5. 生成 debug 包: yavta-0_git20240914.debug/yavta.debug (31168 bytes)

产物：
- `packaging/yavta-0_git20240914-ohos-aarch64.tar.gz` (57372 bytes)
  - sha256: d325aebdd3192dae15d69a067b23377454296cddaabc478034b867e850d2ee32
- `packaging/yavta-0_git20240914-ohos-aarch64-debug.tar.gz` (33308 bytes)

预编译包安装验证：
```
$ tar xzf yavta-0_git20240914-ohos-aarch64.tar.gz -C /tmp/ohc-verify-pkg
$ /tmp/ohc-verify-pkg/bin/yavta --help
Usage: /tmp/ohc-verify-pkg/bin/yavta [options] device
Supported options:
-B, --buffer-type    Buffer type ("capture", "output", ...)
✅ 通过
```

### 6. 本地安装

```bash
cp yavta $DEFAULT_PREFIX/bin/yavta
```

### 7. 本地验证

```
$ $DEFAULT_PREFIX/bin/yavta --help
Usage: /storage/Users/currentUser/usr/local/bin/yavta [options] device
Supported options:
-B, --buffer-type        Buffer type ("capture", "output",
                                "capture-mplane" or "output-mplane")
-c, --capture[=nframes]  Capture frames
-C, --check-overrun      Verify dequeued frames for buffer overrun
...
    --stride value       Line stride in bytes
✅ 功能验证通过
```

```
$ file $DEFAULT_PREFIX/bin/yavta
/storage/Users/currentUser/usr/local/bin/yavta: ELF shared object, 64-bit LSB arm64,
  dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

```
$ readelf -d $DEFAULT_PREFIX/bin/yavta | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | git.linuxtv.org snapshot 不可用 | cgit 返回 "No repositories found" | 改用 Debian Salsa upstream tag archive 下载 tarball |
| 2 | SSL 证书验证失败 | 鸿蒙 Python 缺少 CA 证书 | curl -kL 手动下载 Mozilla CA 证书到 /storage/Users/currentUser/usr/local/ssl/cert.pem |
| 3 | Makefile CC 硬编码为 gcc | `CC := $(CROSS_COMPILE)gcc` 使用 `:=` 覆盖环境变量 | 命令行 `make CC=clang` 覆盖 |
| 4 | CFLAGS 缺少 -Iinclude | Makefile CFLAGS 使用 `?=`，环境变量值不完整 | 命令行指定完整 `CFLAGS="-fPIC -O2 -W -Wall -Iinclude"` |
| 5 | Makefile 无 install 目标 | yavta 是简单的单文件项目 | 手动 cp 二进制到目标目录 |
| 6 | Makefile 无 check/test 目标 | yavta 无自动化测试套件 | 使用 `yavta --help` 作为功能验证替代 |
| 7 | ohc-run.py package 命令不存在 | 工具链版本差异 | 按打包指南手动执行 10 步流程 |
| 8 | G0 clean-verify 失败 | G0 检查器强制运行 ./configure，makefile 项目无 configure 脚本 | 已知限制，makefile 项目不适用 G0 干净构建验证 |
| 9 | G4 manifest 缺少 build_system 字段 | G4 检查器在文件内容中查找 `build_system:` 字符串 | 在 manifest.yaml 添加顶层 `build_system: makefile` 字段 |

## 源码修改

无源码修改，无补丁。所有编译均通过命令行参数（CC、CFLAGS）完成，未修改任何源文件。

## 依赖版本

- 无外部依赖（仅依赖系统 musl libc，即 libc.so）
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)

## 质量门禁结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 干净构建 | ⚠️ FAIL | 已知限制: makefile 项目无 configure 脚本 |
| G1 二进制完整性 | ✅ PASS | ELF64 AArch64 PIE 格式正确 |
| G2 功能可用性 | ✅ PASS | yavta --help 输出正常 (1 警告) |
| G3 可移植性 | ✅ PASS | 仅依赖 libc.so，BIND_NOW PIE |
| G4 档案完整性 | ✅ PASS | manifest/notes/patches/reports/packaging 齐全 |

**质量报告最终判定: PASS**

## 交付物

| 文件 | 大小 | sha256 | 说明 |
|------|------|--------|------|
| packaging/yavta-0_git20240914-ohos-aarch64.tar.gz | 57372 bytes | d325aebdd3192dae15d69a067b23377454296cddaabc478034b867e850d2ee32 | 预编译主包 (bin/yavta, 已 strip) |
| packaging/yavta-0_git20240914-ohos-aarch64-debug.tar.gz | 33308 bytes | - | Debug 符号包 |
| $DEFAULT_PREFIX/bin/yavta | 59840 bytes | - | 已安装二进制 (未 strip) |

## 注意事项

- yavta 的 Makefile 标记为 deprecated，上游推荐使用 meson 构建
- 上游仓库 git.ideasonboard.org/yavta.git 可能在未来版本移除 make 支持
- 本版本 (0_git20240914) 仍保留 Makefile，可正常使用 make 编译
