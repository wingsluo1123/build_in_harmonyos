# maqview 0.2.5 适配笔记

- **平台任务**：8690（分支 `feat/maqview-0.2.5`）
- **构建系统**：autotools（configure.ac + Makefile.am；tarball 不含生成的 configure）
- **目标**：OHOS / armv8 / clang 15（`ci/conan/profiles/ohos-aarch64`，build=host 原生编译）
- **状态**：built（conan create + L0/L1/L2/L4/L5 见 CI 报告）

## 1. 上游与源码核验

maqview 0.2.5 无 GitHub/GitLab release，上游发布页是 SourceForge
（`https://maq.sourceforge.net/maqview.shtml`），无稳定直链归档。故采用
**Debian 主池的 orig 源包**：

- URL：`https://deb.debian.org/debian/pool/main/m/maqview/maqview_0.2.5.orig.tar.gz`
- sha256：`2d01495bb03fe108d87a348432bdc9c81e93c6f765ccba8f88fc94a979a7eba2`（188,833 字节）
- 与同版本 `maqview_0.2.5-12.dsc` 的 `Checksums-Sha256` / `Checksums-Sha1` / `Files`
  逐字比对：sha256、md5（`050c8c3692b2bdd44bd794f872d2388b`）、size 三项一致。
  Debian `3.0 (quilt)` 格式的 orig 必须与上游逐字节一致，因此该文件即上游原始 tarball。
- 解包后 `configure.ac` 的 `AC_INIT(MAQVIEW, 0.2.5)` 与任务 version 逐字一致。

源码语言由 `lang-preflight` 判定为 C/C++（`.c` + `.cc`）。

## 2. 上游测试清点（N_upstream = 0）

| 项 | 结果 | 证据 |
|---|---|---|
| `Makefile.am` 的 `TESTS` | 无 | `grep -nE 'TESTS|check_PROGRAMS' Makefile.am` → 无输出 |
| `configure.ac` 测试脚手架 | 无 | 无 `AC_CONFIG_TESTDIR` 等 |
| `test_razf.c` | **孤儿**，非测试目标 | 不在任何 `_SOURCES`；`#include "razf.h"` 指向树中不存在的头（树里是 `zrio.h`）；本体是计时基准、无断言、恒 `return 0` |

结论：无 `make check` 可跑，N_upstream = 0。消费者验证全部由 `test_package/` 承担。

## 3. OHOS 适配要点

### 3.1 GL 栈：桌面 GL vs GLES

OHOS 只交付 OpenGL ES。实测 sysroot（`ohos-sdk_26.0.0.18`）与制品仓：

- `sysroot/usr/lib/aarch64-linux-ohos/`：只有 `libEGL.so`、`libGLESv2.so`、
  `libGLESv3.so`、`libGLv4.so`，**没有** `libGL.so` / `libglut.so` / `libGLU.so`。
- 逐个查符号：`libGLESv2.so` / `libGLESv3.so` / `libGLv4.so` 均**不导出**
  `glBegin` / `glVertex3f` / `glMatrixMode` / `glOrtho` / `glLoadIdentity` /
  `glPushMatrix` / `glRenderMode` / `glSelectBuffer` / `glPushName`。

而 maqview 的渲染层通篇是桌面 GL 立即模式 + 选择模式拾取：

- `gl_gui.c:77-90` `glBegin(GL_LINE_LOOP)` / `glVertex3f` / `glBegin(GL_LINES)`
- `gl_gui.c:120-124` `glMatrixMode` / `glLoadIdentity` / `glOrtho`
- `MainFrame.c:80-84`、`view_panel.c:260-273` 同上
- `MainFrame.c:5` / `view_goto.c:10` `#include <GL/glu.h>`（`gluPickMatrix` 用于拾取）

因此配方链接制品仓的 **`mesa/24.3.4.1`**：其 `lib/libOSMesa.so` + `lib/libglapi.so`
实测联合导出上述**全部**入口（`llvm-nm -D` 逐个确认，脚本化核对无 MISSING），
并随包交付桌面 `include/GL/gl.h`。
`glu/9.0.3` 提供 `libGLU.so`（`gluPickMatrix`）；`freeglut/3.6.0` 提供 GLUT
（OHOS 制品为 GLES/EGL 版 `lib/libfreeglut-gles.so`，导出 `glutInit` /
`glutMouseWheelFunc` 等全部所需符号）。

