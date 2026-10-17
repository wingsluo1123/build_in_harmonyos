# wxsvg 1.5.25 适配笔记

## 编译环境
- 构建系统: autotools（configure + make；libtool 产 .so/.a）
- 编译日期: 2026-10-13（探索构建）/ 同日 conan 化
- 编译器: clang/clang++ 15.0.4（OHOS PC 原生 arm64）
- 状态: published（探索全链 PASS 后进入 conan 化）

## 软件形态
- 库包（R38）：libwxsvg.so.3.12.8（SONAME libwxsvg.so.3，LIBRARY_VERSION 15:8:12）
  + 头文件（include/wxSVG/）+ libwxsvg.pc；**不打包** svgview 演示程序
  （上游 svgview_LDADD=../src/libwxsvg.la 是全链链接验证品，无 commands.json）
- 上游 AC_INIT 仍写 1.5.24（上游打包笔误，tarball 即 1.5.25），conan 版本以 1.5.25 为准

## 编译步骤

```bash
# 探索构建（.work 目录，E533 补丁后）：
CONFIG_SHELL=/data/service/hnp/bin/bash bash ./configure \
  --prefix=<prefix> --disable-dependency-tracking
make -j8 && make install DESTDIR=... MKDIR_P=/bin/mkdir -p
# conan 化后：conan create archives/w/wxsvg/1.5.25 --build=missing
# （配方 generate() 注入全部环境细节，见下表）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS（uname -s = HarmonyOS） | 上游 autoconf 归档陈旧 | 补丁 0001：`*:HarmonyOS:*` 分支 → aarch64-unknown-linux-ohos（libarchive 同款） |
| 2 | configure/config.status 建临时目录后写文件 EACCES | HMDFS：`umask 077` 建目录产生不可写目录（E533） | 补丁 0001/0003：两处 `umask 077`→`002` |
| 3 | `./configure: /bin/sh: bad interpreter: Permission denied` | 设备会话窗内脚本 shebang exec 被系统性拒绝（二进制 exec 不受影响） | 配方 build() 先探测（shebang probe），失败则把 configure 换成 ELF 启动器（execv hnp bash 直调 configure.real，Autotools.configure() 命令行不变）；wx-config 同样编译为 ELF 二进制包装 |
| 4 | 链接报 undefined symbol: g_libintl_* | 发布的 glib 包内 libglib-2.0.so.0 引用 g_libintl_*（其私有代理 libintl.so 提供 gettext→g_libintl_* 桥），.pc 不传递 | LIBS 追加 `-lintl`（aris/2.2 同款），且把全图依赖 lib 目录前置 LDFLAGS 保证选中 glib 目录下的桥 |
| 5 | 消费方链接报 undefined symbol: ffi_* / pcre2_* | libffi/pcre2 为 glib 的静态传递依赖，既不被 glib 系 .pc 传递，也不出现在 `self.dependencies.host`（配方不可见）；全静态链接 wx（如上游 svgview 演示程序）时须自行补链 | 库本体实测不需要：产物 `libwxsvg.so.3.12.8` 的 `llvm-nm -D --undefined-only` 中 ffi_*/pcre2_* 计数为 0。consumer（test_package）在链接行尾自补 `-lffi -lpcre2-8` 并显式声明这两个包取 lib 目录；注意【不可】把它们声明为本包 requires：一旦进入依赖图，AutotoolsDeps 会把 pcre2 组件（pcre2-posix 等）聚进 LIBS，libtool 对 -lpcre2-8 做 .la 展开得到空前缀路径 `//lib/libpcre2-8.la` 直接断链 |
| 6 | PKG_CHECK_MODULES(libavformat>=50.0.0...) 失败（version of libavformat is 8.1.2） | 发布的 ffmpeg .pc 的 Version=包版本 8.1.2，而上游 ffmpeg .pc 用库版本号（62.x），wxsvg 按库版本语义检查 | `LIBAV_CFLAGS/LIBAV_LIBS` 环境旁路（configure 文档化逃生口） |
| 7 | config.status: am--depfiles 引导挂（exec install-sh 直接失败） | 生成 Makefile 的 MKDIR_P 直接 exec install-sh 脚本 → 问题 3 | `--disable-dependency-tracking`；`make install` 以 `MKDIR_P='/bin/mkdir -p'` 变量覆盖（值含空格须整体引号包裹——conan install() 按空白 join，不裹引号时 "-p" 会被 make 当 --print-data-base 选项） |
| 8 | 本机 conan 缓存部分包的 .so 别名为旧会话 dangling 符号链接（lstat EACCES） | 共享 runner 多会话写缓存 + 本会话 symlink 操作被沙箱拒绝 | W3 用全新 CONAN_HOME 重新拉取（新提取的包别名均为实体文件）；不改配方（CI 缓存健康） |
| 9 | configure 编译器健全性检查"cannot run C compiled programs" | 检查以全量 LDFLAGS+LIBS 链接并【运行】conftest，设备加载器需全部依赖 lib 目录；且设备级 `-L/usr/local/lib`（hnp clang sysroot 注入）会选中其他会话装进共享区的同名坏库（无桥 libintl.so、静态 libgio-2.0.a） | 配方 generate() 把全部 host 依赖 libdir 前置 LD_LIBRARY_PATH（conftest 运行）与 LDFLAGS（取包目录优先） |
| 10 | expat/libexif/cairo/pango/wx 版本对齐 | gtk 树把 expat 统一到 2.8.2.1；ffmpeg 发布配方 pin harfbuzz/14.2.0 而 gtk 树 pin 14.2.0.1.1.1 | requires: expat/2.8.2.1；harfbuzz/14.2.0.1.1.1 override=True（单图单版本） |
| 11 | wxwin.m4 找不到 wx-config（`checking for wxWidgets version... no`） | WX_CONFIG_CHECK 用裸名 "wx-config" 在 cwd 做 test -x（恰好命中包装器），执行却按 PATH 搜索（m4 假定传入绝对路径） | 配方把包装器所在 build 目录前置 PATH（同时保留 WX_CONFIG_PATH 预设，两条路径都通） |
| 12 | make jobserver: `mkfifo: Operation not permitted` | HMDFS 不支持 fifo；conan 默认给 install 加 -j{nproc} | `make install` 附 `-j1`（无并行损失，日志干净） |
| 13 | **CI（远端 worker）**：`checking whether the C compiler works... no` → `C compiler cannot create executables` / `cannot run C compiled programs`（本地 W3 曾全过） | 知识库 **E505** 双层根因：(a) 配方 `generate()` 曾把全部依赖 lib 目录导出为**全局 LD_LIBRARY_PATH**（forbid_2），会被 clang→lld 子进程继承，SDK 的 lld 自身依赖 libxml2，被 Conan 版抢占即崩；(b) 更本质的是 **OHOS musl 一旦发现 LD_LIBRARY_PATH 非空就取代 DT_RPATH**（profile 的 buildenv 本就注入 SDK llvm lib 路径，故恒非空）→ 依赖解析回落到设备默认路径，命中**同名不同符号**的 `/storage/Users/currentUser/usr/local/lib/libintl.so.8`（标准 gettext，无 `g_libintl_*` 桥；桥只在 glib 包私有代理里）→ conftest 运行期 `g_libintl_*: symbol not found`（rc=127）。本机与 worker 的设备前缀内容不同，故本地侥幸不复现 | 按 E505 推荐方案 **materialised-signed-runtime-view** + 清空变量：①`generate()` 内 `env.unset("LD_LIBRARY_PATH")`，让 DT_RPATH 真正生效（实测 clang/lld/llvm-objcopy/patchelf/binary-sign-tool 均不依赖该变量）；②`_runtime_view()` 把依赖 libdir 中符号链接形式的版本化别名解引用实体化；③构建期只用 `-Wl,--disable-new-dtags -Wl,-rpath,<view+libdirs>`；④`package()` 用 patchelf 把产物 rpath 归一为 `$ORIGIN`；⑤test_package 亦内嵌 rpath（不依赖 conanrun 的 LD_LIBRARY_PATH） |

