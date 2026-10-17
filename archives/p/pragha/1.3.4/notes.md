# pragha 1.3.4 适配笔记

## 编译环境
- 构建系统: autotools（上游随附生成文件，无需 autoreconf）
- 编译日期: 2026-10-14
- 编译器: clang 15.0.4（OHOS aarch64 交叉）
- 状态: built

## 对话记录

### 对话 #1（2026-10-14，feat/pragha-1.3.4）

- 任务创建：从 main(b6fd9ca0ac) 新建 worktree `.wt/pragha-1.3.4`，
  分支 feat/pragha-1.3.4；W0 依赖 conan download 验证 6/6 通过；
  语言预检 R47 通过（detected=c，兼容族）。
- 迭代 1（G2 失败）：configure 硬性探测 XML::Parser perl 模块 →
  0005 补丁跳过（intltool 包配方同款绕法）；同时按 E490 增加
  autotools 脚本 +x 位恢复。
- 迭代 2（G2 失败）：pragha-session.c 无条件包含 gdk/gdkx.h（X11 专属）→
  0006 补丁以 GDK_WINDOWING_X11 守卫。
- 迭代 3（G2 失败）：tag_c.h 找不到 → 增强 taglib_c.pc 追加
  -I<inc>/taglib；首次以追加第二行 Cflags 实现 → pkg-config 解析失败
  整包 not found → 改为合并进既有 Cflags 行。
- 迭代 4（G2 失败）：libtool 报 '//lib/libpcre2-8.la'（E236 .la 毒化）→
  activity-log 式 la-free staging；复跑后 test_package 暴露更深问题。
- 迭代 5（test_package 失败）：打包二进制启动 GObject abort
  （static_quark_type_flags）—— readelf 显示二进制无 libglib-2.0 NEEDED，
  glib 被静态链入：gstreamer.pc Requires 链上 glib2(static) 目录先于
  glib(shared) 目录，ld 拾取 libglib-2.0.a，与 gtk 运行期共享 glib 形成
  双实例。修复：staging 扩展为全依赖镜像（.so+.a 除 .la），全部 pc
  libdir 重写指向 staging，同目录 .so 优先于 .a → 共享 glib 胜出。
- 迭代 6：conan-verify 全过（G0-G4/L2/L4/L5），test_package 14/14。
  W3 首跑被 JC1 误拦（fork origin/main 落后 upstream，incremental 模式
  扫到 main 既有他人标记文件）→ 以 JUNK_PR_DIFF（与 CI buildbot prdiff
  同模式，仅扫本 PR 14 个文件）复跑通过。finalize 后补齐软件级
  README/manifest、packaging tar、test-report。

## 编译步骤

1. W0 依赖验证（R35/R36，conan download -r=ohpcd --only-recipe）：
   glib/2.84.0.1、gtk/3.24.43、gstreamer/1.28.3、sqlite3/3.53.4、
   taglib/1.13.1、zlib/1.3.1.1 全部已发布，rc=0。
2. conan create 按配方构建：apply_conandata_patches →
   /system/bin/sh configure（--prefix=/ --disable-nls + 全部可选依赖
   --disable）→ make -j1 → make check（空跑）→ make install DESTDIR →
   签名 bin/pragha。
3. test_package 无头消费测试（--version / --help / --selftest /
   no-display fail-closed）。

## 上游测试清点（R51 申报表）

- tarball 无 tests/、test/、check/ 目录（find 证据）。
- 全部 Makefile.am（根/data/data/icons{,×7}/src/po）无
  check_PROGRAMS / TESTS / XTEST / AC_CONFIG_TESTDIR（grep 证据）。
- configure.ac 无 AC_CONFIG_TESTDIR；automake 递归 check 目标为空跑。
- 结论：上游无自动化测试。新增鸿蒙消费者用例 = `--selftest`
  （0004 补丁，musicobject 往返/dup/compare、播放列表格式识别含负例、
  sqlite3 运行时、GStreamer 运行时共 5 组检查），test_package 无头
  断言 14 项。make check 在配方 build() 中真实执行（空跑留存证据）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别 OHOS triplet | 2018 版 config.guess/sub 无 linux-ohos | 0001/0002 补丁（bluefish 同模式） |
