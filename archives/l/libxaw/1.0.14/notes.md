# libxaw 1.0.14 适配笔记

> 上游库名 **libXaw**（X.Org Athena Widgets，大写 X/A）；本仓按主流小写约定
> 取包名/目录名 `libxaw`（先例：libx11 ← libX11、libxmu ← libXmu、libxt ←
> libXt、libxpm ← libXpm）。1.0.14 是 Debian/Ubuntu 现行版本
> （`2:1.0.14-1`），上游只有 `.tar.gz` / `.tar.bz2`（`.tar.xz` 自 1.0.15 起）。

## 上游形态

- 源码：`https://xorg.freedesktop.org/releases/individual/lib/libXaw-1.0.14.tar.gz`
  sha256 `59cfed2712cc80bbfe62dd1aacf24f58d74a76dd08329a922077b134a8d8048f`
  （已与 `www.x.org` 官方镜像交叉核对一致）。tarball 自带预生成的 `configure`
  （GNU Autoconf 2.69 生成，642 KB），**无需 autoreconf**。
- 一次构建产出**两个共享库**（同一份源码、两套编译宏）：
  - `libXaw6`：`-DOLDXAW`，`-version-info 6:1:0` → `libXaw6.so.6.0.1`，SONAME `libXaw.so.6`
  - `libXaw7`：`-DXAW7`，`-version-info 7:0:0` → `libXaw7.so.7.0.0`，SONAME `libXaw.so.7`
  - `install-exec-hook` 另建 `libXaw.so` → libXaw7（Xaw7 是现代默认），
    以及 `libXaw.so.6` / `libXaw.so.7` 兼容名。configure.ac 自带
    `libtool_hack`，把 libtool 的 `soname_spec` 改成 `libXaw.so.$major`，
    因此两个库的 SONAME 都是**无 libXaw6/libXaw7 前缀**的 `libXaw.so.6/.7`。
- 头文件只有一套（`include/X11/Xaw/*.h`），两库共用；`XawInit.h` 用 `OLDXAW`
  宏区分 `XawVersion`（`7000002L` / `6700002L`）并在 OLDXAW 下裁掉
  `XawInitializeDefaultConverters()`。
- **上游无自动化测试套件**：`Makefile.am` / `src/Makefile.am` 全仓无
  `TESTS`、`check_PROGRAMS`，`make check` 是空操作（0 用例）。1.0.14 的
  tarball 顶层只有 `include/ man/ old-doc/ specs/ src/`，**没有 `examples/`
  目录**（1.0.16 才带 `examples/` 的交互式 demo），故不存在可自动化的上游
  示例。`build()` 中仍保留 `make -j1 check`，以捕获未来上游新增测试。
- **两库 widget 集合的差异只有 Tip**：`src/Makefile.am` 里
  `libXaw7_la_SOURCES = $(COMMON_SOURCES) Tip.c`，`libXaw6_la_SOURCES =
  $(COMMON_SOURCES)`；`Tree.c` 属 COMMON_SOURCES，`Tree.h` 的
  `extern WidgetClass treeWidgetClass` 也未被 `#ifndef OLDXAW` 包住
  （`llvm-nm -D` 实测 libXaw6.so.6.0.1 导出 `treeWidgetClass`）。
  实测符号面：libXaw7 导出 25 个 `*WidgetClass` 符号、libXaw6 导出 24 个，两者
  差异只有 `tipWidgetClass`（即 24 个共有类）。契约测试的两张表（16 / 15）是这
  套 widget 的**子集**——libXaw7 表取 16 个，libXaw6 表取其中 15 个（去掉 Tip）。

## 依赖轨道（W0 预检结论）

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| libx11 | 1.8.13（force=True） | ohpcd ✓ | 对齐 libxmu/1.3.1.1 的 .la 保留轨 |
| libxext | 6.4.0.1 | ohpcd recipe ✓ / binary 需重建 | package_id 随 libx11 变更 |
| libxt | 1.3.1 | ohpcd ✓ | configure 的 `xt` 模块 |
| libxmu | 1.3.1.1 | ohpcd ✓ | configure 的 `xmu` 模块（XAW6/XAW7 都要） |
| libxpm | 3.5.17 | ohpcd recipe ✓ / binary 需重建 | 仅 XAW7 需要 |
| xorgproto | 2025.1 | ohpcd ✓ | xproto / xextproto 头 |

传递依赖：libxau/1.0.11、libxcb/1.17.0、libxdmcp/1.1.5、xtrans/1.4.0、
libsm/1.2.6、libice/1.1.2（经 libxt）。

**两条 libx11 轨的取舍**：仓内 X11 族同时存在 1.8.13 轨与 cmd-pkgs 6.4.0 轨。
libxmu/1.3.1.1 以 `force=True` 钉 libx11/1.8.13（其 `_prepare_ohos_libtool_shadow()`
必须拿到 `libX11.la`，而 libx11/6.4.0 的 `package()` 会删掉 `.la`），
libxpm/3.5.17 则钉 libx11/6.4.0。`conan graph info` 实测两处 force **不冲突**，
图根的 1.8.13 胜出：`Overrides: libx11/6.4.0: ['libx11/1.8.13']`。
代价是 libxext/6.4.0.1 与 libxpm/3.5.17 的 package_id 由 `e647863c` 变为
`eab79208`，已发布二进制不再命中 → 两者在本地/CI **源码重建**（两者配方
均自带 linker-view `.la` 重定位，libxext 正是为源码重建而重出的 `.1` 修订）。