**为什么是 `-lOSMesa -lglapi` 而不是 `-lGL`**：制品仓 `mesa/24.3.4.1` 的
`lib/` 目录只有 `libOSMesa.so`/`libglapi.so`，**没有独立 `libGL.so`**
（该版本的桌面 GL 入口就打包在 libOSMesa 里）。带 `libGL.so` 的
`mesa/24.3.4.1.1.1` 与 `glu/9.0.3` 的 pin 直接冲突——实测
`conan graph info` 报
`Version conflict: Conflict between mesa/24.3.4.1 and mesa/24.3.4.1.1.1 ...
Conflict originates from glu/9.0.3`。故 GLLIBS 用 `-lOSMesa -lglapi`。

**版本一致性**：`glu/9.0.3` 的配方自身 `self.requires("mesa/24.3.4.1")`，故三者
（mesa/24.3.4.1 + glu/9.0.3 + freeglut/3.6.0）版本一致，不存在 mesa 版本冲突。
（注：`mesa/26.1.5` 自上游 25.1.0 起已移除 OSMesa，只交付 EGL/GLES，
不提供桌面 GL 入口，不能用于本库。）

`libx11` **未**作为直接依赖：`grep` 全量源码无 `X11`/`Xlib`/`XOpenDisplay` 使用，
`configure.ac` 也不探测 X11（只探 `GL/glut.h`）。引入未使用的依赖属缺陷，故不列。

### 3.2 无 X display 的做法

构建只做**编译 + 链接**，不创建真实窗口；运行期验证走无头路线：

- `test_package/test_gl_headless.cpp`：用 mesa 的 OSMesa 离屏上下文
  （`OSMesaCreateContextExt` + `OSMesaMakeCurrent`）在无 display 下跑 maqview
  同款固定管线入口，并对视口中心像素做具体数值断言。
- 直接执行打包出的 `bin/maqindex`（无参数 → `Usage`，退出码 1）与
  `bin/maqview`（无参数 → `glutInit` 后、创建窗口前 `return maqview_usage()`，
  退出码 1）。后者顺带验证 GLUT/GL 栈能真实**动态加载**（被禁止的是 loader 的
  缺库/缺符号报错）。实测本机当前会话下 freeglut 的 EGL 拿不到 display，
  `fg_init_egl.c` 的 `eglGetDisplay()` 返回 `EGL_NO_DISPLAY` → 打印
  `<No display available> in function fgPlatformInitialize` 后以 rc=1 退出；
  按「无 X 显示时仅链接/测试，不要求真窗口」口径这是允许结果，测试对两种分支
  都接受。

### 3.3 configure.ac 补丁（0001）

| 改动 | 原因 |
|---|---|
| `AM_CONFIG_HEADER(config.h)` → `AC_CONFIG_HEADERS([config.h])` | automake ≥ 1.13 已移除旧宏（只剩 obsolete 警告 shim），autoreconf 才能干净生成 |
| 取消 “任何 `--prefix` 即静态链接 libglut 并覆盖 `LDFLAGS`/`CPPFLAGS`” 分支 | conan 必传 `--prefix=<包目录>`，该分支会**清空** conan 注入的依赖 include/lib 路径，并请求 OHOS 上不存在的静态 `libglut`（`configure.ac` 顶部 `case ${prefix}` 块） |
| `AC_CHECK_LIB([glut], [glutMouseWheelFunc])` → `[freeglut-gles]` | OHOS freeglut 制品库名是 `libfreeglut-gles.so`，探测名必须对上，否则 `HAVE_FREEGLUT` 不定义，`view_panel.c:1777` 的 `glutMouseWheelFunc` 分支被跳过 |
| `GLLIBS="-lGL -lglut -lm"` → `"-lOSMesa -lglapi -lfreeglut-gles -lGLU -lm"` | 用 OHOS 实际库名（mesa/24.3.4.1 的桌面 GL 入口在 libOSMesa+libglapi，无独立 libGL）；补 `-lGLU`（`gluPickMatrix` 需要；上游只写 `-lglut`，依赖当时 libglut 传递依赖 libGLU） |

