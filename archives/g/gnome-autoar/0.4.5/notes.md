# gnome-autoar 0.4.5 编译笔记

## 编译信息
- **编译日期**: 2026-08-06
- **编译器**: clang 15.0.4
- **构建系统**: meson 1.11.1 + ninja 1.13.1
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64

## 依赖
- glib 2.84.0.1 (from conan remote ohpcd)
- libarchive 3.8.7 (locally built and conan-published)

## 主要问题及解决方案

### 问题1: 源码解压失败 (绝对路径符号链接)
- **问题**: tarball 中 tests/files/extract/test-symlink-parent/reference/arextract 是指向 /tmp 的绝对路径符号链接, Python tarfile 拒绝解压
- **解决**: 使用 tar --absolute-names 手动解压

### 问题2: glib pkg-config 缺少 glib_mkenums 变量
- **问题**: Conan PkgConfigDeps 生成的 glib-2.0.pc 缺少 glib_mkenums 变量, 导致 meson gnome.mkenums() 失败
- **解决**: 手动在 glib-2.0.pc 中添加 glib_mkenums 变量指向 conan 包中的 glib-mkenums 二进制

### 问题3: meson 找不到 clang 编译器
- **问题**: conanrun.sh 修改 PATH 后, /data/service/hnp/bin 不在 PATH 中
- **解决**: 显式设置 CC, CXX, AR, RANLIB 环境变量, 并在 source conanrun.sh 后重新 prepend /data/service/hnp/bin 到 PATH

## 编译命令总结

```bash
# 设置环境
export CC=/data/service/hnp/bin/clang
export CXX=/data/service/hnp/bin/clang++
export AR=/data/service/hnp/bin/llvm-ar
export RANLIB=/data/service/hnp/bin/llvm-ranlib
export PATH="/data/service/hnp/bin:$PATH"

# 安装 glib 依赖 (conan)
conan install --requires="glib/2.84.0.1" -r=ohpcd --build=missing -g PkgConfigDeps

# 修复 glib-2.0.pc (添加 glib_mkenums 变量)
echo 'glib_mkenums=${bindir}/glib-mkenums' >> glib-2.0.pc

# 配置
source conanrun.sh
export PATH="/data/service/hnp/bin:$PATH"
export PKG_CONFIG_PATH="$PWD:/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
meson setup build --prefix=$DEFAULT_PREFIX -Dgtk=false -Dintrospection=disabled -Dtests=false

# 编译
meson compile -C build -j2

# 安装到 staging
meson install -C build --destdir=$TEST_PREFIX
```

## 功能验证
- libgnome-autoar-0.so ✅
- gnome-autoar-0.pc ✅
- 头文件完整 ✅

---
*编译者: OpenDesk Compile Agent*
*日期: 2026-08-06*
---

**编译结束**: 2026-08-06 15:35
**最终状态**: built
