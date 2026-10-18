# xarchive 0.2.8-6 适配笔记

## 编译环境
- 构建系统: autotools（上游 autoconf 2.59/automake 老脚本）
- 编译日期: 2026-10-17
- 编译器: clang（OHOS SDK，/data/service/hnp/bin/clang）
- 状态: published
- 配方: archives/x/xarchive/0.2.8-6/conanfile.py（参考 xsane/0.999 同类 GTK2 GUI 应用骨架）

## 编译步骤
1. conan create 以 ohos-aarch64 profile 交叉编译，--build=missing
2. 配方 build() 内自动完成：
   - 替换 2005 年的 config.guess/config.sub（autotools-dev 20240727.1-nmu1），识别 aarch64-ohos
   - chmod +x configure（E490）
   - _patch_configure_tmpdir：把 configure 的临时目录从 cwd 硬编码改为 ${TMPDIR:-.} 且 umask 000（HMDFS 对 mktemp 0700 目录拒绝写入且静默忽略 chmod，同 gtk2/xsane 口径；命中 autoconf 2.59 的 confstat 变体）
   - 写入 ohos mktemp wrapper（/system/bin/sh 优先，失败回退 /data/service/hnp/bin/mktemp，目录补 chmod 0755）
3. configure 传 ac_cv_func_fnmatch_works=yes（关键修复，见问题 1）
4. CPPFLAGS 追加 -I<top_srcdir>（关键修复，见问题 2）
5. make -j1（umask 000）；make install DESTDIR=<package>（umask 000）
6. test_package 冒烟：xarchive --help（5/5 断言通过(全部为真实断言)）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报 `linking ./fnmatch_.h to ./fnmatch.h: file not found` | AC_REPLACE_FNMATCH 在交叉编译下 AC_RUN_IFELSE 无法运行探测程序，判 fnmatch 为 broken → 触发 AC_CONFIG_LINKS(fnmatch.h:fnmatch_.h)，但上游 tarball 根本没带 fnmatch_.h（上游缺陷） | musl 的 fnmatch 工作正常，configure 传 cache 变量 `ac_cv_func_fnmatch_works=yes` 跳过探测 |
| 2 | `fatal error: 'icons/xarchive.xpm' file not found`（widgets_gtk.h 中 #include"icons/xarchive.xpm"） | 2005 年 src/Makefile.am 无 VPATH include 路径配置，xpm 以 C 数据形式被 include，路径以源码根为基准，VPATH(out-of-tree) 编译时找不到 | 构建环境 CPPFLAGS 追加 `-I<top_srcdir>`；上游 configure 把 CPPFLAGS 捕获进 CONFIGURE_CFLAGS 注入 src/Makefile，故能生效 |
| 3 | configure 在 cwd 生成 conftest 目录后无法写入 | HMDFS 对 mktemp -d(0700) 目录拒绝写入且静默忽略 chmod（知识库既有经验，gtk2/xsane 同款） | _patch_configure_tmpdir 改写 configure：临时目录落 ${TMPDIR:-.}，umask 000 + chmod 777 兜底 |
| 4 | ac_cv_func_canonicalize_file_name = no | musl 无 canonicalize_file_name（glibc 扩展） | 无需处理：上游 config.h 未定义 HAVE_CANONICALIZE_FILE_NAME 时 src/main.c 自带 realpath() fallback， musl realpath 可用 |
| 5 | conan create 首轮拉起 pango 从源码重建（触发 E538 提示） | 仓内 pango 发布 binary 的 option 组合与 gtk2 依赖图不完全匹配 | 属预期行为（--build=missing），重建成功且其 meson test 通过，无 E538 冲突产物混用 |

## 源码修改
- 无 .patch 文件（全部规避逻辑在配方内：chmod、configure tmpdir 改写、mktemp wrapper、cache 变量、CPPFLAGS 注入）

## 依赖版本
- gtk2/2.24.33（pkg_config_name: gtk+-2.0，X11 后端）
- tool_requires: autotools-dev/20240727.1-nmu1、pkgconf/3.0.5
- 传递依赖（构建期重建/安装）：pango/1.50.14.1.1（源码重建）、cairo/1.18.4.1、gdk-pixbuf/2.44.6.1、harfbuzz/14.2.0.1.1.1、fontconfig/2.18.1.1、glib/2.84.0.1 等

## 验证结果
```text
conan-verify: G0/G1/G2/G3/G4 全部 PASS
test_package 冒烟: xarchive --help → exit 0, "xarchive consumer smoke: 5/5 checks passed"
  （--help 在 g_option_context_parse 内、gtk_init 之前 exit(0)，无头环境可验证动态链接链与命令行解析；
   完整 GUI 行为需 X server，属 R40 人工确认边界）
```

## 上游信息
- 上游 0.2.8-6（2005 年发布，SourceForge）为传统 GTK2 GUI 前端，调用 tar/zip/rar/7z/deb 等命令行工具的 wrapper 脚本（安装至 pkglibdir/wrappers）
- 无上游测试套件（无 tests/、无 make check TESTS），MANIFEST.yml 已按规范声明（upstream_case_count: 0）
### 对话 #1 (2026-10-17)
- 用户任务：适配 xarchive 0.2.8-6 到 aarch64-linux-ohos（路径 A，本地闭环 + fork 分支 + 手动 PR）
- 关键过程：W0 依赖检查（gtk2/2.24.33 已在制品仓）→ init-build/lang-preflight 通过 →
  基于 xsane/0.999 骨架编写配方 → 修复 fnmatch_.h 缺失（cache 变量）、VPATH include
  （CPPFLAGS -I top_srcdir）、HMDFS tmpdir（replace_in_file 改写 configure）→
  conan-verify 全门禁 PASS，test_package 冒烟 5/5 → 打包 release/debug tar.gz →
  finish 完成后推送 feat 分支，PR 正文写入 鸿蒙PC/PR正文/，严禁自动建 PR
---

**编译结束**: 2026-10-17 08:08
**最终状态**: published
