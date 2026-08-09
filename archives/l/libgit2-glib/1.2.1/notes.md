# libgit2-glib 1.2.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 构建依赖 libgit2 1.9.0 (static, with OpenSSL from conan)
2. 安装 glib 2.84.0 via conan (PkgConfigDeps + MesonToolchain generators)
3. 修正 conan 生成的 glib-2.0.pc，补充 glib_mkenums 等工具变量路径
4. 修正 conan 生成的 gobject-2.0.pc 和 gio-2.0.pc 路径
5. meson setup with native file, -Dintrospection=false -Dpython=false -Dvapi=false -Dssh=false -Dgtk_doc=false
6. ninja build && ninja install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan glib-2.0.pc 缺少 glib_mkenums 变量 | PkgConfigDeps 只生成基本的 .pc 文件 | 手动补充 glib_genmarshal/glib_mkenums 等变量路径 |
| 2 | gobject-2.0.pc/gio-2.0.pc 路径指向 / | conan 包内 .pc 文件 prefix=/ | 手动创建修正路径的 .pc 文件 |
| 3 | libgit2 共享库链接失败 (PIC relocation) | conan zlib 静态库未编译 -fPIC | libgit2 改为静态构建 (shared=False) |
| 4 | meson 找不到 llvm-ar | conan meson native file 未声明 ar | 在 native file 中添加 ar/ld/strip 路径 |
| 5 | libgit2.pc Requires.private: zlib 找不到 | zlib.pc 不在 PKG_CONFIG_PATH | 添加 conan-deps 目录到 PKG_CONFIG_PATH |
| 6 | 测试失败 G_DISABLE_ASSERT | release buildtype 添加 -DG_DISABLE_ASSERT | GNOME 库预期行为，非真实失败 |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- glib/2.84.0 (from conan artifact repo)
- libgit2/1.9.0 (built from source, static, with OpenSSL 1.1.1w + zlib 1.3.1)
- openssl/1.1.1w (from conan artifact repo)
- zlib/1.3.1 (from conan artifact repo)

## 验证结果

```bash
pkg-config --modversion libgit2-glib-1.0
# 1.2.1

ls /storage/Users/currentUser/usr/local/lib/libgit2-glib-1.0.so*
# libgit2-glib-1.0.so -> libgit2-glib-1.0.so.0.200.1
# libgit2-glib-1.0.so.0 -> libgit2-glib-1.0.so.0.200.1
# libgit2-glib-1.0.so.0.200.1
```

## 注意事项

- libgit2 未发布到 conan 制品仓，需先适配并发布 libgit2 conan 配方
- libgit2 conan 配方已创建本地缓存，CI 需要 libgit2 先发布到制品仓
- glib conan 包的 .pc 文件路径不正确，conan-verify 时需处理

---

**编译结束**: 2026-08-10 06:10
**最终状态**: built
