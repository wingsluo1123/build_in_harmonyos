# clutter 1.26.4 适配笔记（本地实测）

## 编译环境
- 构建系统: autotools（tarball 自带 `configure`/`Makefile.in`，无需 autoreconf）
- 编译日期: 2026-10-01（2026-09-29 初版 + 2026-10-01 收尾）
- 编译器: clang 15 / libc++（OHOS aarch64 原生，非交叉）
- 状态: built（`conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2` EXIT=0，test_package ALL PASS）
- 包引用: `clutter/1.26.4`（package_id b3df52abe85ba74efd753afb8080e647e7d3f32d）

## 目标版本核实（重要）

曾按 `feat/clutter-1.27.4` 起分支，但**上游不存在 1.27 系列**。逐项核实：

| 核实手段 | 结果 |
|---|---|
| GNOME 官方 `download.gnome.org/sources/clutter/cache.json` | 最高 `1.26.4`，`1.27` 出现 0 次 |
| GNOME 官方 `1.27/`、`1.28/` 目录 | 均 HTTP 404 |
| GNOME Archive/clutter GitLab tags（全分页） | 最高稳定 tag `1.26.4`（2020-03-09） |
| 上游 master 的 `configure.ac` / `meson.build` | `1.26.5`（奇数微号=开发中，**无正式发布**） |
| Debian/Alpine/Fedora/openSUSE/Guix/openEuler | 最高均 `1.26.4` |
| `www.clutter.org/clutter-1.27.4.tar.gz` | **假阳性**：随机文件名同样 302→200（停靠页）；`clutter.org` 无源码分发能力 |

经确认按真实上游最新稳定版 **1.26.4** 适配，分支 `feat/clutter-1.26.4`。
源码 sha256 = `8b48fac159843f556d0a6be3dbfc6b083fc6d9c58a20a49a6b4919ab4263c4e6`
（与官方 `clutter-1.26.4.sha256sum` 一致）。

## 编译步骤

1. `conan create . -pr:h=<ohos-aarch64 profile> --build=missing -c tools.build:jobs=2`
2. 配方 `generate()`：PkgConfigDeps；`build()` 内手写重写版 .pc（cogl/cogl-path/
   cogl-pango/cairo-gobject/json-glib/atk）一并落 generators_folder（优先级最高）。
3. `build()`：
   - 编译 cogl-pango stub .o（cogl 包缺组件）；cairo 包二进制缺 cairo-gobject
     组件时编译 cairo-gobject stub .o；
   - patch configure：confstat `umask 077`→`umask 000`（HMDFS 0700 临时目录不可写）；
   - touch autotools 文件防重生成（**固定递增时间戳分四层**：configure.ac+*.am+*.m4 <
     aclocal.m4 < Makefile.in+config.h.in < configure——乱序或亚秒级同刻 touch 会让
     某文件显 stale，实测两种形态：aclocal.m4 stale→aclocal-1.16 Error 127；
     Makefile.in stale→automake Error 1）；
   - `./configure --prefix=<pkg>`：仅 `--enable-egl-backend`，x11/gdk/wayland/quartz/
     win32/mir/cex100/evdev/tslib 全禁 + `--disable-glibtest`（glib 运行时测试程序
     在 HMDFS 上跑不起来，cogl 同款）+ `--disable-gtk-doc --disable-introspection
     --disable-docs --disable-examples --disable-gdk-pixbuf --disable-Bsymbolic`；
   - 顶层 Makefile SUBDIRS 摘除 `tests doc po`（conform 链接需 GL 渲染环境且缺
     test_utils_* 符号；上游测试实跑改由 test_package 对安装包进行）；
   - `make -j1`（HMDFS 不支持 jobserver mkfifo）。
4. `package()`：`make install` 拷产物 + 核心产物校验（lib/libclutter-1.0.so、
   include/clutter-1.0/clutter/clutter.h、lib/pkgconfig/{clutter-1.0,cally-1.0,
   clutter-cogl-1.0,clutter-egl-1.0}.pc 缺一即 Exception）。
5. `test()`：复用 test_package/test_clutter.py 对 self.package_folder 实跑
   （recipe_folder 下有脚本时执行，conan 缓存导出上下文优雅降级——create 的
   test_package 阶段执行同 17 用例）。

## 上游测试清点与实跑（R51 三步法）

### 第 1 步：清点（逐文件实测，非估算）

| 目录 | 注册方式 | 用例数 |
|------|----------|--------|
| tests/conform | 26 个 test_programs 内 `CLUTTER_TEST_UNIT` 注册（逐文件 grep 计数） | **83** |
| tests/interactive | check_PROGRAMS（交互式演示，非测试） | — |
| tests/accessibility | check_PROGRAMS（示例） | — |
| tests/micro-bench / performance | 基准演示 | — |

### 第 2 步：可运行环境实际运行

**83 个 conform 注册单元中 17 个纯 CPU 用例实跑通过**（color 5 / units 3 /
interval 3 / model 5 / binding-pool 1），由 test_package 编译运行（上游
CLUTTER_TEST_SUITE 展开的 main 经 clutter_test_init→clutter_init 需 EGL 显示
服务不可行——改为顺序调用注册的测试函数，script 用例的 g_test_build_filename
改相对路径，scripts/ 数据随包提供）。

其余 **66 例省略**（0 运行，非失败），技术原因：所有用例入口经
`clutter_init()` 建立 EGL/GL 渲染上下文，OHOS 本环境无显示服务（无
X11/Wayland/DRM、无 /dev/dri），`cogl_context_new(NULL)` 实测 SIGSEGV
（cogl/1.22.8 先例）——**环境限制**：OHOS 无显示服务。与 cogl/1.22.8 口径
一致（72 例中仅 3 例纯 CPU 可跑）。

