# imagination 3.6 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure + Makefile.in，无需 autoreconf）
- 编译日期: 2026-10-12
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos 目标）
- 状态: built

## 编译步骤

```bash
# conan create（ohos-aarch64 profile，--build=missing，jobs=2）
conan create archives/i/imagination/3.6 \
  -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
```

配方内部流程：get() 解包 → apply_conandata_patches（0001/0002）→
config.guess/config.sub 替换为自包含 OHOS-aware 版本 → Autotools.configure()
（ac_cv_prog_cc_works=yes / ac_cv_prog_cc_cross=yes）→ make -j1
LIBS="-lgmodule-2.0 -lintl -L<glib libdir>" → install。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sox 为 configure.ac 无条件硬依赖（PKG_CHECK_MODULES(SOX, sox>=14.2.0)），但 ohpcd 制品仓无 sox 包 | 平台未发布 libsox；sox 自身配方仅有 manifest/notes/patches 未合入 conanfile | generate() 生成 no-op stub sox.h + 空 Libs 的 stub sox.pc，prepend PKG_CONFIG_PATH；sox_open_read/sox_open_write 恒返 NULL，所有调用方按"无法打开音频文件"路径处理——音频文件进不了 GUI 列表、sox 导出线程永不 spawn、ffmpeg 导出走 -an 分支。零上游源码改动 |
| 2 | configure 报 "unable to guess system type" | tarball 内 2020-01 版 config.guess 不认识 HarmonyOS（E007） | 构建期替换为自包含 OHOS-aware config.guess/config.sub（aris/2.2 先例） |
| 3 | CFLAGS 被覆写导致交叉编译标志丢失 | configure.ac 的 `CFLAGS="-g -Wall"`（SVN 调试模式遗留）覆盖 conan 注入的交叉标志 | 0001 补丁改为 `CFLAGS="$CFLAGS -g -Wall"` 追加 |
| 4 | XML::Parser perl 模块缺失致 configure 失败 | HMDFS 上 XS 模块 dlopen 受限（intltool/0.51.0 配方同坑） | 0001 补丁跳过探测——本构建只触 intltool-merge 的 desktop 模式（纯文本处理，实测不依赖 XML::Parser） |
| 5 | config.status 建临时目录 Permission denied | hmdfs setgid 卷上 umask 077 的 0700 目录创建者自身不可写 | 0001 补丁 umask 077 → 022（l3afpad/intltool 先例） |
| 6 | doc/ 子目录构建失败/挂起 | DocBook XSL 样式表构建期联网拉取 docbook.sourceforge.net | 0002 补丁从 SUBDIRS 剔除 doc/（文档非交付物） |
| 7 | 链接缺 g_libintl_* 符号与 gmodule | glib gi18n.h 把 gettext 映射到私有 libintl 的别名，.pc 不传播 -lintl；上游 LDADD 硬编码 -lgmodule-2.0 但 glib 包 libdir 不在默认搜索路径 | make LIBS="-lgmodule-2.0 -lintl -L<glib libdir>" 单词注入（l3afpad 先例；不能走 configure，会破坏 AC_PROG_CC conftest） |
| 8 | 并行构建随机失败 | hmdfs jobserver fifo EPERM（E074） | make -j1 |
| 9 | support.c 报 -Wint-conversion 硬错（ngettext 隐式声明，int 传 const gchar*） | 上游 configure.ac 无 AC_CONFIG_HEADERS，config.h 不存在 → ENABLE_NLS 永不定义 → 走 support.h 非 NLS 回退宏块，该块 gettext/_/N_/Q_ 都有唯独漏了 ngettext；clang 15 下隐式声明退化为 int 返回值 | 0003 补丁在回退块补 `#define ngettext(Msgid1,Msgid2,N) ((N)==1?(Msgid1):(Msgid2))` |

## 源码修改

| 文件 | 内容 |
|------|------|
| patches/0001-configure-ohos-build-fixes.patch | configure + configure.ac：CFLAGS 覆写改追加、XML::Parser 探测跳过、umask 077→022 |
| patches/0002-build-drop-doc-subdir.patch | Makefile.am + Makefile.in：SUBDIRS 剔除 doc/ |
| patches/0003-support.h-ngettext-fallback.patch | support.h：非 NLS 回退宏块补 ngettext 宏 |
| （构建期生成，非补丁） | OHOS-aware config.guess/config.sub；sox no-op stub 头 + stub pc |

## 依赖版本

- gtk/3.24.43（传递 glib/2.84.0.1、cairo、pango、gdk-pixbuf、atk 等）
- 构建 tool_requires：intltool/0.51.0、gettext/0.22.5.1

## 验证结果

```bash
conan create archives/i/imagination/3.6 -pr:h=...ohos-aarch64 \
  --build=missing -c tools.build:jobs=2   # RC=0
# test_package: 4/4 用例通过（ELF 架构/插件枚举与 dlopen/插件 API 契约/入口符号）
```

详见 PR 正文「验证结果」段实测数据。

## 注意事项

- 音频子功能（背景音乐导入/导出）因平台无 sox 制品被整体禁用，UI 其余功能
  （幻灯片编辑/转场插件/字幕/视频导出）不受影响；若未来 sox 入库可移除 stub
  恢复。
- imagination 产物为 GUI 应用：无头环境只能验证到 GTK 显示初始化前
  （"Cannot open display" 为预期终点，l3afpad 同款断言策略）。
- 15 个转场插件装在 lib/imagination/，运行期经 GModule 按绝对路径加载。
