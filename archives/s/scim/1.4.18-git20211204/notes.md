# scim 1.4.18-git20211204 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-07
- 编译器: /data/service/hnp/bin/clang / clang++
- 状态: published

## 编译步骤

1. 上游源码为 git 快照（无 configure），运行 `sh bootstrap`（autopoint + intltoolize + autoreconf）生成 configure。
2. `./configure --prefix=... --disable-panel-gtk --enable-tests`（conan 配方内由 AutotoolsToolchain 注入依赖 CPPFLAGS/LDFLAGS）。
3. `make -j1` 构建 libscim-1.0 核心库、scim-gtkutils、各模块（Socket FrontEnd、socket/rawcode IMEngine、sctc Filter）、scim/scim-config-agent/scim-im-agent 工具。
4. `make install` 打包；test_package 以 pkg-config 直编方式验证消费者编译链接与 API 调用。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：`PKG_PROG_PKG_CONFIG: inaccessible or not found` | 上游 git 快照缺 `m4/pkg.m4`，autoconf 无法展开 pkg-config 宏 | 随配方 export_sources 提供 m4/pkg.m4（serial 12, pkg-config-0.29.2） |
| 2 | configure 失败：`config.status: can't create ./confXXXXXX/subs1.awk Permission denied` | HMDFS 文件系统 UID 映射导致 umask 077 临时目录不可写（E052/E060） | 补丁 0001：configure.ac m4_define 覆盖 AS_TMPDIR 为 umask 002 |
| 3 | configure 失败：`IT_PROG_INTLTOOL(0.33, no-xml)` 未展开 | 上游缺 `m4/intltool.m4` | 随配方 export_sources 提供 m4/intltool.m4（intltool 0.51.0） |
| 4 | libtoolize 报 libltdl 源缺失 | conan libtool 包重定位后 `share/libtool-conan/libltdl/` 只有头文件，完整源在 `share/libtool/` | 配方 `_stage_libtool_data()` 复制完整 libltdl 源，bootstrap 时以 `_lt_pkgdatadir` 指向（E443 模式） |
| 5 | autoreconf/aclocal 崩溃 `Perl_my_cxt_init: symbol not found` | conan tool_requires perl 包注入 PERL5LIB（5.42.2 XS 模块），与系统 perl 5.42.0 解释器 ABI 不匹配 | 配方将 PERL 指向系统 perl，PERL5LIB 仅指向 automake share 目录 |
| 6 | make 失败 `No rule to make target '../libltdl/libltdlc.la'` | configure 未检测到系统 libltdl 时回退内嵌路径 | 配方将各依赖 include/lib 目录注入 CPPFLAGS/LDFLAGS，configure 检测到 `-lltdl` 走系统库 |
| 7 | libltdl/configure 内嵌 AS_TMPDIR umask 限制 | conan 环境生成的 libltdl/configure 用 umask 022/077，HMDFS 上同样不可写 | 配方正则替换 `umask 0\d\d` → `umask 002` |
| 8 | GTK Panel（extras/panel）编译 20 错误 | 上游 1.4.18 代码不兼容 GTK3（`_tray_icon` 未声明、double→guint16 narrowing） | `--disable-panel-gtk`（下游 scim-thai 不需要 panel） |
| 9 | test_package 的 cmake.configure() 崩溃 libc++_shared.so 加载失败 | conan 子进程中 HNP cmake 二进制缺 libc++_shared.so 加载路径 | test_package 改用 pkg-config 直编（参照 libthai 先例），绕开 cmake 二进制 |
| 10 | package_info 校验失败：direct dependency 'gtk' 未使用 | conan 2 要求直接依赖在 cpp_info.requires 声明 | package_info 补 `gtk::gtk` |

## 源码修改

- `patches/0001-configure.ac.patch`：configure.ac 覆盖 AS_TMPDIR（umask 002），解决 HMDFS config.status 临时目录权限（E052/E060）
- `m4/pkg.m4`：随配方 export_sources 提供，解决上游 git 快照缺 pkg.m4 导致 PKG_PROG_PKG_CONFIG 未展开
- `m4/intltool.m4`：随配方 export_sources 提供，解决上游缺 intltool.m4 导致 IT_PROG_INTLTOOL 未展开

## 依赖版本

- libltdl/2.6.0（LT_INIT dlopen 必需）
- gtk/3.24.38（scim-gtkutils + GTK3 IMModule）
- tool_requires: autoconf/2.72、automake/1.18、libtool/2.5.4、gettext/0.22.5、intltool/0.51.0

## 验证结果

- conan-verify 全绿：G1 配方完整性、G0 预检、G2 conan create（含 test_package 消费者测试）PASS、G3 系统同名库隔离 PASS、G4 产物完整性 PASS、L2/L4/L5 PASS
- 消费者测试：scim.h UTF-8/WideString 往返转换 + locale 函数调用成功
- 上游测试（探索阶段，--enable-tests 构建 5 程序 + 2 helper）：testiconvert ✅、testlang ✅；testpanel ❌（需运行中的 SCIM Panel，无 X11 环境）；socket 配对测试大字符串往返基本通过；make check 的 po/ 目录因 xgettext/intltool 工具链兼容问题失败（翻译模板生成，非核心测试）

## 注意事项

- scim 是 scim-thai 的必需依赖（configure.ac `PKG_CHECK_MODULES(SCIM, scim >= 0.99.8)`），本 PR 为依赖项适配，分支 feat/scim-1.4.18-git20211204。
- 提交仅含 archives/s/scim/1.4.18-git20211204/ 配方目录，不包含其他软件。
---

**编译结束**: 2026-10-07 10:33
**最终状态**: published
