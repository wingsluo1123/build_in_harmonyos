# gnome-autoar 0.4.5 编译笔记

## 编译信息
- **编译日期**: 2026-08-06
- **编译器**: clang 15.0.4
- **构建系统**: meson 1.11.1 + ninja 1.13.1
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64

## 依赖
- glib 2.84.0.1 (from conan remote ohpcd)
- libarchive 3.8.7 (locally built and conan-published, separate PR)

## 主要问题及解决方案

### 问题1: 源码解压失败 (绝对路径符号链接)
- **问题**: tarball 中 tests/files/extract/test-symlink-parent/reference/arextract 是指向 /tmp 的绝对路径符号链接, Python tarfile 拒绝解压
- **解决**: 使用 tar --absolute-names 手动解压

### 问题2: glib pkg-config 缺少 glib_mkenums 变量
- **问题**: Conan PkgConfigDeps 生成的 glib-2.0.pc 缺少 glib_mkenums 变量, 导致 meson gnome.mkenums() 失败
- **解决**: 在 conanfile.py generate() 中添加 _fix_glib_mkenums() 方法, 手动在 glib-2.0.pc 中添加 glib_mkenums 变量

### 问题3: meson 找不到 llvm-ar
- **问题**: Conan MesonToolchain 生成的 native file 缺少 ar/ranlib, meson 报 "Unknown linker(s): [['llvm-ar']]"
- **解决**: 在 conanfile.py generate() 中添加 _inject_meson_binaries() 方法, 从 compiler_executables conf 中推导 ar/ranlib 路径并注入到 native file

### 问题4: Conan CMakeDeps 不填充组件级 includedirs
- **问题**: OHOS 适配版 Conan 的 CMakeDeps 生成器不填充 glib 组件的 includedirs, 导致 test_package 编译时找不到 glib-object.h
- **解决**: 在 test_package/CMakeLists.txt 中手动添加 glib include 路径

### 问题5: E088 HarmonyOS musl namespace 隔离
- **问题**: 共享库运行时加载失败, musl namespace 忽略 LD_LIBRARY_PATH 和 RUNPATH, 系统库路径只读
- **解决**: 将 meson.build 中的 shared_library() 改为 library(), 设置 default_library=static, 静态链接避免运行时加载

## 编译命令总结

```bash
# 配置 (通过 Conan)
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 功能验证
- libgnome-autoar-0.a ✅ (static library)
- gnome-autoar-0.pc ✅
- 头文件完整 ✅
- test_package: cmake.test() PASS ✅

---
*编译者: OpenDesk AI Worker*
*日期: 2026-08-06*
