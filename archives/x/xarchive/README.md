# xarchive

GTK+2 图形归档管理前端（XArchive），通过 wrapper 脚本调用 tar/gzip/bzip2/zip/unzip/rar/7z/deb/rpm 等命令行归档工具，实现归档的浏览、解包与创建。

- 主页: https://sourceforge.net/projects/xarchive/
- 上游协议: GPL-2.0-or-later
- 归档版本: 0.2.8-6（上游 2005 年发布，传统 Autotools）

## 适配版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.2.8-6 | published | conan-verify 全门禁通过；详见 0.2.8-6/notes.md |

## 平台要点（鸿蒙PC / aarch64-ohos）

- 依赖仓内 `gtk2/2.24.33`（pkg_config_name `gtk+-2.0`，X11 后端）
- 2005 年 config.guess/config.sub 以 autotools-dev 替换，识别 aarch64-ohos
- 关键修复：交叉编译下 fnmatch 探测失败触发上游缺失的 fnmatch_.h 链接 → 用
  `ac_cv_func_fnmatch_works=yes` 跳过（musl fnmatch 正常）；VPATH 编译缺
  `-I<top_srcdir>`（icons/xarchive.xpm 以 C 数据被 include）→ CPPFLAGS 注入
- HMDFS 规避：configure 临时目录重定向 ${TMPDIR:-.} + umask 000 + mktemp wrapper
  （与 gtk2/xsane 系配方同口径）
- 无头冒烟：`xarchive --help` 在 gtk_init 之前 exit(0)，可验证完整动态链接链；
  GUI 交互验证需 X server（R40 人工确认边界）
