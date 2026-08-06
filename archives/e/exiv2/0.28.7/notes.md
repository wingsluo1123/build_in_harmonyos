# exiv2 0.28.7 编译笔记

## 编译环境
- 平台: HarmonyOS aarch64 (OHOS 6.0)
- 编译器: clang 15.0.4
- 构建系统: CMake 4.1.2

## 依赖
- zlib/1.3.1 (conan, 静态)
- expat/2.8.2 (conan, 共享)
- brotli/1.2.0 (conan, 共享)
- inih r58 (源码编译, conan inih/r58 不含 INIReader C++ wrapper)

## 编译过程

### 源码修复
1. **目标名不匹配**: exiv2 CMake 使用 EXPAT::EXPAT, ZLIB::ZLIB, BROTLI_FOUND 等
   大写目标名/变量, 但 conan CMakeDeps 生成小写名 (expat::expat, zlib::zlib, Brotli_FOUND)。
   在 build() 中用 replace_in_file() 修复所有不匹配。

2. **自定义 find 模块冲突**: exiv2 的 cmake/FindBrotli.cmake 和 cmake/Findinih.cmake
   使用 find_path/find_library, 与 conan CMakeDeps 配置模式冲突。
   在 build() 中删除这两个文件, 让 CMakeDeps 接管。

3. **inih/INIReader 缺失**: conan inih/r58 只包含 libinih.a 和 ini.h,
   不包含 C++ wrapper INIReader.h/INIReader.cpp。
   从 inih r58 源码编译 ini.c + INIReader.cpp, 安装到本地 prefix 并生成 cmake 配置。

4. **xmpsdk 包含路径**: xmpsdk/CMakeLists.txt 使用 ${EXPAT_INCLUDE_DIRS} 变量
   (CMakeDeps 不设置此变量), 改为 target_link_libraries(exiv2-xmp PRIVATE expat::expat)

### 产物
- libexiv2.a (8.5M, 静态库)
- libinih.a, libINIReader.a (从源码编译, 包含在包中供消费者链接)
- exiv2 命令行工具
- exiv2 开发头文件 (include/exiv2/)

## 验证
- conan-verify G0-G4 + L2/L4/L5 全部通过
- test_package: 调用 Exiv2::version() 验证库可用
---

**编译结束**: 2026-08-06 09:38
**最终状态**: built
