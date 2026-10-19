# gdl 3.40.0 — OHOS PC 适配笔记（HarmonyOS PC aarch64）

GNOME Docking Library（GNOME Devtools Libraries）— GTK+3 停靠组件库。
产物：libgdl-3.so.5（libtool -version-info 5:9:0）+ gdl-3.0.pc + 头文件
include/libgdl-3.0/gdl。3.40.0 为上游最终稳定版（download.gnome.org sources
顶层最高系列 3.40；GitLab Archive/gdl 最新 tag GDL_3_40_0，2021-08-26，仓库
已归档停维护）。

## 构建方式

- autotools；GNOME dist tarball 自带完整预生成 configure/Makefile.in，
  **不做 autotools regen**（设备无 automake/libtoolize）。build() 里做
  mtime 归一化（生成文件必新于输入），防止 make 走 `missing automake`
  再生路径（enchant 先例）。
- configure 开关：`--build/--host=aarch64-unknown-linux-gnu`（2021 版
  config.guess 不识别 OHOS triple，libido3 先例）、`--disable-static
  --enable-shared`、`--disable-nls`、`--disable-introspection`（E179：
  g-ir-scanner 需 dlopen 目标 .so，OHOS ELF 签名下 Permission denied；
  dependency-resolution.md:706 g-i 循环禁用）、`--disable-gtk-doc`。

## intltool 解法（本库最大的构建系统障碍）

configure.in:122 `IT_PROG_INTLTOOL([0.40.4])` 已被展开进 dist tarball 的
生成版 configure，形成 5 处无条件硬失败探针（intltool-update 版本探测、
intltool 三脚本缺失、GNU gettext 工具缺失 ×2、perl XML::Parser 缺失）。
设备上 intltool/XML::Parser/msgmerge 全部缺失，perl-XML 工具链不可供给。

**落地解法：补丁去除（patches/0001-neutralize-intltool-configure-hard-deps.patch）**
—— 只把 5 处 `as_fn_error` 换成 `:` no-op（探针保留、报告保留），配合
上游原生开关 `--disable-nls`：USE_NLS=no 时 po/Makefile.in.in 的
`all-no:` 与 `install-data-no:` 为空目标，intltool/gettext/perl 机制在
make/install 阶段完全不执行。库代码 grep bindtextdomain/dgettext = 0，
NLS 运行时亦 inert。未引入任何平台条件宏（R8 干净）。

未选路线：tool_requires 供 intltool（需 perl + XML::Parser + msgmerge
全家桶，设备不可行）；合成 stub 脚本（PATH 里放假工具，行为不可控）。

## glib dev tools 的坑（本库特有）

libgdltypebuiltins.[ch]（glib-mkenums）/libgdlmarshal.[ch]
（glib-genmarshal）在 make 期生成。gdl 的 configure 用
`$PKG_CONFIG --variable=glib_genmarshal glib-2.0`（及 glib_mkenums）解析
工具路径并烤进 Makefile —— **conan PkgConfigDeps 镜像 .pc 不携带自定义
变量**，直接构建两变量为空。解法：generate() 里把 glib 包内工具的绝对
路径作为 `glib_genmarshal=` / `glib_mkenums=` 变量追加进生成目录的
glib-2.0.pc 镜像（镜像位于 PKG_CONFIG_PATH 首位，必胜出）。glib 包内
两脚本 shebang 为 `#!/usr/bin/env python3`，profile buildenv PATH 已含
python3 所在目录。

## 依赖

- 直接：libxml-2.0 >= 2.2.8（configure.in:80 无条件 PKG_CHECK_MODULES）、
  gtk+-3.0 >= 3.0.0（configure.in:84 无条件）。conan 闭包取 libido3
  13.10.0（官方 CI 通过）同一套 proven graph：glib/2.84.0.1 +
  gtk/3.24.43（ohpcd 已发布，broadway-only 后端）+ libxml2/2.15.3.1 +
  全套 override 钉版（RREV 对齐 ohpcd 发布二进制，消除 CCI 工具边）。
- gdl-3.0.pc `Requires: gtk+-3.0`：下游消费面传染（pkg-config 0.29.2
  链解析需整条可定位），配方 vendored .pc 合成 + fail-fast 探针照搬
  libido3 范式（镜像优先、真实目录兜底）。