## 源码修改（3 补丁，均在 conandata.yml 注册）
- 0001-config.guess.patch：config.guess 加 `*:HarmonyOS:*` 分支 + set_cc_for_build 三处 `umask 077`→`002`
- 0002-config.sub.patch：config.sub 两处 OS 列表追加 `| ohos*` / `| linux-ohos*`
- 0003-configure.patch：configure 内两处 `umask 077`→`002`（config.status 临时目录）

## 依赖版本（与 manifest.yaml 一致）
wxwidgets-gtk3/3.2.10（静态 PIC，wx-config 消费）、expat/2.8.2.1、libexif/0.6.26.1、
cairo/1.18.4、pango/1.50.14.1.1、ffmpeg/8.1.2（harfbuzz/14.2.0.1.1.1 override=True）；
harfbuzz/14.2.0.1.1.1 以 override=True 统一（ffmpeg 发布配方 pin 14.2.0、
gtk 树 pin 14.2.0.1.1.1，单图不允许双版本，无 ABI 差异）。
glib 的静态传递依赖 libffi/3.4.4 + pcre2/10.45 不入依赖表（见问题 5）：
库本体不需要（产物 0 个 ffi_*/pcre2_* 未定义符号），consumer 侧由
test_package 自行声明取目录并按需补链。

## 验证结果

```bash
# 探索构建（.work，DESTDIR 安装后直跑）：
# $ svgview → "Unable to initialize GTK+, is DISPLAY set properly?"（GUI 程序无显示环境
#   的预期行为——完整共享链加载成功，wx 静态全链链接成功）
# 冒烟测试 test_package.cpp（9 断言全过）：
PASS: SVG document loads (XML/expat path)
PASS: root <svg> element present
PASS: <title> parsed via DOM
PASS: GetElementById finds the rect
PASS: element id round-trips
PASS: Render produces a valid wxImage
PASS: rendered image is 32x32
PASS: rect center pixel is red (cairo rasterized)
PASS: background pixel stays white
# make check：上游无测试（tarball 无 tests/，"Nothing to be done for 'check-am'"）
```

```bash
# E505 运行期定位验证（不再依赖 LD_LIBRARY_PATH）：
readelf -d <pkg>/lib/libwxsvg.so.3.12.8 | grep -E 'RPATH|RUNPATH'   # → RPATH $ORIGIN
env -u LD_LIBRARY_PATH ./test_wxsvg                                 # → 9/9 PASS
```

## R51 测试清点
上游 0 个测试；test_package 9 断言补位（见 test_package/MANIFEST.yml）。
---

**编译结束**: 2026-10-13 21:06
**最终状态**: published