### 第 3 步：消费者视角实跑（test_package）

`test_clutter.py` 对安装包产物实跑：lib/头存在性 + consumer.c（版本契约/
颜色解析/units 换算/actor 基础/interval/binding-pool 纯 CPU 冒烟，链接
-lclutter-1.0 且运行 rc=0）+ 上述上游 17 用例逐用例 PASS 断言。
本机全绿输出：
`PASS [upstream] color/units/interval/model/binding-pool 全过（17/17），ALL PASS`。

## 构建问题实录（七轮迭代）

| # | 症状 | 根因 | 修复 |
|---|------|------|------|
| 1 | stub 编译 `pkg-config: No package 'glib-2.0' found` → `glib-object.h not found` | `env PKG_CONFIG_PATH=x clang ... \`pkg-config ...\``：shell 先做反引号命令替换再执行 env 前缀——替换子 shell 看不到 env 前缀设的变量 | 改 `export PKG_CONFIG_PATH=x; clang ... \`pkg-config ...\`` |
| 2 | configure：`No package 'cairo-gobject' found` | 图内解析的 cairo/1.18.4 二进制不含 cairo-gobject 组件（无 .so 无 .pc），clutter 硬依赖 >=1.14 | stub 实现源（上游 CAIRO_GOBJECT_BOILERPLATE 逐行等价，libclutter 实际未解析符号仅 context/surface_get_type 两枚）+ stub 转发 pc（Libs 带 .o） |
| 3 | `make: aclocal-1.16: error: autom4te failed (127)` → Error 2 | 触发 aclocal.m4 重生成（本机无 aclocal-1.16 链）：touch 顺序乱致 configure.ac mtime 晚于 aclocal.m4 27μs | 固定递增时间戳分四层 touch（见上） |
| 4 | `automake-1.16: error: autoconf failed (127)` → Makefile.in Error 1 | 同根因换形态：Makefile.in 层 mtime 早于 aclocal.m4 层，判 stale 触发 automake 重生成 | 同上（四层：源层<aclocal.m4<Makefile.in/config.h.in<configure） |
| 5 | test 阶段 `fatal error: 'cogl/cogl.h' not found`（consumer/upstream 全挂） | cogl 包头安装布局 `include/cogl/cogl/*.h` 需 `-I<pkg>/include/cogl`，依赖收集只收顶层 includedirs | 依赖头子目录补齐清单加 ("cogl", ("cogl",))（conanfile 与 test_package 同步） |
| 6 | CI #66493：`clutter-canvas.c:50: fatal error: 'cairo-gobject.h' file not found`（本机过、CI 挂） | 同 package_id 不同 rev 的 cairo 包内容差异：本机缓存包带头，worker 的不带（stub pc 旧 Cflags 指向 cairo include 目录→头不存在） | stub 头 `cairo-gobject.h` 随配方 exports_sources（上游原样两宏+两声明，clutter 全源码仅用 CAIRO_GOBJECT_TYPE_CONTEXT/SURFACE 两宏）；stub pc Cflags 改指 src 根；pc 转发条件加"pc+头双存在"防中间态 |
| 7 | CI #66619：链接期 `libtool: error '.../p/b/cogl54618945e9137/p/lib/libcogl.la' is not a valid libtool archive`（本机过、CI 挂） | cogl 包 .la 烘焙原构建机 conan home 路径（cogl54618945e9137 构建文件夹 ID），CI 上 grep/sed 读该路径报 No such file——正则修补只覆盖 -L/libdir 形态不够；本机缓存 .la 被早前轮次就地修补"碰巧"通过，CI 全新环境必暴露 | 全量重建三个 cogl .la 为最小合法 .la：dlname/library_names 按包内真实 .so 文件名构造（不猜版本号）、dependency_libs 置空（消除全部烘焙路径）、libdir 指向当前解析的 cogl package_folder——本机/CI 确定性一致 |

其余先例问题（.pc/.la prefix 固化、cogl-pango 缺组件、json-glib dlopen 签名）
沿用 cogl/1.22.8 与本配方既有方案，不再重复。

## 平台限制说明（如实记录）

- **无显示服务 / 无 `/dev/dri`**：Clutter 作为图形 UI 框架，渲染路径的端到端
  验证需在有显示能力的设备上另行进行。本配方交付的是**可编译、可链接、可加载、
  免显示 API 可实跑（17 用例）**的库产物。
- 本配方未引入任何 `__OHOS__` 平台宏（PF5 合规），平台适配全部经 configure
  开关裁剪与配方内等价修正完成。
- 产物不入库（.la 为构建期中间产物随包保留原样；主交付 .so + 头 + .pc）。

## 依赖版本

cogl/1.22.8 + glib/2.84.0.1 + pango/1.50.14 + cairo/1.18.4 + atk/2.38.0.1.1 +
json-glib/1.10.6（>=0.12 即满足，选 1.10.6 避开 1.6.6 绑定 glib/2.84.0 与图内
2.84.0.1 冲突）。EGL 头由系统默认路径解析（clang sysroot），libclutter NEEDED
无 libEGL——EGL 经 cogl 封装，无需直连 egl/gles2 包。

## 版本号递增说明（2026-10-17）
制品仓已存在 clutter/1.26.4（他人简化版，L0g 门禁：同版本异内容 409 Conflict），本增强版按门禁 hint 递增版本号为 **1.26.4.1**；上游源码仍为 clutter-1.26.4.tar.xz（sha256 不变）。
