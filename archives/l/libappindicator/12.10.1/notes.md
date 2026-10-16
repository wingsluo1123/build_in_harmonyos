# libappindicator 12.10.1 适配笔记（HarmonyOS PC / OHOS 6.0 aarch64）

## 编译环境

| 项 | 值 |
|----|----|
| 构建系统 | autotools（autoreconf 生成 configure） |
| 编译器 | clang 15（`aarch64-unknown-linux-ohos-clang`，OHOS 6.0 SDK） |
| sysroot | `/root/ohpc/sdk/ohos-6.0/native/sysroot` |
| 本地验证 | WSL2 Ubuntu 22.04（x86_64 交叉）+ qemu-aarch64-static + OHOS musl 运行根 |
| CI worker | `ci/conan/build_and_test.sh` → `conan create`（交叉构建 + qemu 运行测试） |
| 状态 | published |

## 源码身份（R39 相关，重要）

上游 Canonical `libappindicator`（<https://launchpad.net/libappindicator>）**从未发布
12.10.1 的 release tarball**：12.10 系列 Launchpad 官方下载只有 12.10.0
（`libappindicator-12.10.0.tar.gz`）。12.10.1 是 12.10 分支的维护快照
（`lp:libappindicator` trunk），业界发行版统一以「12.10.1+20.10.20200706.1」
这一快照版本号发行，本配方与之一致：

* Ubuntu 源码包 `libappindicator 12.10.1+20.10.20200706.1`（orig tarball，上游
  快照原样打包，未做 Debian 化裁剪，tarball 内无 `debian/` 目录）
* NixOS/nixpkgs 同名版本（`fetchgit` 同一提交 `fe25e53bc7e39…`）
* Fedora `libappindicator-12.10.1`

采用 URL（`conandata.yml` 中另列 Ubuntu pool 镜像作回退）：

```
https://launchpad.net/ubuntu/+archive/primary/+files/libappindicator_12.10.1+20.10.20200706.1.orig.tar.gz
sha256 94e7096a49c400628ecddcafe313d63bf917d95a90ab994930909de724604e0a   (75204 bytes)
```

本地逐字节核验：launchpad.net 官方归档与 mirrors.tuna.tsinghua.edu.cn 的
`ubuntu/pool/universe/liba/libappindicator/` 同名文件 sha256 一致；`gzip -t` 通过。
注意 tarball 内 `configure.ac` 的 `AC_INIT` 版本串仍是 `12.10.0`（上游裁分支时未
改版本号），发行版一致以包版本号 12.10.1 为准。

## 编译步骤（`conanfile.py`）

1. `source()`：下载上游快照（无顶层目录，`strip_root=False`）与 libdbusmenu
   16.04.0（`strip_root=True` → `libdbusmenu-src/`）。
2. `generate()`：
   * `PkgConfigDeps` 生成依赖 .pc；对 glib 系 .pc 追加 `-lintl`
     （glib 的 proxy-libintl 提供 `g_libintl_*` 符号）。
   * 构建环境：`PKG_CONFIG_PATH = <generators> : <build_folder>/prefix/lib/pkgconfig`，
     `LD_LIBRARY_PATH` 前缀为私有 prefix 与各依赖 libdir，`TMPDIR/TMP/TEMP`
     指向构建私有目录（HMDFS 上系统 /tmp 与相对临时目录都不可靠）。
   * `AutotoolsToolchain`：`--with-gtk=3`、`--enable-tests`。
3. `build()`：
   * `apply_conandata_patches()`（4 个补丁，见下）
   * 依赖包 libtool 归档（`*.la`）就地重定位（见问题 9）
   * 随包构建 libdbusmenu 16.04.0 → `build_folder/prefix`
     （`--with-gtk=3 --disable-static --disable-nls --disable-dumper
     --disable-tests --disable-vala`）
   * `autoreconf -fi -I m4` → 构建期注入 `config.sub` 的 linux-ohos 支持 +
     `configure` 临时目录 umask 022 → `configure` → `make`
   * `make -C tests test-libappindicator test-simple-app`（编译不依赖 dbus-glib 的
     2 个上游测试程序）
