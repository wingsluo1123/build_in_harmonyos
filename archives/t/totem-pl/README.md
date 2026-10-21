# totem-pl（上游 totem-pl-parser）

GNOME Totem 播放列表解析库：解析 m3u/pls/asf/xspf/rss/atom/qtl/smil/vcf 等播放列表格式，
对外暴露 C API `totem-pl-parser`（完整版）与 `totem-plparser-mini`（mini 变体）。

- 上游: https://gitlab.gnome.org/GNOME/totem-pl-parser
- 许可证: LGPL-2.1-or-later
- 构建系统: meson
- 下游兼容: pkg-config 名 `totem-plparser` / `totem-plparser-mini`（grilo 等消费）

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 3.26.7 | built | 2026-10-16 |

## OHOS 适配要点

- glib/2.84.0.2（ohpcd binary 与 zlib/1.3.1.1 override 图精确匹配）；公共头暴露 glib
  类型，`transitive_headers/transitive_libs=True` 传播
- PkgConfigDeps 生成的 glib-2.0.pc 缺 `glib_mkenums`/`glib_genmarshal` 变量，配方
  generate() 注入（GNOME meson 族通用模式）
- uchardet/0.0.7 静态 C++ 档案：C 链接行加 `-lc++`、头子目录 `include/uchardet` 入 include 路径
- hmdfs：meson rpath fixup in-place 重写损坏 ELF，package() sha256 校验+重拷
  （DRAFT-15202）
- OHOS 无 shared-mime-info 数据库：MIME 依赖功能需最小 globs/magic/subclasses 注入
  （DRAFT-15201）
- 上游测试 main 依赖 getpwuid_r：容器 uid 环境需纯 C LD_PRELOAD shim
  （DRAFT-15203）

详见 `3.26.7/notes.md`（含 R51 上游测试实测 72 执行/68 通过/4 失败及逐条根因）。
