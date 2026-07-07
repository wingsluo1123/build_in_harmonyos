# libfido2 1.15.0 适配笔记

## 编译环境
- 构建系统: cmake（init-build 误识别为 autotools）
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: failed

## 编译步骤

### Step 1: init-build
✅ 源码下载并解压成功（已有 tarball）
✅ 归档目录创建成功

### Step 2: 手动 CMake 配置（纠正构建系统识别）
**原因**: init-build 误识别为 autotools，实际为 CMake 项目

配置命令：
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_TOOLS=OFF \
  -DBUILD_MANPAGES=OFF
```

配置成功输出：
- CBOR_VERSION: 0.11.0 ✅
- CRYPTO_VERSION: 3.5.6 ✅
- ZLIB_VERSION: 1.3.1 ✅

### Step 3: make 编译
❌ 失败于 hid_linux.c 和 hid_unix.c

- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 1. 设置PKG_CONFIG_PATH识别依赖
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig

# 2. 创建build目录并配置
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release

# 3. 编译
make -j2

# 4. 安装到staging目录
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libfido2-1.15.0

# 5. 安装到本地
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
<<<<<<< HEAD
| 1 | init-build 误识别构建系统 | CMakeLists.txt 存在，无 configure 脚本 | 手动使用 cmake 配置 |
| 2 | CMake 找不到 HID 后端 | HarmonyOS 未在 src/CMakeLists.txt 平台列表中 | 修改 CMakeLists.txt 添加 HarmonyOS 支持（使用 Linux HID） |
| 3 | 编译失败: libudev.h 缺失 | HarmonyOS 无 libudev（systemd 组件） | ⚠️ **平台架构差异** |
| 4 | 编译失败: ppoll 未声明 | HarmonyOS 不支持 ppoll（仅 poll） | ⚠️ **平台架构差异** |

## 源码修改

**已追踪修改**:
- src/CMakeLists.txt: 添加 `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"` 到 Linux HID 后端条件
  - 目的：让 HarmonyOS 使用 hid_linux.c + hid_unix.c
  - 结果：遇到更深层的平台差异问题（libudev/ppoll）

## 核心失败原因分析

**平台架构不兼容**：

libfido2 在 Linux 平台上依赖：
1. **libudev**：用于与 USB HID 设备通信（设备发现、权限管理）
2. **ppoll()**：用于信号安全的 polling（Linux 特有函数）

HarmonyOS 平台现状：
- ❌ 无 libudev（systemd 组件，HarmonyOS 不使用 systemd）
- ❌ 无 ppoll()（仅有标准 poll()）

**解决路径**（需要深度适配）：
1. 编译 libudev（依赖 systemd 源码）→ 复杂度极高
2. 编译 hidapi（作为 libudev 替代）→ 无预编译包，需手动编译
3. 修改 hid_unix.c 替换 ppoll → 需源码适配
4. 禁用 HID 后端（仅提供 API 库）→ 功能受限

## 依赖版本

- libcbor/0.11.0: ✅ 已安装
- openssl/3.5.6: ✅ 已安装
- zlib/1.3.1: ✅ 已安装
- libudev: ❌ 无预编译包，无系统包（systemd 组件）
- hidapi: ❌ 无预编译包

## 验证结果

编译失败，需要平台深度适配。

## 交付物

无交付物（编译失败）
**失败原因**: 平台架构不兼容 - HarmonyOS 缺少 libudev 和 ppoll 支持
---

**编译结束**: 2026-05-27 20:59
=======
| 1 | HID backend未定义 | CMakeLists.txt未识别HarmonyOS系统 | 修改CMakeLists.txt添加OHOS系统识别，设置HID backend为Linux HID |
| 2 | ppoll系统调用不可用 | HarmonyOS musl libc不支持ppoll | 修改src/hid_unix.c，用poll替代ppoll |
| 3 | libudev.h缺失 | HarmonyOS缺少libudev库 | 创建stub头文件和实现，提供必要的udev函数 |
| 4 | NULL未定义 | 源码缺少stddef.h包含 | 在相关源文件中添加#include <stddef.h> |

## 源码修改

应用了4个补丁文件：

1. **0001-CMakeLists.txt.patch**
   - 添加HarmonyOS系统识别
   - 设置HID backend为Linux HID

2. **0002-src-CMakeLists.txt.patch**
   - 添加libudev stub源文件编译
   - 修复NULL未定义问题

3. **0003-src-hid_unix.c.patch**
   - 用poll替代ppoll系统调用
   - 适配HarmonyOS musl libc

4. **0004-src-stub-udev-libudev.h.patch**
   - 创建libudev stub头文件和实现
   - 提供必要的udev函数定义

## 依赖版本

| 软件 | 版本 |
|------|------|
| libcbor | 0.11.0 |
| openssl | 1.1.1w |
| zlib | 1.3.1 |

## 验证结果

```bash
# 验证fido2-token
/storage/Users/currentUser/usr/local/bin/fido2-token --version
# 输出: fido2-token 1.15.0

# 验证fido2-assert
/storage/Users/currentUser/usr/local/bin/fido2-assert --version
# 输出: fido2-assert 1.15.0

# 验证库文件
ls -lh /storage/Users/currentUser/usr/local/lib/libfido2.so*
# lrwxrwxrwx 1 currentUser currentUser   16 May 19 22:30 libfido2.so -> libfido2.so.1.15.0
# lrwxrwxrwx 1 currentUser currentUser   16 May 19 22:30 libfido2.so.1 -> libfido2.so.1.15.0
# -rwxr-xr-x 1 currentUser currentUser 7.0M May 19 22:30 libfido2.so.1.15.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libfido2-1.15.0-ohos-aarch64.tar.gz | 7.02MB | 预编译包，包含二进制文件和库文件 |

## 注意事项

- HarmonyOS缺少libudev，需要创建stub实现
- ppoll系统调用在HarmonyOS上不可用，需要用poll替代
- HID backend需要在CMake中显式指定为Linux HID
---
**编译结束**: 2026-05-19 22:32
**最终状态**: published
---

**编译结束**: 2026-05-20 12:00
>>>>>>> origin/main
**最终状态**: built
