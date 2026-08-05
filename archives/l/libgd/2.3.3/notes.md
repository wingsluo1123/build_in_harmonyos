# libgd 2.3.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang/clang++ (15.0.4)
- 目标平台: HarmonyOS PC (os=OHOS os.version=6.0 arch=armv8)
- 状态: built（conan create -pr:h=ohos-aarch64 -pr:b=default 通过）

## 编译步骤

1. `conan create archives/l/libgd/2.3.3/conanfile.py -pr:h=$PROFILE -pr:b=default --build=missing`
2. CMake configure: libgd 使用 CMake 内置 find_package(ZLIB/PNG/JPEG/Freetype)，通过 Conan CMakeToolchain cache_variables 预设各依赖的 INCLUDE_DIR 和 LIBRARY 变量
3. CMake build: 编译 libgd.so (SONAME libgd.so.3) + 工具程序 (gdtopng, pngtogd, webpng, annotate 等)
4. CMake install: 安装 lib/libgd.so*, include/gd.h 等 12 个头文件, lib/pkgconfig/gdlib.pc, bin/ 工具

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | zlib 版本冲突 | libpng/1.6.58 要求 zlib/1.3.1.1，recipe 写了 1.3.1 | 改 requires 为 zlib/1.3.1.1 |
| 2 | CMake "System is unknown to cmake" | OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 不认 | 仅警告，configure 正常完成，不影响构建 |
| 3 | 链接时找不到共享依赖 | libpng16.so/libfreetype.so 在 conan 包目录，链接器找不到 | LDFLAGS 加 -L + -rpath-link 指向依赖 lib 目录 |
| 4 | OHOS 共享库无 SONAME | CMake 在 OHOS 下不自动设置 -Wl,-soname | CMakeUserMakeRulesOverride 注入 ohos-cmake-rules.cmake |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- libpng/1.6.58
- libjpeg/10
- freetype/2.14.3
- zlib/1.3.1.1

## 验证结果

```
libgd: dlopen libgd.so ok
libgd: gdImageCreate(64, 32) ok
libgd: gdImageDestroy ok
libgd: version 2.3.3
libgd: test PASSED
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libgd.so | 共享库 (SONAME libgd.so.3) |
| lib/libgd.so.3 | SONAME 软链 |
| lib/libgd.so.3.0.11 | 版本化共享库 |
| lib/pkgconfig/gdlib.pc | pkg-config 文件 |
| include/gd.h + 11 others | 公共头文件 |
| bin/gdtopng, pngtogd, webpng, annotate 等 | 工具程序 |
| licenses/COPYING | 许可证 |