### 3.4 源码补丁（0002，clang 两阶段名字查找）

`stdhash.hh` 的 `hash_set_misc` / `hash_map_misc` 派生自模板基类
`__lh3_hash_base_class<keytype_t>`，派生类里对基类成员 `direct_insert_aux(...)`
的**非限定**调用在 clang 下报：

```
stdhash.hh:496:13: error: explicit qualification required to use member
'direct_insert_aux' from dependent base class
```

（GCC 容忍这种写法；`this->n_capacity` 等数据成员上游本来就加了 `this->`，
只有这 3 处方法调用漏了。）改为 `this->direct_insert_aux(...)`，语义不变：
`hash_set_misc::insert`（1 处）、`hash_map_misc::insert`（2 处）。

### 3.5 源码补丁（0003，OHOS freeglut 的 GLUT 字体标识）

链接 `maqview` 时报：

```
ld.lld: error: undefined symbol: glutBitmap8By13
ld.lld: error: undefined symbol: glutBitmap9By15
```

根因（对着 freeglut 3.6.0 上游源码确认）：

- `include/GL/freeglut_std.h` 的非 Windows 分支把字体宏定义成**指针的地址**：
  `GLUT_BITMAP_8_BY_13 ((void *) &glutBitmap8By13)`，并 `extern void* glutBitmap8By13;`。
- 这些全局量定义在 `src/x11/fg_glutfont_definitions_x11.c`，而 `CMakeLists.txt`
  只在 Wayland/X11 平台把它加进 `FREEGLUT_SRCS`；**HarmonyOS 分支不编译它**。
- 且 `CMakeLists.txt`：`IF(NOT FREEGLUT_GLES AND NOT OGC) … fg_font.c … ELSE …
  gles_stubs.c`。OHOS 是 `FREEGLUT_GLES` 构建 ⇒ 用 `src/gles_stubs.c`，
  其中 `void glutBitmapCharacter(void* font, int character) {}` 是**空实现**
  （忽略 `font`），`glutStrokeCharacter` 同理。
- 实测 `readelf --dyn-syms libfreeglut-gles.so`：只有 `glutBitmap*` 函数，
  **没有任何 `glutBitmap8By13`/`glutBitmap9By15` 对象符号**。

修法：maqview 三处使用（`view_goto.c:46,47`、`view_panel.c:333`；
`view_panel.c:353` 的 `glutStrokeCharacter` 在注释块内不参与编译）改用
freeglut 头文件**Windows 分支同款**的 GLUT 数字字体 ID
（`8_BY_13 = (void*)0x0003`、`9_BY_15 = (void*)0x0002`，与 GLUT 二进制兼容）。
在该构建下 `glutBitmapCharacter()` 本就忽略 `font`，指针形式与数字 ID 语义等价。

### 3.6 autotools 落地

- tarball 只有 `configure.ac`，构建前在源目录 `autoreconf -fi`
  （tool_requires 只有 `automake/1.18`；autoconf 2.72 / m4 / perl 取设备 hnp
  工具链——原因见下条；`AUTOPOINT=true` 跳过 autopoint 版本检查）。
- `--build/--host=aarch64-unknown-linux-gnu`：设备 `config.sub` 不保证认识
  `ohos`，该三元组被普遍接受且 `host_os` 解析为 `linux`，命中上游 linux 分支。
  （设备 `clang -dumpmachine` 已默认 `aarch64-unknown-linux-ohos`，无需 `--target`/`--sysroot`。）
- 生成的 `configure` 里 `umask 077` 在 hmdfs 上造出 mode 2700 的临时目录，
  而 hmdfs 按组位判定遍历权限、`chmod` 又是 no-op → EACCES；改回 `022`。
