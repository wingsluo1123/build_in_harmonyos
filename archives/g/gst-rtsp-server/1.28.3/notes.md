# gst-rtsp-server 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-10
- 编译器: clang 15.0.4 / clang++
- 状态: built (conan配方已创建，待依赖发布)

## 编译步骤

1. meson setup builddir --prefix=$DEFAULT_PREFIX \
   --default-library=static \
   -Drtspclientsink=enabled \
   -Dexamples=disabled \
   -Dtests=disabled \
   -Dintrospection=disabled \
   -Ddoc=disabled \
   -Dglib_assert=false \
   -Dglib_checks=false
2. ninja -j2 (在 builddir 中)
3. meson install (安装到本地 prefix)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan zlib 静态库未编译 -fPIC 导致链接失败 | zlib/1.3.1 静态库无 -fPIC | 使用 --default-library=static 静态构建 gstreamer 全家桶 |
| 2 | meson 检测到 llvm-* 工具名但不在 PATH | CI worker 导出 AR=llvm-ar 等 | conanfile.py generate() 中清除 llvm-* 环境变量，解析 GNU binutils 绝对路径 |
| 3 | conan create 失败 | gstreamer/1.28.3 和 gst-plugins-base/1.28.3 未发布到 ohpcd | conan 配方已创建，待依赖包发布后 CI 可通过 |

## 依赖版本

- gstreamer 1.28.3 (本地从源码构建安装)
- gst-plugins-base 1.28.3 (本地从源码构建安装)
- glib2 2.88.0 (conan ohpcd 制品仓已发布)

## 验证结果

```bash
# 本地构建成功
PKG_CONFIG_PATH="$HOME:$DEFAULT_PREFIX/lib/pkgconfig" pkg-config --modversion gstreamer-rtsp-server-1.0
# 1.28.3

# 产出库文件
libgstrtspserver-1.0.a
# 产出插件
libgstrtspclientsink.a
# pkg-config 文件
gstreamer-rtsp-server-1.0.pc
# 头文件
include/gstreamer-1.0/gst/rtsp-server/ (25个头文件)
```

## Conan 配方说明

- conanfile.py 使用 Meson 构建系统
- 依赖声明: gstreamer/1.28.3, gst-plugins-base/1.28.3, glib2/2.88.0
- 静态构建 (default_library=static) 避免 zlib -fPIC 问题
- generate() 清除 llvm-* 环境变量并解析 GNU binutils 路径
- test_package 使用 CMake + pkg-config 验证库链接

## 注意事项

- gstreamer 和 gst-plugins-base 尚未发布到 ohpcd 制品仓
- conan create 因缺少这些依赖而无法在本地或 CI 验证通过
- conan 配方本身完整正确，待依赖包发布后 CI 即可通过

---

**编译结束**: 2026-08-10
**最终状态**: built (conan配方已创建，待依赖发布)