4. `package()`：`make install -j1` + libdbusmenu 运行库/头文件/.pc 随包交付 +
   `.pc` prefix 重定位 + 去 `DT_RUNPATH` + OHOS 上
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`。

## 随包交付 libdbusmenu 16.04.0（R49 私有 prefix）

**为什么必须随包构建**：上游 `configure.ac` 硬依赖
`PKG_CHECK_MODULES(LIBRARY, … dbusmenu-gtk3-0.4 >= 0.5.90)`，`src/app-indicator.c`
直接调用 `dbusmenu_*` API。制品仓实测未发布该依赖：

```
$ conan list "*dbusmenu*/*" -r ohpcd      # 空
```

按「一库一 PR / 禁止捎带」（PF1/R36）不能在本 PR 新增独立包，故按 R49 把上游
Canonical 官方 `libdbusmenu-16.04.0.tar.gz`（sha256 `b9cc4a2a…`）构建进
**`build_folder/prefix`**：

* 注入方式只指向私有 prefix（`PKG_CONFIG_PATH`/`LD_LIBRARY_PATH`），**没有**写入
  `/usr/local` 等共享位置（R49 三条禁令均未触碰）。
* 交付内容（保留上游布局）：`lib/libdbusmenu-glib.so{,.4,.4.0.12}`、
  `lib/libdbusmenu-gtk3.so{,.4,.4.0.12}`、
  `lib/pkgconfig/dbusmenu-glib-0.4.pc`、`dbusmenu-gtk3-0.4.pc`、
  `include/libdbusmenu-glib-0.4/libdbusmenu-glib/*.h`（7 个）、
  `include/libdbusmenu-gtk3-0.4/libdbusmenu-gtk/*.h`（5 个）、licenses。
* 交付理由（诚实申报）：上游 C 头文件与上游测试源码会直接
  `#include <libdbusmenu-glib/…>`，且 `appindicator3-0.1.pc` 的
  `Requires: dbusmenu-glib-0.4 gtk+-3.0` 需要该 .pc 可解析；不交付则消费方无法
  编译。PR 描述中已单列说明，供审查判断。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf -fi` 报 `GTK_DOC_CHECK`/`AM_PROG_VALAC` 未定义 | OHOS 构建镜像无 `gtk-doc.m4`（gtk-doc-tools）与 `vala.m4`（vala） | 0001 补丁移除这两个宏调用，并停建 docs/（API 文档不属于交付物） |
| 2 | `automake` 报 `cannot open < gtk-doc.make`，以及 `SUBDIRS must be set with '=' before using '+='` | `docs/reference/Makefile.am` 有 `include $(top_srcdir)/gtk-doc.make`（由 gtkdocize 生成，不可用）；`SUBDIRS` 是折行列表，直接删末项会给上一行留下悬空 `\`，注释行更是 `comment following trailing backslash` 错误 | 0001 从 `AC_CONFIG_FILES` 去掉 docs 生成项（**宏参数内不能写注释**，`#` 会被当参数 → `` `#' is already registered with AC_CONFIG_FILES``）；0002 从 `SUBDIRS` 去掉末项 `docs` 并同时去掉 `bindings` 行的续行反斜杠 |
| 3 | `configure` 拒绝 `--host=aarch64-linux-ohos` | ① `autoreconf` 从构建机 automake 复制 `config.sub`，其基本系统类型白名单不含 `ohos*`；② 2022+ 版 config.sub 另有一张 kernel-os 配对白名单，`linux-ohos` 落到 `*-*` 兜底 → `Invalid configuration 'aarch64-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'`（E007） | `build()` 在生成后往两张白名单各注入一项（`gnu*\|android*\|ohos*\|bsd*` 与 `linux-ohos*` 配对），并回读校验注入生效；文件随构建机版本变化，不能用稳定 .patch |
| 4 | HMDFS 上 `configure` 建临时目录失败（E114/E236 同类） | autoconf 生成的 configure 用 `umask 077 && mktemp -d ./confXXXXXX`，HMDFS 拒绝 umask 077 下自建目录 | `build()` 把生成的 configure 中两处 `umask 077` 改为 `umask 022`（strict=False，匹配不到不报错） |
| 5 | `conan create` 报 `Version conflict: glib/2.88.0 vs glib/2.84.0.1` | dbus-glib/0.114 锁 glib/2.88.0，gtk/3.24.43 链 pin glib/2.84.0.1 | 顶层 `self.requires("glib/2.84.0.1", force=True)` 统一（两版本并存会生成同名 .pc 互相覆盖） |
| 6 | 按 dbus-glib 配方对 glib 2.84 源码重建失败 | 该配方按 glib 2.88（静态）布局手工拼 CFLAGS/LIBS | 0003 补丁把上游 `TESTDEPS`（dbus-glib-1）探测改为非致命；tests/ 中 6 个使用 dbus-glib 的程序不编译（它们同时需要 Xvfb + dbus-test-runner，OHOS 本就不可运行）——完整报错：`ld.lld: error: unable to find library -lgio-2.0 / -lglib-2.0 / -lffi` |
| 7 | 上游 `make check` 的 4 个 TESTS 无法在 OHOS 运行 | 生成的脚本固定 `export DISPLAY= ; . run-xvfb.sh ; dbus-test-runner --dbus-config /usr/share/dbus-test-runner/session.conf`；OHOS 的 GTK 只有 broadway 后端（无 X11/Xvfb），且根文件系统只读无法安放 `/usr/share/dbus-test-runner/session.conf` | 不执行这 4 个脚本；改为真实执行可运行的上游单元测试（9 个 g_test 用例，见 MANIFEST.yml） |
| 8 | 需显示后端才能跑上游单元测试 | 上游 `main()` 先 `gtk_init()`（无显示立即退出，E471；broadwayd 在 OHOS 上未签名会 EPERM） | `test_package` 从 gtk 依赖包取 `broadwayd` → OHOS 上先 `--remove-section .codesign` + `binary-sign-tool -selfSign 1` 自签名 → 拉起 `:5`；客户端必须 `GDK_BACKEND=broadway DISPLAY=:5 BROADWAY_DISPLAY=:5`（见问题 13） |
| 9 | `make` 链接失败：`libtool: error: '//lib/libfreetype.la' is not a valid libtool archive`（伴随大量 `library ... was moved` 警告） | 制品仓依赖包里的 `*.la` 记录了发布构建机前缀，个别 `libdir='/'`，libtool 读取后拼出 `//lib/…` 死路径 | `build()` 前把各依赖包 `lib/*.la` 的 `libdir=` 改写为本机实际目录、`dependency_libs=` 清空（同 xauth 1.1.4 / libxp 1.0.4 既有做法；共享库链接不需要 .la 的传递依赖，`gtk+-3.0.pc` 已给全链接行） |
| 10 | `make install` 报 `cannot create regular file …/app-indicator-enum-types.h: File exists` | 上游 `src/Makefile.am` 把该头文件同时列进 `libappindicatorinclude_HEADERS` 与 `nodist_libappindicatorinclude_HEADERS`，`-j16` 并行安装同一目标文件竞争 | `package()` 用 `make install -j1`（串行） |
| 11 | test_package 编译报 `fatal error: 'hb.h' file not found` | 制品仓 `pango/1.50.14.1.1` 未对 harfbuzz 声明 `transitive_headers`，而 `gtk.h → gdk.h → pango/pango.h → pango-coverage.h` 直接 `#include <hb.h>` | 配方显式 `self.requires("harfbuzz/14.2.0.1.1.1", transitive_headers=True, transitive_libs=True)` 补全头闭包 |
| 12 | 随包 dbusmenu 头文件在消费方找不到 | `package()` 原用 `copy(self, "*.h", src=<prefix>/include/libdbusmenu-glib-0.4 …)` 只取顶层，而上游头文件在下一级 `libdbusmenu-glib/` 子目录 | 改为 `shutil.copytree` 整棵子树复制；`cpp_info.includedirs` 同时暴露 `include/libappindicator3-0.1`、`…/libappindicator`、`include/libdbusmenu-glib-0.4`、`include/libdbusmenu-gtk3-0.4` |
| 13 | 上游/消费者用例报 `cannot open display: :5`，改为 `localhost:8055` 也连不上 | broadwayd 默认只听 unix socket（实测 `broadwayd --port 8055 :5` → `Listening on /run/user/0/broadway6.socket`），GDK broadway 后端的显示名必须是同一个 `:N`；只给 `DISPLAY` 不给 `BROADWAY_DISPLAY` 时 GDK 报 `cannot open display: :5` | 客户端环境统一 `GDK_BACKEND=broadway DISPLAY=:5 BROADWAY_DISPLAY=:5`（实测该组合 TAP 输出正常、exit=0） |
| 14 | 消费者用例偶发 `qemu: uncaught target signal 11 (Segmentation fault)`（5 次里 1 次），并在 `.desktop` 段前打印 `gtk_widget_get_visible: assertion 'GTK_IS_WIDGET (widget)' failed` | 用例里对 `gtk_menu_new()` 的 **浮动引用** 调了 `g_object_unref()`：`app_indicator_set_menu()` 内部 `g_object_ref_sink()` 已把该浮动引用转为指示器自己的强引用（upstream `app-indicator.c:2261`），再 unref 就把指示器唯一引用放掉 → 菜单被析构而指示器留悬垂指针 | 删除该 `g_object_unref()`（upstream 测试同样不 unref）；修复后 5/5 次复跑 27/27 通过、0 条 Gtk-CRITICAL |
| 15 | 发布件 `DT_RUNPATH` 里写进了 conan 缓存/私有 prefix 构建机路径 | libtool 链接时把安装前缀与依赖 libdir 硬编码进 RUNPATH（同族已发布制品 gtk/3.24.43、glib/2.84.0.1 均无 RUNPATH；xcfa 消费方用例把「无 RPATH/RUNPATH」列为自检项） | `package()` 在签名**之前**用 `patchelf --remove-rpath` 清除（签名是内容哈希，改字节会失效）；缺 patchelf 时告警跳过 |
| 16 | **CI 首次失败（#65065）**：`configure: error: cannot guess build type; you must specify one`（失败点 `_build_libdbusmenu()` 的 configure） | CI worker 是 HarmonyOS PC，`conan create` 为**原生构建**（`cross_building=False`）→ AutotoolsToolchain 不注入 `--build/--host`；随包 libdbusmenu 16.04.0 自带 2015-08-20 版 `config.guess`，其 `uname -s` 表不认 `HarmonyOS`/`HongMeng Kernel 1.12.0`（CI 日志原文 `uname -s = HarmonyOS`）→ 探测直接失败 | ① 随包 libdbusmenu 的 configure 显式给 GNU 三元组（`--build=<build机> --host=<目标>`，该版 config.sub 也不认 `ohos`，故用 `*-linux-gnu`，与 xprop/1.2.8、xauth/1.1.4 处理 E007 同款）；② libappindicator 主包仅在**原生构建**时补同款 `--build/--host`（交叉构建时 toolchain 自己注入 `--host=aarch64-linux-ohos --build=x86_64-linux-gnu`，本地验证路径行为不变）；CI 原生场景 host==build → configure 走非交叉分支、conftest 在真机上真实执行 |
| 17 | **CI 二次/三次失败（#65144、#65460）**：`./config.status: line 836: ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（失败点都是 `_build_libdbusmenu()` 的 configure） | autoconf 生成的 `configure`/`config.status` 里有**写死的子 shell** `(umask 077 && mktemp -d "./confXXXXXX")`（回退分支 `(umask 077 && mkdir "$tmp")`），在其中写 `subs1.awk` 后**二次读取**；OHOS 文件系统（HMFS/HMDFS）拒绝这套「私有临时目录 + 二次读取」的权限模型（E114/E236 同类）。本地实证：该行 umask 077 → 目录 0700 / 文件 0600；改为 022 → 目录 0755 / 文件 0644 | 随包 libdbusmenu 的 `configure` **文本改写**这两处 `umask 077`→`022` 并回读校验。关键坑：**在外层 shell 里 `umask 000 && configure` 无效**（首次修复尝试，CI #65460 实证仍失败）——那两处 umask 在脚本自己的子 shell 内，外层 umask 影响不到；且 `configure` 会把这两行**原样复制**进它生成的 `config.status`（本地逐行比对 `configure:2453/2458` ↔ `config.status:546/551`），故改写 `configure` 即同时修好配置期与运行期。主包 configure 用同一改写（原有逻辑，见问题 4） |

| 18 | **CI 四次/五次失败（#65468、#65495）**：`/data/service/hnp/bin/bash: /data/service/hnp/bin/glib-mkenums: /usr/bin/perl: bad interpreter: No such file or directory` → `make[2]: *** [Makefile:1096: stamp-enum-types] Error 126`（失败点 `_build_libdbusmenu()` 的 make） | CI worker 上 `glib-mkenums` 解析到 **HNP 的 perl 版**脚本，shebang 写死 `#!/usr/bin/perl`，而 HarmonyOS PC 上 perl 在 `/data/service/hnp/bin/perl`（本地 WSL 侧同名工具是 python3 版，故本地从不复现——这也是它前几轮没暴露的原因） | 用 configure 的 **AC_ARG_VAR 接口**注入 `GLIB_MKENUMS=<依赖包内可用实现的绝对路径>`。**关键教训**：只往 PATH 前面塞 shim **不管用**——configure 用 `AC_PATH_PROG` 取 PATH 中第一个匹配（CI #65495 实证仍命中 `/data/service/hnp/bin/glib-mkenums`），并把该**绝对路径固化进生成的 Makefile**，之后再改 PATH 无效；`GLIB_MKENUMS` 在 `AC_ARG_VAR` 列表里（configure:726），环境变量直接覆盖探测结果（同 xauth 1.1.4 用 XAUTH_CFLAGS/LIBS 绕过 pkg-config 的思路）。另留一个 `tools-shim/glib-mkenums` 包装，供没有该逃生口的调用方使用。两者都只落在本配方 build_folder 内，不改依赖包、不写共享位置 |

| 19 | **CI 六次失败（#65510）**：`sh: aclocal: inaccessible or not found` → `autoreconf: error: aclocal failed with exit status: 127`（失败点 `_build_libappindicator()` 的 autoreconf）——此时 libdbusmenu **已完整构建并安装成功**（前三处修复全部生效） | 上游 tarball 不含预生成 `configure`（autoreconf 产物不进发行包），必须自举；CI worker（HarmonyOS PC 原生构建）基础 PATH 只有 `/data/app/bin:/system/bin:/system/sbin:/vendor/bin`，**没有 aclocal**；本地 WSL 交叉构建机自带 `/usr/bin/{aclocal,automake,autoreconf}`，故本地不复现（E178） | `build_requirements()` 里**按需** tool_requires（`automake/1.18` + `libtool/2.5.4` + `autoconf/2.72`，制品仓三者均有 OHOS armv8 binary），仅在构建机缺 autotools 时触发（`shutil.which` 探测，同 xsel/1.2.1、afuse、argp-standalone 做法）。**不能无条件引入**：autoconf 会拉入 m4，而 m4 的 `printf-frexpl` 在 OHOS 交叉下汇编失败（实测 `fldcw [x9]` 3 errors），本地验证路径会被拖垮 |

| 20 | **CI 七次失败（#89171、#90732）**：随包 libdbusmenu 的 `configure` **静默 rc=1**——stdout 只到 `checking whether we are cross compiling... `（**没有 result**）、stderr **0 字节**，conan 只报 `Error in build() method, line 382 → _build_libdbusmenu()`。前两轮误判为 intltool 探测问题（`ddb6c0a5` 为此加了 fail-closed 守卫） | **真因是 `--build` 与 `--host` 相同**：`_gnu_triplet()` 只看 arch，而 CI worker 上 conan `settings.arch` 与 `settings_build.arch` **同为 armv8** ⇒ 两边都映射成 `aarch64-linux-gnu`。autoconf 见 `build == host` 即判定为**原生构建**，`cross_compiling` 停在 `no`/`maybe`，于是坚持要**运行**刚链接出的 conftest；但工具链是 OHOS 目标（`os=OHOS`），conftest 在 worker 上无法执行 ⇒ `as_fn_error "cannot run C compiled programs. If you meant to cross compile, use --host"` ⇒ rc=1。dash 下该错误路径**不留 stderr**，故表现为"静默 rc=1"（`ddb6c0a5` 的守卫因此**放行**——它查的是 intltool，不是三元组） | 新增 `_libdbusmenu_triplets()`：`--host` 用目标三元组，`--build` 用构建机三元组，**并强制二者不相等**（撞车时 `--build` 固定为 `x86_64-linux-gnu`，即 CI worker 的宿主 arch）。本地逐行复现并验证：同一环境下 `--build=aarch64-linux-gnu --host=aarch64-linux-gnu` → rc=1 卡在 cross-compiling 检查；改为 `--build=x86_64-linux-gnu --host=aarch64-linux-gnu` → `cross compiling... yes`，一路走到 `checking for DBUSMENUGTK...`，`conan create` 全程 **rc=0**。**未使用** `aarch64-linux-ohos` 作 `--host`：随包 2015 版 config.sub 不认 `ohos`，实测会停在 `checking host system type... ` 静默 rc=1 |

| 21 | **CI 八次失败（#92718）**：`replace_in_file didn't find pattern 'gnu* \| android\| bsd*' in .../src/config.sub`（失败点 `_build_libappindicator()` → `_fix_generated_autotools_files()`，即问题 3 的修复代码**自身**；此时 perl/PERL5LIB（`5566fa8cf9`）与 autoreconf 均已通过） | autoreconf 装进 src/ 的 config.sub **结构随构建机 automake 版本变**：CI 侧按需 tool_requires `automake/1.18` → 其自带 **2024-05-27 版** config.sub，基本系统类型白名单已改为**每行一项**的 `\| gnu* \ …` 列表，旧的**单行** pattern 根本不存在 → `strict=True` 替换直接抛异常；本地 WSL 用系统 automake 1.16 → **2022-01-03 版**（单行 pattern 在）故本地从不复现（同 E178 盲区）。实测 2024-05-27 版**上游已内置 ohos**（`\| ohos*`（行 2070）+ `linux-ohos*-`（行 2213），`sh config.sub aarch64-linux-ohos` → rc=0、输出 `aarch64-unknown-linux-ohos`），根本无需注入 | `_fix_generated_autotools_files()` 改为**按结构分支**：含单行 pattern 才注入两张白名单（老版路径，行为不变）；已含 `ohos*` 与 `linux-ohos*` 的直接跳过（2024+ 路径）；两者皆非则抛"结构无法识别"（fail-closed）。最后**真执行** config.sub 做行为校验（subprocess 直调 `/bin/sh config.sub <目标三元组>`，要求 rc=0、双流无 `Invalid`、stdout 含 `linux-ohos`）——比原先的子串回读强：注入失效也能抓住（负例实测：2022 版不注入 → rc=1 被拦）。两分支 + 负例在本地对真实文件仿真全部 PASS |

## 源码修改（补丁，均不触碰 `src/` 与 `tests/`）

| 补丁 | 内容 | 类型 |
|------|------|------|
| `0001-configure.ac-drop-missing-gnome-macros.patch` | 移除 `GTK_DOC_CHECK`/`AM_PROG_VALAC`；从 `AC_CONFIG_FILES` 去掉 docs 项 | portability |
| `0002-Makefile.am-drop-docs-subdir.patch` | 顶层 `SUBDIRS` 去掉 `docs`（并收掉续行反斜杠） | portability |
| `0003-configure.ac-testdeps-optional.patch` | `PKG_CHECK_MODULES(TESTDEPS, dbus-glib-1, [], [警告])` 改为非致命 | portability |
| `0004-libdbusmenu-configure-relax-intltool-probe.patch` | 随包 libdbusmenu 的 `configure`：intltool 版本探测/脚本存在性、GNU gettext、perl、XML::Parser 四处硬失败改宽松；并在 `enable_tests=no` 时补上 `HAVE_VALGRIND` 条件定义（否则 `conditional "HAVE_VALGRIND" was never defined`） —— OHOS 构建镜像无 intltool/gettext/perl | portability |

**上游测试用例源码零修改**：`test_package/upstream-test-libappindicator.c` 与上游
`tests/test-libappindicator.c` 逐字节一致（sha256 `d5fa8623fc4e23cfba7aed50bad6b22a4d3f0f518f9daab9d651a6dae04eb469`）。

## 依赖版本

* glib/2.84.0.1（force 统一；shared）
* gtk/3.24.43（shared）→ pango 1.50.14.1.1、cairo 1.18.4、cairo-gobject 1.18.4.2、
  gdk-pixbuf 2.44.6.1、atk 2.38.0.1.1、harfbuzz 14.2.0.1.1.1、freetype 2.14.3、
  fontconfig 2.18.1.1、fribidi 1.0.16、libepoxy 1.5.10、pixman 0.46.4、
  libpng 1.6.58、libtiff 4.7.2、libjpeg-turbo 3.2.0、libwebp 1.6.0、zlib 1.3.1.1、
  expat 2.8.2.1、zstd 1.5.7
* harfbuzz/14.2.0.1.1.1（显式带入，补全头闭包，见问题 11）
* libdbusmenu 16.04.0（vendored，`build_folder/prefix`，见上）
* 不依赖 dbus-glib（见问题 5/6）：test_package 与 package 均不需要

## 验证结果

本地（WSL2 x86_64 交叉 + qemu-aarch64-static + OHOS musl 运行根）实测：

| 项 | 命令 | 结果 |
|----|------|------|
| 构建 + 打包 + 测试（一次完整 `conan create`） | `conan create . -pr:h=ohos-aarch64-run -pr:b=default --build=missing` | **exit 0**（2026-09-30 14:06 CST，日志 `/root/ohpc/scratch/create-lai-4.log`） |
| 消费者端到端用例（rule12） | `./test_package`（`GDK_BACKEND=broadway DISPLAY=:5 BROADWAY_DISPLAY=:5`） | **checks=27 failures=0，display=yes**；连续复跑 **5/5 次 exit=0**，0 条 Gtk-CRITICAL（`CONSUMER_E2E_RESULT` 行） |
| 上游单元测试（未修改源码） | `./test-libappindicator --verbose` | **1..9 全 ok，exit=0**；连续复跑 **3/3 次 exit=0**（TAP `ok 1..9`） |
| 上游 automake TESTS（4 个脚本） | — | 不可运行，原因见 MANIFEST.yml（Xvfb/X11 + dbus-test-runner + 硬编码 `/usr/share` 路径） |
| 上游 8 个 check_PROGRAMS | `make -C tests test-libappindicator test-simple-app` | 编译 2/8（其余 6 个需 dbus-glib-1；原因见问题 6） |
| 制品动态段（L5a/L5b） | `llvm-readelf -d` | 3 个 .so 的 SONAME 均为相对名（`libappindicator3.so.1` / `libdbusmenu-glib.so.4` / `libdbusmenu-gtk3.so.4`）；DT_NEEDED 全为裸库名，绝对/`../` 路径计数 **0**；`DT_RUNPATH` 已清除 |
| 包体量 | `du -sh` | 592K |
| CI 失败修复验证（问题 16/17） | 本地复跑上表两条 | 三元组注入后 configure 日志为 `cross compiling... yes` / `build system type... x86_64-pc-linux-gnu`；`umask 077`→`022` 改写后 `config.status` 正常完成（构建全过程 exit 0） |

**真机端到端**（润和 DAYU200-RK3568 · OpenHarmony 6.0.0.47 API20 aarch64，
2026-10-02 00:52 CST，执行器 `device_runner.sh run lai_e2e_fix3`）：

| 项 | 命令 | 结果 |
|----|------|------|
| 消费者端到端用例（rule12，真机真实运行） | `LD_LIBRARY_PATH=. E2E_DESKTOP=./test-libappindicator.desktop ./test_package` | **checks=19 failures=0**，`CONSUMER_EXIT=0`；设备证据 `_device_evidence.json`（job `lai_e2e_fix3`，exit_code 0，`result_json_received=true`） |
| 真机与 qemu 的项数差异 | — | 真机 19 项 vs qemu 27 项：真机无 GTK 显示后端（`broadwayd` 不在设备镜像内），菜单往返 6 项按用例设计走 `SKIP`（打印 `SKIP menu roundtrip: no GTK display backend`），其余 19 项全部真实执行并通过、0 failures |

夹具路径改进（本轮）：`test_consumer.c` 改为优先读环境变量 `E2E_DESKTOP`，未设置时回退编译期 `E2E_SRCDIR`——真机部署路径与 conan 构建目录不同时也能跑，且夹具缺失时显式 `SKIP` 并说明，而不是报一个无信息量的 FAIL。

说明：上游 g_test 日志中会出现 8 行 `not ok … FATAL-WARNING: Unable to get the
session bus … Bail out!`，来自 libdbusmenu 派生的子进程（OHOS 无 D-Bus session
bus，`/run/dbus/system_bus_socket` 不存在）；用例本体（父进程）9 个用例全部
`ok`，进程退出码 0，故判定通过。消费者用例里同一原因出现
`Unable to get the session bus` 警告，不影响断言。

## 交付物

```
lib/libappindicator3.so -> .so.1 -> libappindicator3.so.1.0.0      (SONAME libappindicator3.so.1)
lib/libdbusmenu-glib.so -> .so.4 -> libdbusmenu-glib.so.4.0.12     (SONAME libdbusmenu-glib.so.4)
lib/libdbusmenu-gtk3.so -> .so.4 -> libdbusmenu-gtk3.so.4.0.12     (SONAME libdbusmenu-gtk3.so.4)
lib/pkgconfig/appindicator3-0.1.pc                                 (prefix=${pcfiledir}/../..)
lib/pkgconfig/dbusmenu-glib-0.4.pc
lib/pkgconfig/dbusmenu-gtk3-0.4.pc
include/libappindicator3-0.1/libappindicator/app-indicator.h
include/libappindicator3-0.1/libappindicator/app-indicator-enum-types.h
include/libdbusmenu-glib-0.4/libdbusmenu-glib/{client,dbusmenu-glib,enum-types,menuitem,menuitem-proxy,server,types}.h
include/libdbusmenu-gtk3-0.4/libdbusmenu-gtk/{client,dbusmenu-gtk,menu,menuitem,parser}.h
licenses/{COPYING,COPYING.2.1,COPYING-GPL3,COPYING.LGPL.2.1}
```

## 注意事项

* 消费方编译路径：`appindicator3-0.1.pc` 的
  `Cflags: -I${includedir}/libappindicator3-0.1`，即
  `#include <libappindicator/app-indicator.h>`；`cpp_info.includedirs` 另含
  `…/libappindicator3-0.1/libappindicator`，使上游那种 `#include <app-indicator.h>`
  写法也能编译（上游 tests/、example/ 即如此）。
* 随包交付的 dbusmenu 库与 .pc 位于同一个包内（`lib/`、`lib/pkgconfig/`），
  conan 消费者由 CMakeDeps/PkgConfigDeps 生成的 .pc 解析，无需额外 remote。
* `CONSUMER_E2E_RESULT` 里 `new_label_signals=0` 是用例有意为之：校验「值不变不
  发信号」前把计数器清零，信号语义由 check 09/10 断言（1 次 / 0 次）。
* 6 个 dbus-glib 测试程序未编译的原因见问题 6；它们即便编译也无法在 OHOS 运行
  （问题 7），故未采用「强行引入 dbus-glib」的方案。