## 上游测试（NO_UPSTREAM_TESTS，discovery.status=EVIDENCE_COMPLETE）

3.40.0 dist tarball **无自动化测试**，逐项证据（2026-10-15 实测）：

| 检查 | 结果 | 证据（tarball 解包根相对路径:行） |
|---|---|---|
| tests/ 目录 | 不存在 | 源码树仅 docs/ gdl/ m4/ po/ 四目录 |
| make check 自定义入口 | 无 | Makefile.am:1 `SUBDIRS = gdl docs po`；全仓 grep `^TESTS\|^check_PROGRAMS` 0 命中（Makefile.am、gdl/Makefile.am）→ 无注册用例；check 期 po/ 的 .pot 再生规则仍会执行（intltool 构建卫生，非测试，见结论） |
| 断言型测试程序 | 无 | gdl/Makefile.am:71 `noinst_PROGRAMS=test-dock` —— gdl/test-dock.c:184 `main ()` 建 GUI 窗口、:313 `gtk_main ()` 进事件循环；`g_test_*\|g_assert` 计数 = 0 |
| 其他测试入口 | 无 | docs/reference/Makefile.am:105 gtk-doc `#TESTS` 上游已注释；test-dock-gjs.js / test-dock-seed.js 为 noinst_SCRIPTS 绑定示例（gdl/Makefile.am:76），设备无 GJS/Seed 运行时 |

结论：唯一可执行程序 test-dock 是交互式 GTK demo，无 headless 断言路径；
`make check` 无测试用例可执行，实际以 Error 1 退出——po/ 的 .pot 再生
规则（po/Makefile.in.in:148 `check: all $(GETTEXT_PACKAGE).pot`，不受
USE_NLS 门控）在 INTLTOOL_* 为空时命令塌缩为 127（intltool 构建卫生
失败，非测试失败），由 conanfile build() 的 ignore_errors 按设计捕获
后输出 HMBS_UPSTREAM_TEST_RESULT status=no_upstream_tests 机读标记
（gdl/ 与 docs/ 段均 Nothing to be done）。上游测试门结论
NO_UPSTREAM_TESTS 独立成立（Auditor 独立复核：无 tests/、无
TESTS/check_PROGRAMS、test-dock 0 断言、无未盘点测试入口）。
消费面验证由 test_package 在真机执行 5 项检查（含 libxml2 布局
save/load 往返、broadway 后端 widget 构造）。**未用 broadwayd 硬凑
上游测试**（E471 针对 gtk4-broadwayd；gtk3 包自带的 broadwayd 在本机
 libido3/ayatana-ido 官方 CI 先例可用，仅用于消费面 widget 检查）。

## OHOS 适配点汇总

| 项 | 处理 |
|---|---|
| intltool 5 处硬探针 | patch 0001 去 error + --disable-nls |
| introspection | --disable-introspection（E179） |
| gtk-doc | --disable-gtk-doc（默认即 no） |
| config.guess 2021 版 | --build/--host 显式 triple，跳过探测 |
| glib 工具变量经 pkg-config | glib-2.0.pc 镜像追加变量 |
| umask 077（E011） | build() 内 relax → 022 |
| toybox install（E182/E188） | cp/mkdir shim + Makefile INSTALL 重定向 |
| 依赖 .la 损坏（E236） | 构建前剥离依赖包 .la，产物不装 .la |
| lld 链接闭包 | 每依赖 libdir -L/-rpath/-rpath-link；libintl 绝对路径显式注入 |
| SONAME 真文件 | package() 复制 libgdl-3.so.5.0.9 → libgdl-3.so.5 |
| ELF 签名 | package() binary-sign-tool 自签 |

源码级风险扫描（Scout）：X11/dlopen/汇编/proc 路径/fork-exec/__linux__
分支全部 0 命中；无平台条件宏新增（R8 干净）。

## 附：test_package 布局 XML 根元素（L3 库内事实）

gdl 布局持久化的 XML 根元素是 `dock-layout`（上游 gdl-dock-layout.c:62
`#define ROOT_ELEMENT "dock-layout"`，:802 同名比较校验）——不是
"gdl-layout"。test_package/test.c check3 据此断言 save_to_file 产物含
`<dock-layout` 根元素并完成 load_from_file 往返。此为库内私有 quirk
（L3），无平台/构建系统机理，不入 B 申报不入经验仓。
