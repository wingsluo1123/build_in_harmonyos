# quesoglc 0.7.2 — 适配记录

QuesoGLC 是 OpenGL Character Renderer (GLC) 的自由实现：为 OpenGL 应用提供
Unicode 文字渲染，用 FreeType 光栅化字形、用 Fontconfig 解析字体族与目录，
再用 GL/GLU 画出几何。上游是纯 C + autotools 工程，发布 tarball 自带
预生成的 `configure`，配方直接驱动该 configure，不重新生成。

## 任务与产物

- 平台任务 9926（`changeType=feat`），分支 `feat/quesoglc-0.7.2`
- 源码：`https://downloads.sourceforge.net/project/quesoglc/0.7.2/quesoglc-0.7.2-free.tar.gz`
  sha256 `fa47582cac5a0ac98d24b462d0cdba8d0c7a2f0aded6220b05d907b598f06571`
  （`-free` 是上游的 LGPL-only 包；经实测与 Debian `quesoglc_0.7.2.orig.tar.gz` 逐字节相同）
- 产物：`lib/libGLC.so.0.0.7`（+ `libGLC.a`）、`include/GL/glc.h`、
  `lib/pkgconfig/quesoglc.pc`
- **纯库包**（无 `bin_PROGRAMS`，tests/examples 全为 `noinst_PROGRAMS`）→ 按 R38/PF8
  **不提供 `commands.json`**（PF8「纯库误加」是 fail-closed）。

## 关键适配点

### 1. OHOS 无桌面 GL → 用 Mesa OSMesa

OHOS 只有 EGL + GLES2/GLES3，没有 `libGL.so` / `GL/glx.h`。QuesoGLC 自身源码
`grep -rn 'glX\|GL/glx.h\|XOpenDisplay' src/ include/` 命中 **0**（唯一命中在
上游自带的第三方 `src/glew.c` 内），即它只需要「一份桌面 OpenGL 实现」。用
`mesa/24.3.4.1` 的 `libOSMesa.so` + `include/GL/gl.h`（离屏软件渲染，不需要
X11/Wayland）——与仓库 `glu/9.0.3` 同一条路线。

`configure` 的 `AX_CHECK_GL` / `AX_CHECK_GLU` 只探测 `-lopengl32/-lGL` 与
`-lglu32/-lGLU`，OHOS 上都不存在。**不修改生成的 `configure`**，改为向 autoconf
cache 播种（configure 命令行 `VAR=VALUE` 即 cache 变量）：

```
ax_cv_check_gl_libgl=-lOSMesa
ax_cv_check_glu_libglu=-lGLU
```

include 路径由 `AutotoolsDeps` 提供（mesa → `GL/gl.h`，glu → `GL/glu.h`）。

### 2. GLEW 必须用「内嵌」而不是外部包

`configure.in` 里 `--with-glew=no` 的语义不是「不要 GLEW」，而是：

```
if (test "x$no_glew" = "xyes"); then
  GLEW_CFLAGS="-DGLEW_MX"
  GLEW_OBJ="libGLC_la-glew.lo"     # 编译上游自带的 src/glew.c
else
  PKGCONFIG_LIBS_PRIVATE="-lGLEW ..."   # 链外部 GLEW
fi
```

QuesoGLC 全库按 GLEW **多上下文** API（`GLEW_MX`）编写：`src/ocontext.h` 里有
`GLEWContext glewContext;`，`src/misc.c` 定义 `glewGetContext()`，`src/global.c`
调用 `glewInit()`（在 `GLEW_MX` 下展开为 `glewContextInit(glewGetContext())`）。
ohpcd 上的 `glew/2.3.1` 是用 `-DGLEW_EGL` 构建、**没有** `GLEW_MX` 的版本，无法满足。
因此必须走内嵌分支（`--with-glew=no`），由 configure 自动加 `-DGLEW_MX`。

### 3. 内嵌 GLEW 的 GLX 段需要 X11 → 补丁 0003

`src/glew.c`（上游自带）在非 `_WIN32` 平台会 `#include <GL/glxew.h>`，而
`include/GL/glxew.h` 无条件包含 `<X11/Xlib.h>`、`<X11/Xutil.h>`、`<X11/Xmd.h>`
——OHOS 没有任何 X11 头（实测 sysroot 无；只有 harmonybrew 前缀下有，不能引用）。
补丁 `0003-src-glew.c.patch` 做两件事，都用**平台中立**的 `GLEW_NO_GLX` 开关
（上游 GLEW 2.x 后来为「构建无 GLX 的 GLEW」引入的正是这个宏，仓库 `glew/2.2.0`
适配也明确「无 X11 系统应使用 EGL 版本」）：

1. 把 5 处 GLX 守卫改为
   `(!defined(__APPLE__) && !defined(GLEW_NO_GLX)) || defined(GLEW_APPLE_GLX)`；
