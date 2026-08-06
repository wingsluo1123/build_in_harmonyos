# libarchive 3.8.7 编译笔记

## 编译信息
- **编译日期**: 2026-08-06
- **编译器**: clang 15.0.4
- **构建系统**: cmake 4.1.2 + ninja 1.13.1
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64

## 主要问题及解决方案

### 问题1: autotools config.status 权限错误
- **问题**: autotools configure 通过但 config.status 报 "Permission denied" 创建临时文件
- **解决**: 改用 CMake 构建系统（libarchive 同时支持 autotools 和 CMake）

### 问题2: CMake 不识别 HarmonyOS 平台
- **问题**: CMake 报 "System is unknown to cmake, create: Platform/HarmonyOS"
- **解决**: 警告但不阻塞，CMake 自动回退到 Linux 平台检测，编译成功

## 编译命令总结

```bash
mkdir build-cmake && cd build-cmake
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DENABLE_TEST=OFF
make -j2
make install
```

## 功能验证
- libarchive.a ✅
- libarchive.so ✅
- archive.h ✅
- archive_entry.h ✅
- bsdcat/bsdtar/bsdcpio/bsdunzip ✅
- libarchive.pc ✅

---
*编译者: OpenDesk Compile Agent*
*日期: 2026-08-06*
---

**编译结束**: 2026-08-06
**最终状态**: built