## OHOS 适配要点

1. **交叉 configure（`--build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos`）**：
   用 `/system/bin/sh` 执行 `configure-ohos` 副本。显式交叉可保证 autoconf
   **不 RUN conftest 二进制**（OHOS worker 上执行新编译产物属已知脆弱点）。
2. **configure umask 077→022**（生成 `configure-ohos`，`count==2` 契约校验）：
   config.status 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录后往里写
   `subs*.awk`，HMFS 上 0700 目录的写会被拒（Permission denied）。TMPDIR 重定向
   无效（conf 目录建在 cwd）。知识草稿 DRAFT-E565。
3. **build-local linker-view**：`generate()` 阶段把依赖的 `.la` 收集到
   `<build>/linker-view`，`libdir` 改写为 view，`dependency_libs` 里的 `.la`
   绝对路径换成 `-L<view> -l<name>`；`LDFLAGS=-L<view>` 注入 configure。
   这样 libtool 既不会因 libxcb.la 等陈旧路径失败，也不会把缓存绝对路径写进
   发布元数据。链接完 `package()` 删除 `libXaw6.la` / `libXaw7.la`。
4. **pkg-config 模块名对齐**：libxmu/1.3.1.1 的组件 PC 名是 `libxmu`，而
   libXaw 的 `PKG_CHECK_MODULES(XAW*, ... xmu)` 需要上游模块名 `xmu`；
   在**消费侧**（本配方的 `PkgConfigDeps`）把 `libxmu::xmu` 的
   `pkg_config_name` 覆写为 `xmu`，无需重出 libxmu 制品。同理覆写
   libx11→x11、libxext→xext、libxpm→xpm。
5. **config.sub 补丁**：1.0.14 自带 config.sub 是 2020-06-20 版，不认识
   `linux-ohos`，`aarch64-linux-ohos` 会被判为 `system 'ohos' not recognized`，
   即使放宽也会被下方 `linux*) os=linux-gnu` 分支改写。补丁把 `linux-ohos*`
   同时加进 `maybe_os` 列表与 portable OS 列表，得到
   `aarch64-unknown-linux-ohos`。
6. **组件化导出**：`package_info()` 用 `cpp_info.components["xaw7"]` /
   `["xaw6"]` 分别导出 `libXaw7` / `libXaw6`，并各自列全直接依赖
   （Conan 2 要求每个直接依赖都被某个组件引用，否则报
   "direct dependency not used by any requires"）。另设
   `cmake_file_name=libxaw`、`cmake_target_name=libxaw::libxaw`、
   `cmake_target_aliases=["libxaw::Xaw7"]`，并在 `buildenv_info` /
   `runenv_info` 追加包内 `lib/pkgconfig`，让消费者经 pkg-config 也能解析。

## 源码修改

仅 1 个补丁（`patches/0001-config.sub.patch`，纯可移植性改动，不触源码逻辑）：

```diff
--- a/config.sub
+++ b/config.sub
@@ -133,6 +133,7 @@
 		case $maybe_os in
 			nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc \
 			| linux-newlib* | linux-musl* | linux-uclibc* | uclinux-uclibc* \
+			| linux-ohos* \
@@ -1388,7 +1389,7 @@
 	     | midnightbsd* | amdhsa* | unleashed* | emscripten* | wasi* \
-	     | nsk* | powerunix* | genode*)
+	     | nsk* | powerunix* | genode* | linux-ohos*)
```

## 编译步骤

```bash
cd archives/l/libxaw/1.0.14
conan create . \
  -pr:h=$PWD/../../ci/conan/profiles/ohos-aarch64 \
  -pr:b=$PWD/../../ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

实际执行的 configure（由 `_configure_ohos()` 组装，`/system/bin/sh` 执行
`configure-ohos` 副本）：

```
/system/bin/sh <build>/configure-ohos \
  --srcdir=<src> \
  --build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos \
  --enable-shared --disable-static --prefix=/ ... \
  --disable-docs --disable-specs --without-xmlto --without-fop --without-xsltproc \
  LDFLAGS=-L<build>/linker-view
