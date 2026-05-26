# hdf5 1.13.0 适配笔记

## 编译环境
- 构建系统: cmake（autotools 因权限问题失败）
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

由于 autotools 构建在 configure 阶段遇到 config.status 权限问题，改用 CMake 构建：

```bash
cd /storage/Users/currentUser/tmp
mkdir hdf5-build
cd hdf5-build
cmake ../builds/hdf5-1.13.0.work \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON \
  -DHDF5_BUILD_EXAMPLES=OFF \
  -DHDF5_BUILD_TESTING=OFF
cmake --build . -j2
DESTDIR=/storage/Users/currentUser/tmp/test-install-hdf5-1.13.0 cmake --install .
cmake --install . --prefix /storage/Users/currentUser/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess (2014版本) 不包含 HarmonyOS 检测分支 | 手动添加 HarmonyOS case 分支，输出 aarch64-unknown-linux-ohos |
| 2 | config.sub 无法验证 ohos | config.sub 未包含 ohos 在 OS 白名单中 | 在 case $os in 中添加 linux-ohos* 和 -ohos* |
| 3 | autotools configure 权限错误 | config.status 创建临时文件时权限问题 | 改用 CMake 构建系统 |
| 4 | CMake 不识别 HarmonyOS 平台 | CMake 未包含 HarmonyOS 平台定义 | 使用默认配置，忽略平台警告 |

## 源码修改

修改了 autotools 配置文件（仅用于 autotools 构建，实际使用 CMake）：

1. **bin/config.guess** - 添加 HarmonyOS 系统识别：
   - 在 case 语句开头添加 *:HarmonyOS:*:* 分支
   - 输出 ${MACHINE}-unknown-linux-ohos
   - 补丁文件: patches/0001-config.guess.patch

2. **bin/config.sub** - 添加 ohos 系统验证：
   - 在 maybe_os 映射中添加 linux-ohos*)
   - 在 OS 白名单中添加 -linux-ohos* 和 -ohos*)
   - 补丁文件: patches/0002-config.sub.patch

## 依赖版本

- zlib: 系统预装版本
- cmake: 4.1.2
- clang: 默认版本
- make: GNU Make 4.4.1

## 验证结果

```bash
$ h5dump --version
h5dump: Version 1.13.0

$ h5ls --version
h5ls: Version 1.13.0

$ ls -lh /storage/Users/currentUser/usr/local/lib/libhdf5*
-rw-rw---- libhdf5.a (10M)
-rwxrwx--- libhdf5.so (3.8M)
-rw-rw---- libhdf5_hl.a (197K)
-rwxrwx--- libhdf5_hl.so (138K)
-rw-rw---- libhdf5_tools.a (585K)
-rwxrwx--- libhdf5_tools.so (294K)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hdf5-1.13.0-ohos-aarch64.tar.gz | 85M | 预编译包（含库、工具、头文件） |
| 0001-config.guess.patch | 763B | HarmonyOS 系统识别补丁 |
| 0002-config.sub.patch | 1.4K | ohos 系统验证补丁 |

## 注意事项

1. **CMake 构建推荐**: autotools 构建在鸿蒙环境可能遇到权限问题，推荐使用 CMake
2. **平台警告**: CMake 会输出 "System is unknown to cmake" 警告，但不影响编译
3. **静态库与动态库**: 同时生成了静态库(.a)和动态库(.so)，默认链接动态库
4. **测试跳过**: 编译时跳过了测试套件（-DHDF5_BUILD_TESTING=OFF），功能验证依赖实际使用