| 2 | configure 临时目录创建失败 | HMDFS setgid 语义拒绝 0700 目录 | 0003 补丁 umask 077→022 |
| 3 | configure 硬性探测 intltool-update/merge/extract，worker 无 Perl | IT_PROG_INTLTOOL 无条件探测 | intltool/gettext shim（activity-log 同模式）；intltool-merge shim 真实产出 pragha.desktop（strip `_` 前缀），非空壳 |
| 4 | 链接期 g_libintl_* 符号缺失风险 | glib 为 musl proxy-libintl 构建，glib-2.0.pc 不传播 -lintl | 生成器改写 glib-2.0.pc 追加 -lintl（sound-juicer 同模式） |
| 5 | configure 探测 gstreamer-1.0 / gstreamer-base-1.0 无对应 .pc | conan gstreamer 包 pc 名为 gstreamer | 生成 gstreamer-1.0.pc / gstreamer-base-1.0.pc 重定向（sound-juicer 同模式） |
| 6 | glib/2.84.0.1(gtk 图) 与 glib2/2.88.0(gstreamer 图) 并存 | 两图 zlib 版本钉不一致（1.3.1.1 vs 1.3.1） | requires zlib/1.3.1.1 force=True 对齐（sound-juicer 同模式） |

## 源码修改

- 0001-config.guess.patch：config.guess 识别 HarmonyOS uname，输出
  aarch64-unknown-linux-ohos。
- 0002-config.sub.patch：config.sub 接受 linux-ohos OS 后缀（两处）。
- 0003-configure-umask.patch：configure 临时目录 umask 022。
- 0004-src-pragha-cmdline-selftest.patch：新增 --selftest 无头选项
  （GOptionEntry 回调，先于 GTK 窗口激活执行，exit 0/1）。

## 依赖版本

- glib/2.84.0.1（gio-2.0 >= 2.36 满足）
- gtk/3.24.43（gtk+-3.0 >= 3.8.0 满足，broadway 后端）
- gstreamer/1.28.3（gstreamer-1.0 / gstreamer-base-1.0 >= 0.11.90 满足）
- sqlite3/3.53.4（>= 3.4 满足）
- taglib/1.13.1（taglib_c >= 1.8 满足）
- zlib/1.3.1.1（force 对齐）

## 知识积累

- ✅ XDT(Intl) autotools 包在 OHOS 上以 intltool/gettext shim 应答 configure 探针；intltool-merge shim 按真实语义产出 .desktop（ref: manifest knowledge_gained #1，配方 `_write_i18n_tool_shims`）。
- ✅ glib(musl proxy-libintl) 消费者需在 glib-2.0.pc 既有 Libs 行合并 -lintl（ref: manifest knowledge_gained #2，sound-juicer 同模式）。
- ✅ conan gstreamer 包 pc 名无 -1.0 后缀，消费者用重定向 .pc 映射 gstreamer-1.0 / gstreamer-base-1.0（ref: manifest knowledge_gained #3，配方 `_write_redirect_pkgconfig`）。
- ✅ gtk 图(glib) 与 gstreamer 图(glib2) 并存时以 zlib force 对齐版本使依赖图可解（ref: manifest knowledge_gained #4）。
- ✅ glib(shared)/glib2(static) 双提供者同图致静态遮蔽（GObject 启动 abort）：全依赖 la-free 镜像 + pc libdir 统一重写，同目录 .so 优先于 .a（ref: manifest knowledge_gained #5；知识草稿 knowledge/drafts/E429-draft-A458.md）。
- ✅ pkg-config .pc 不允许重复 Cflags/Libs 关键字行，增强必须合并进既有行（ref: manifest knowledge_gained #6，taglib_c.pc Cflags 合并实证）。

## 验证结果

```bash
# 本地无头验证（conan test_package，14 断言全过）
pragha --version      # pragha 1.3.4, rc=0
pragha --help         # Usage + 选项表（含 --selftest）, rc=0
pragha --selftest     # glib/sqlite3/GStreamer 绑定行 + all checks passed, rc=0
pragha                # GUI 路径：无显示 → fail closed rc≠0（Cannot open display）
```
GUI 交互无法自动化（OHOS PC 无 X server），如实说明。
- conan create：成功（日志见 reports/ 与 .ci-result.json 记录哈希）。
- test_package：14 断言 0 失败（--version/--help/--selftest/no-display）。
- make check：空跑通过（上游无测试入口，见上方清点）。
---

**编译结束**: 2026-10-14 20:33
**最终状态**: built