2. 让 GL 入口解析改走 dlfcn：`dlGetProcAddress` 与 `glewGetProcAddress` 的
   `__sgi/__sun` 分支条件加 `|| defined(GLEW_NO_GLX)`（否则
   `glXGetProcAddressARB` 未声明，20 个编译错误——实测第二轮）。

配方**仅在 OHOS 上**定义 `-DGLEW_NO_GLX`（`AutotoolsToolchain.extra_cflags`），
其他平台行为完全不变。GLX 代码在 OHOS 运行期从不被引用。

### 4. 上游构建系统不支持 VPATH → 就地（in-source）构建

quesoglc 的生成 Makefile 把**源码头目录**写成了 `$(top_builddir)`：

```
DEFAULT_INCLUDES  = -I. -I$(srcdir) -I$(top_builddir)/include
libGLC_la_CFLAGS  = -I$(top_builddir)/src ...
```

in-source 构建时 top_builddir == top_srcdir 才成立；VPATH（外树）构建下这两个
`-I` 指向构建树里并不存在的目录，`#include "internal.h"`（实为
`include/internal.h`）直接找不到（实测第二轮：`'internal.h' file not found`）。
修法采用仓库既有写法（`archives/a/aconf/0.8.1` 等）：`layout()` 里
`self.folders.build = "."`，在源码目录就地构建，**不改生成文件**（R6）。

### 5. 依赖菱形冲突：expat

- `mesa/24.3.4.1` → `expat/2.8.2.1.1`
- `fontconfig/2.18.1.1` → `expat/2.8.2.1`

两者不可互换：`expat/2.8.2.1.1` 的包只交付 `libexpat.so`（实测 SONAME 也是
`libexpat.so`），而 fontconfig 的 `DT_NEEDED` 要的是 `libexpat.so.1`——第一轮用
2.8.2.1.1 统一时，configure 的 conftest 直接
`Error loading shared library libexpat.so.1` 而失败。`expat/2.8.2.1` 的包带
`libexpat.so → libexpat.so.1 → libexpat.so.1.12.2`。故 override 统一到
**fontconfig 一侧的 `expat/2.8.2.1`**；`libOSMesa.so.8` 的 `DT_NEEDED`
实测不含 expat，不受影响。

## 依赖清单（全部来自 ohpcd，OHOS/armv8 预编译包）

| 包 | 版本 | 作用 |
|---|---|---|
| freetype | 2.14.3 | 字形光栅化（configure 必需） |
| fontconfig | 2.18.1.1 | 字体族/目录解析（configure 必需） |
| mesa | 24.3.4.1 | 提供 `libOSMesa.so` + `GL/gl.h`（GL 实现） |
| glu | 9.0.3 | 提供 `libGLU.so` + `GL/glu.h`（并要求 mesa/24.3.4.1） |
| expat | 2.8.2.1 | fontconfig 的 XML 解析（override 统一菱形） |

fribidi 为可选：`--without-fribidi` 使用上游自带的内嵌副本。

## 上游测试清点与实测（R51）

- `tests/` 目录 1 个；`test*.c` 源文件 21 个（test1..test17 + testcontex/testfont/
  testmaster/testrender）。
- `tests/Makefile.am`：`TESTS = $(noinst_PROGRAMS)`，
  `noinst_PROGRAMS = test4 @DEBUG_TESTS@ @TESTS_WITH_GLUT@`。
  `DEBUG_TESTS` 仅 `--enable-debug` 时非空；`TESTS_WITH_GLUT` 仅找到 GLUT 时非空。
  OHOS 无 (free)GLUT：configure 走 `AC_MSG_WARN`，`EXECUTABLES="tests"`，
  `TESTS_WITH_GLUT` 为空 → **`make check` 只构建并运行 test4**，其余 20 个测试源
  依赖 GLUT + 显示器，本平台无法构建（具体技术原因：无 GLUT 库、无显示服务）。

| 项 | 值 |
|---|---|
| 上游注册测试 N | 1（test4） |
| 实际运行 N′ | 1 |
| 通过 | **1 / 1（100%）** |
| 未运行 | 20（GLUT + 显示器依赖，本平台未构建） |

本平台实际执行的上游测试集合满足 `TOTAL = PASS + FAIL + SKIP + NOT_RUN`
= `1 = 1 + 0 + 0 + 0`（其余 20 个测试源因缺 GLUT/显示服务未构建，不计入运行集合）。

**test4 原本无法执行的原因（平台能力边界，非本构建缺陷）**：test4 断言「无当前 GLC
上下文时非 global 命令报 `GLC_STATE_ERROR`」，但它是通过 `glcAppendCatalog("/")`
走到那一步的；库在状态检查**之前**先用 `access("/", R_OK)` 校验目录。OHOS 把进程
放进受限域后，根目录/系统目录对 `access()` 与 `opendir()` 都返回 EACCES（`stat()`
成功）。设备侧最小复现（本任务私有探针，见回执）：

