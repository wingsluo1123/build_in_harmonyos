# mtpaint

GTK+ 像素绘画程序 (mtPaint), 用于图标与像素画创作编辑。

- 上游: https://github.com/wjaguar/mtPaint (3.50.14)
- 主页: http://mtpaint.sourceforge.net
- 许可证: GPL-3.0-only
- 类型: 命令行/GUI 工具 (tool), 产物为 `bin/mtpaint`

## 功能概述

- 索引调色板 / 24 位 RGB 图像编辑, 画笔与调色板工具
- 通道/图层/动画, JPEG/TIFF/PNG/GIF 支持 (本适配启用 jpeg/tiff/lcms2)
- `--cmd` 脚本模式可在无显示环境运行命令

## OHOS 适配

- 手写 mini-configure (非 GNU Autotools), 配置 `gtk3 release jpeg tiff lcms2 nojp2 nowebp --prefix=/`, 不传 `--build/--host` (R15)。
- GTK+3 来自 registry gtk (broadway 后端); 图像编解码经 Conan 依赖链 (libpng/libjpeg-turbo/libtiff/freetype/lcms2/zlib; 上游 3.50.03 起 GIF 已内置不再链接 giflib)。
- 仅打包二进制 (`bin/mtpaint`); 上游无测试套件, 按 `no_tests` 口径输出 HMBS 标记, 消费者测试在 `test_package/` (`--version/--help` + 产物校验, 均为 gtk_init 前退出的确定性路径)。

## 依赖

- gtk/3.24.43, zlib/1.3.1, libpng/1.6.58.2, libjpeg-turbo/3.1.4.1, libtiff/4.7.2.2, freetype/2.14.3, lcms2/2.19 (无 giflib: 上游 3.50.03 起 GIF 已内置)

## 参考

- 各版本详情见 `3.50.14/notes.md`