```

随后 `make -j1` → `make -j1 check`（空操作）→ `make -j1 install DESTDIR=<pkg>`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub: system 'ohos' not recognized` | 1.0.14 自带 config.sub（2020-06-20）无 ohos 分支；且 `linux*)` 分支会把 linux-ohos 改写成 linux-gnu | `0001-config.sub.patch` 同时补 `maybe_os` 与 portable OS 两处 |
| 2 | `config.status` 建 confXXXXXX 临时目录后写 subs*.awk 报 Permission denied | HMFS 上 umask 077 产生的 0700 目录对该进程不可写（E002/DRAFT-E565） | 生成 configure-ohos 副本，`umask 077`→`022`（count==2 契约） |
| 3 | libtool 报 `libxcb.la is not a valid libtool archive` / 依赖 `.la` 指向已清理的构建目录 | conan 制品里的 `.la` 记录了绝对路径，跨包/跨构建失效 | build-local linker-view：`.la` 重定位 + `LDFLAGS=-L<view>` |
| 4 | `PKG_CHECK_MODULES(XAW*, ... xmu)` 找不到 `xmu.pc` | libxmu/1.3.1.1 导出的组件 PC 名是 `libxmu` | 消费侧 `pkg_config.set_property("libxmu::xmu", "pkg_config_name", "xmu")` |
| 5 | libxext/6.4.0.1、libxpm/3.5.17 需源码重建（package_id 随 libx11 变更） | 两条 libx11 轨导致 package_id 变化 | 依赖配方自带 linker-view，源码重建即可通过（本仓既有模式） |

## 依赖版本

见上文「依赖轨道」表。

## 验证结果

```bash
$ conan create archives/l/libxaw/1.0.14 -pr:h=... -pr:b=... --build=missing --user=ohpcd --channel=stable
...
libxaw/1.0.14@ohpcd/stable (test package): RUN: "./libxaw7_widget_set_contract"
libXaw7 widget-set contract passed (16 classes, XawVersion 7000002)
libxaw/1.0.14@ohpcd/stable (test package): RUN: "./libxaw6_widget_set_contract"
libXaw6 widget-set contract passed (15 classes, XawVersion 6700002)
```

产物与 SONAME（`llvm-readelf -d`）：

```
libXaw6.so.6.0.1   SONAME libXaw.so.6
libXaw7.so.7.0.0   SONAME libXaw.so.7
libXaw.so -> libXaw7.so（install-exec-hook）
```

NEEDED（两库一致，`llvm-readelf -d` 实测）：libXmuu.so.1、libXmu.so.6、
libXpm.so.4、libXext.so.6、libXt.so.6、libX11.so.6、libxcb.so.1、libSM.so.6、
libXdmcp.so.6、libXau.so.6、libICE.so.6、libc.so。
（注：libXaw6 的上游 `XAW6_LIBS` 不含 xpm，但 `AutotoolsDeps` 把全部依赖库放进
`LIBS`，故 libXaw6 也记录 `libXpm.so.4` / `libXmuu.so.1` 依赖；与仓内其它 X11
配方一致，且 libxpm 本就是 libxaw 的包级依赖，不影响消费者。）

包内布局：`include/X11/Xaw/*.h`、`lib/libXaw*.so*`、`lib/pkgconfig/xaw{6,7}.pc`
（prefix 重定位为 `${pcfiledir}/../..`）、`licenses/COPYING`；`lib/` 下无 `.la`。

## 注意事项

1. **1.0.14 与 1.0.16 的关系**：仓内另有未合并的 libxaw 1.0.16 PR（#9432，
   `feat/libxaw-1.0.16`）。两者源码 URL/sha256/补丁行号不同（1.0.16 有
   `.tar.xz` 且自带 config.sub/config.guess 更新），配方本体结构一致；
   1.0.14 是 Debian/Ubuntu 现行版本，供下游 xdu / xmix 等 Athena Widgets
   消费者使用。两个版本目录可并存（同 libx11 多版本先例）。
2. **下游**：libxaw built 后，xdu 3.0 / xmix 2.1 的「缺 libXaw」硬缺口解除
   （xdu 变 A 类；xmix 仍受 OSS `/dev/mixer` 子系统限制，维持 C 类）。
3. **config.sub/config.guess 的 umask 陷阱**：若改为不传 `--build`（让
   configure 自己跑 config.guess 猜 build 三元组），则还需补 config.guess 的
   HarmonyOS 分支——否则 2020 版 config.guess 会在 `set_cc_for_build` 里用
   0700 临时目录写 dummy.c 而失败（同 E002）。本配方用显式 `--build`
   规避，只需 config.sub 一个补丁。
4. **RUNPATH 指向 build-local linker-view（X11 族既有共性，非本配方引入）**：
   `llvm-readelf -d` 显示两个库的 RUNPATH 是
   `<build>/linker-view:<build>/linker-view`，该路径在装包后不存在。对同族
   已上架制品实测结果一致——libxpm/3.5.17、libxext/6.4.0.1（本机重建）与
   从 ohpcd 拉取的 libxmu/1.3.1.1、libxt/1.3.1 都带同款 build 目录 RUNPATH
   （libxmu/libxt 指向 `…/build-release/libtool-shadow`），只有 libx11/1.8.13
   无 RUNPATH。成因是 libtool 对 `-L` 依赖目录做 hardcode。运行时加载依赖
   走 Conan 依赖包的 `libdir`（`package_info` 已导出），不依赖该 RUNPATH，
   故不影响使用；保持与同族制品一致，未额外加装置去除。
---

**编译结束**: 2026-10-13 18:36
**最终状态**: built