| 路径 | access(R_OK) | opendir() | stat() |
|---|---|---|---|
| `/` | -1 (EACCES 13) | FAIL errno=13 | 0 (isdir) |
| `/usr` | -1 (EACCES 13) | FAIL errno=13 | 0 (isdir) |
| `/system` | -1 (EACCES 13) | FAIL errno=13 | 0 (isdir) |
| `$HOME` | 0 | OK | 0 (isdir) |

即 `access("/", R_OK)` 在该域内**确实**为假，库的判据本身没有错；沿用上游默认根
`/` 时 test4 因此得到 `GLC_PARAMETER_ERROR(0x40)` 而非 `GLC_STATE_ERROR(0x42)`，
用例无法执行。与知识库 E303（受限进程不可枚举根目录，`scope-root-probe-eacces`）
同源。

**补丁 0004 使该用例在本平台可执行**：把 test4 的 catalog 根改为取自环境变量
`$QUESOGLC_TEST_CATALOG`（变量缺省时回退原值 `/`），`build()` 在 `make check`
命令行以 make 变量传入一个**可写**的 build 目录（`<build_folder>/test-catalog`）。
`access()` 因此命中可读目录，test4 走到断言本身并**真实通过 1/1**。补丁**不修改
任何断言、不删除用例、不改上游逻辑流**（R8）；上述结果由最终门禁日志逐行复算
（`RUN: make check -j1 QUESOGLC_TEST_CATALOG=…` / `PASS: test4` /
`All 1 tests passed`）。

## 构建摩擦（既有知识复用）

| 现象 | 处理 | 知识 |
|---|---|---|
| `config.guess` 不识别 `uname -s == HarmonyOS` → `cannot guess build type` | 补丁 0001 新增 HarmonyOS 分支（输出 aarch64-unknown-linux-gnu） | E007 |
| `configure` 建 config.status 临时目录用 `umask 077`，HMDFS 下不可写 | 补丁 0002 去掉 umask 077 | E114 |
| 并行 make 的 jobserver FIFO 在 HMDFS 上 EPERM | `make -j1` | E074 |
| configure 编译并运行 conftest，OHOS 加载器找不到 Conan cache 里的依赖 .so | build scope 注入 `LD_LIBRARY_PATH` | — |
| OHOS 拒绝执行未签名 ELF | package() 用 `binary-sign-tool` 签名（fail-closed，仅 OHOS） | E077 |
| 根目录 `access()/opendir()` EACCES（受限域） | 平台能力边界，见上（不改上游逻辑） | E303 |

## 实测门禁结果

- `ohc-run.py conan-verify quesoglc 0.7.2`（job `quesoglc-verify-20261020-1`，
  exit 0）：G0 PASS / G1 PASS / G2 PASS / G3 PASS（无系统同名库冲突）/ G4 PASS；
  L2/L4/L5 因「无法找到程序包 ID」走 skip。
- CI 同构 `ci/conan/build_and_test.sh`（job `quesoglc-ci-20261020-1`，exit 0）：
  L0 PASS、KC PASS、JC PASS（单软件原子性 1 个包）、L1a/b/c PASS、
  **L1e PASS（破坏性反向验证：移走产物后测试确实失败 → 非空壳）**、
  L2 skip（无 `bin/`，纯库）、L4 warn（见下）、L5 PASS（`lib/` 有内容）；
  `make check` 原始行 `PASS: test4` / `All 1 tests passed` / `Pass rate: 100.0% (1/1)`。
- 上述两个 job 的 `job.json` 均 `head_before == head_after ==` 本文件所在提交。
- L4 的 warn 是**误报**：扫描器用 `grep -E '(strcpy|sprintf|gets|strcat)\b'` 扫
  patches，`0001-build-config.guess.patch` 的**上下文行**里含英文单词
  “targets”，其中 “gets” 命中 `gets\b`；补丁本身没有引入任何危险函数。

## 证据

- 门禁日志与报告：`reports/conan-create.log`、`reports/conan-verify-report.md`
  （`reports/` 被 .gitignore 忽略，属本地证据，不入 PR）
- 本轮门禁日志（绑定本文件所在提交）：
  `$HOME/.local/share/ohpc-porting/runs/quesoglc-verify-20261020-1/`、
  `$HOME/.local/share/ohpc-porting/runs/quesoglc-ci-20261020-1/`
- 任务私有证据：`$HOME/tmp/ohpc-porting/port-quesoglc-20261018-1/`
- 回执：`claude-control/receipts/port-quesoglc-20261018-1.md`、
  `claude-control/receipts/fix-quesoglc-p1-20261020-1.md`
