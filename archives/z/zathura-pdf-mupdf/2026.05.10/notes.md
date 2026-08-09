# zathura-pdf-mupdf 2026.05.10 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装 glib 2.88.0 (cmd-pkgs) 和 cairo 1.18.4 (conan repo)
2. 下载 mupdf 1.27.2 源码 + 第三方子模块 (freetype, harfbuzz, libjpeg 等)
3. 应用 mupdf mujs 补丁 (填充 thirdparty/mujs/ 的 regexp/utf 源文件)
4. 构建 mupdf 库: `make HAVE_X11=no HAVE_GLUT=no HAVE_OBJCOPY=no shared=no build=release extract=no html=no mujs=no -j1 libs`
5. 下载 girara 2026.02.04 源码 (仅安装头文件)
6. 下载 zathura 2026.05.20 源码 (仅安装头文件)
7. 生成 girara-version.h 和 zathura-version.h
8. 创建 girara.pc, zathura.pc, mupdf.pc pkg-config 文件
9. 创建 stub libgirara.a 和 libzathura.a (空归档, 插件链接时不需要实际符号)
10. 创建 stub gtk/gtk.h (zathura links.h 包含 <gtk/gtk.h>, 但插件不直接使用 GTK)
11. meson 构建: `meson setup builddir -Dc_std=c17 -Dtests=disabled -Dpdf=enabled` + `ninja -C builddir`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson.build 默认 c_std=c23 | clang 15 不支持 C23 | 覆盖为 -Dc_std=c17 |
| 2 | zathura links.h 包含 <gtk/gtk.h> | GTK3 不可用 | 创建 stub gtk.h (仅 GdkAtom typedef) |
| 3 | girara/zathura 不在 conan 制品仓 | 无 conan 配方 | 从源码安装头文件, 创建 stub .a 和 .pc |
| 4 | mupdf 不在 conan 制品仓 | 无 conan 配方 | 从源码构建 (bundled thirdparty) |
| 5 | mupdf mujs 子模块不完整 | tarball 不含 git 子模块 | 应用补丁填充 mujs/regexp/utf 文件, mujs=no |
| 6 | mupdf build 失败: extract/extract.h 找不到 | thirdparty/extract 为空 | extract=no 禁用 |
| 7 | -Werror=maybe-uninitialized 不支持 | clang 15 不支持此警告 | meson 自动跳过 |

## 源码修改

无源码修改。所有调整通过构建配置完成:
- meson options: -Dc_std=c17, -Dtests=disabled, -Dpdf=enabled
- mupdf build flags: extract=no, html=no, mujs=no, HAVE_X11=no, HAVE_GLUT=no, HAVE_OBJCOPY=no
- stub gtk/gtk.h (GdkAtom typedef only)

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib | 2.88.0 | cmd-pkgs → conan recipe: glib/2.84.0.1 |
| cairo | 1.18.4 | conan repo |
| mupdf | 1.27.2 | built from source (bundled thirdparty) |
| girara | 2026.02.04 | source (headers only) |
| zathura | 2026.05.20 | source (headers only) |
| pcre2 | 10.40 | cmd-pkgs (glib dependency) |

## 验证结果

```bash
$ file libpdf-mupdf.so
ELF shared object, 64-bit LSB arm64, not stripped

$ llvm-readelf -d libpdf-mupdf.so | head -5
NEEDED: libcairo.so.2
NEEDED: libc.so
FLAGS: BIND_NOW
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpdf-mupdf.so | 42.5 MB | zathura PDF 插件 (含静态链接的 mupdf) |
| libmupdf.a | 54.9 MB | mupdf 静态库 |
| libmupdf-third.a | 3.6 MB | mupdf 第三方依赖库 |

## 注意事项

- 插件体积较大 (~42MB) 因静态链接了 mupdf (~55MB)
- GTK3 stub 仅用于编译, 运行时由 zathura 提供 GTK 符号
- girara/zathura stub .a 仅用于链接, 运行时由 zathura 提供符号
---

**编译结束**: 2026-08-10 00:53
**最终状态**: built