- GL 头/库路径显式传入：`AC_CHECK_HEADER(GL/glut.h)` 只看 `CPPFLAGS`，
  `AC_CHECK_LIB` 只看 `LDFLAGS`，故二者都显式给（`-I<dep>/include`、`-L<dep>/lib`）。
- 就地（in-source）构建，避开 VPATH 组合风险；`--prefix=<package_folder>`
  直接装进包目录。
- **perl 版本必须统一（本库最大的一处坑）**：automake / autoconf 都是 perl
  脚本，而设备上存在两个 perl：

  | 来源 | 版本 | 谁在用 |
  |---|---|---|
  | 设备 hnp 工具链 `/data/service/hnp/bin/perl` | 5.42.0 | conan automake 制品脚本的 shebang（`/data/service/hnp/bin/perl`）、系统 autoconf |
  | conan `perl/5.42.2` 制品 | 5.42.2 | conan `autoconf/2.72` 制品脚本的 shebang |

  两者 XS 模块 ABI 不兼容。实测：
  - 让 conan perl 的 lib 目录进 `PERL5LIB` → 系统 perl 加载 5.42.2 的 `Cwd.so`
    报 `Error relocating ...: Perl_my_cxt_init: symbol not found`（aclocal 255 退出）；
  - 反过来只给 automake 的模块目录 → conan 的 `autoreconf`（跑在 conan perl 下）
    报 `Can't locate strict.pm in @INC`（conan perl 的内置 `@INC` 被装成
    `//lib/perl5/5.42.2`，指向不存在的位置）。

  结论：**不能同时用 conan autoconf 与 conan automake**。本配方只用制品仓的
  `automake/1.18`，autoconf/autoheader/autoreconf/m4/perl 全部取设备 hnp 工具链
  （与 clang/make/bash 同源），并把 `PATH` 显式前置为
  `<conan automake bin>:<设备 hnp bin>:$PATH`（设备目录必须排在 conan perl
  tool_require 的 bin 之前）；`PERL5LIB` 只放
  `<conan automake>/share/automake-1.18`（`Automake::Config` 等模块），
  `ACLOCAL_PATH` 放 `<conan automake>/share/aclocal`。

### 3.7 签名

`os == "OHOS"` 时对打包出的每个实体 ELF（`bin/` 下 4 个可执行文件）：
先 `llvm-objcopy --remove-section .codesign` 清掉安装改写 RUNPATH 后失效的旧段，
再 `binary-sign-tool sign -selfSign 1`，`os.chmod` 恢复 0755，随后
`readelf -SW` 断言**恰好 1 个** `.codesign` 段，fail-closed（缺工具/无 ELF 直接报错）。

## 4. 构建产物

`bin/` 下四个可执行文件（`Makefile.am` 的 `bin_PROGRAMS`）：
`maqview`、`maqindex`、`zrio`、`maqindex_socks`。

## 5. 已知限制

- 真实 GUI 渲染（窗口、事件循环、选择模式拾取）需要窗口系统，OHOS 无 X/Wayland，
  未做真机窗口验证；本包保证**编译、链接、加载**与无头 GL 渲染路径可用。
- `maqview` 链接的 freeglut 是 OHOS 的 GLES/EGL 版（`libfreeglut-gles.so`），
  与桌面 GL（libGL/libOSMesa）属不同后端；`maqview` 实际出图能力取决于运行期
  GL 后端，本次交付按“无 X 显示仅链接/测试”口径验证。
- 上游二进制内置版本串仍打印 `MaqView 0.2.4`（`MainFrame.c:178` 硬编码），
  与包版本 0.2.5 不一致，属上游遗留，未改源码。
- OHOS 的 freeglut 是 `FREEGLUT_GLES` 构建，位图/矢量字体 API 来自
  `src/gles_stubs.c`，**本身就不渲染**（freeglut 适配笔记已声明）；maqview 侧
  使用 GLUT 数字字体 ID 仅保证链接与调用不崩，文字仍不会出现在画面上。
  freeglut 包缺导出 `glutBitmap8By13`/`glutBitmap9By15` 等全局量是个后续可修项
  （应在其 OHOS 平台层补一份字体标识定义），但不在本任务范围。
