# harfbuzz 14.2.0 编译记录

## 编译环境

- **软件**: harfbuzz
- **版本**: 14.2.0
- **构建系统**: CMake (HarfBuzz 官方 CMake 构建，非 meson)
- **平台**: OpenHarmony aarch64
- **编译器**: clang 15.0.4 (LLVM)
- **编译日期**: 2026-07-22

## graphite2 支持（本次新增）

- ✅ 启用 graphite2 shaper 支持 (HB_HAVE_GRAPHITE2=ON)
- ✅ 链接 libgraphite2.a (graphite2/1.3.14)
- ✅ hb-graphite2.h 已安装到 include/harfbuzz/
- ✅ conanfile.py requirements() 包含 graphite2/1.3.14
- ✅ conanfile.py package_info() 设置传递依赖 graphite2::graphite2

## 编译过程

### 1. 源码获取

- 源码下载成功（通过 ghfast.top 镜像）：https://github.com/harfbuzz/harfbuzz/releases/download/14.2.0/harfbuzz-14.2.0.tar.xz
- sha256: 94017020f96d025bb66ae91574e4cf334bcad23e8175a8a40565b3721bc2eaff
- 源码位置：/storage/Users/currentUser/tmp/builds/harfbuzz-14.2.0

### 2. 构建系统选择

- meson 在 HMDFS 上有 subprocess 执行限制（已知问题）
- CMake 构建系统工作正常
- 使用 CMakeToolchain + CMake 进行构建
- conan-verify 的 conan create 使用 CMake 成功构建

### 3. CMake 构建选项

```
BUILD_SHARED_LIBS=OFF          # R5/R26: 静态编译
HB_HAVE_GRAPHITE2=ON           # 启用 graphite2 支持
HB_HAVE_FREETYPE=ON            # 启用 freetype 支持
HB_HAVE_GLIB=OFF              # 禁用 glib（不可用）
HB_HAVE_ICU=OFF               # 禁用 ICU（不可用）
HB_HAVE_CAIRO=OFF             # 禁用 cairo
HB_BUILD_UTILS=OFF            # 不构建工具
```

### 4. 编译产物

- libharfbuzz.a (静态库)
- libharfbuzz-subset.a
- libharfbuzz-raster.a
- libharfbuzz-vector.a
- libharfbuzz-gpu.a
- hb-graphite2.h (graphite2 头文件已安装)

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| graphite2 | 1.3.14 | conan cache (ohpcd) |
| freetype | 2.14.3 | conan cache (ohpcd) |

## 验证结果

- conan-verify: ✅ PASS (G0/G1/G2/G3 全部通过)
- test_package: ✅ PASS (C++ 测试验证库版本、buffer 操作、face 创建)
- 可标记 status: published

## 注意事项

- harfbuzz CMake 构建会将 C++ 标准重置为 11（CMakeLists.txt 中设置）
- test_package 必须使用 C++ (test.cpp) 而非 C，因为 harfbuzz 和 graphite2 是 C++ 库
- conanfile.py 的 package_info() 需要设置 includedirs = ["include/harfbuzz"]
- conanfile.py 的 package_info() 需要设置传递依赖 (cpp_info.requires)
---

**编译结束**: 2026-07-22 11:30
**最终状态**: built
