# yorick-gl 1.1-cvs20070922 适配笔记（OHOS/aarch64 原生 build=host）

## 这是什么

`yorick-gl`（包内名 **yorgl**）是 Yorick 科学解释器的 OpenGL/GLX 3D 图形**插件**，
不是独立库：上游构建产出共享对象 `yorgl.so` + 一批解释层 `.i` 文件，覆盖到 Yorick
安装树（`lib/`、`i0/`、`i/`、`i-start/`）后由 `plug_in, "yorgl"` 在运行时动态加载
（见 yorick `i0/std.i` 的 `plug_in` 文档、`yorick/task.c: Y_plug_in`）。

本包由上游 `configure` 选择两个半边：

| 半边 | 内容 | 本机可否用 |
|------|------|-----------|
| `yiso3d` | 等值面 / 切片引擎（纯计算：ContourTets3D/Gradient3D/isotree/slicetree） | **可用**（本包交付） |
| `yorgl`  | Yorick `play`/`gist` 的交互式 OpenGL/GLX 驱动 | **不可用**（见下「GL 半边阻塞」） |

## 源码来源

- 上游无正式 release tarball，只有 CVS 快照（Debian 源版本 `1.1+cvs20070922`）。
- 采用 Debian 主池 orig 源码包（DFSG 清洗版）：
  `https://deb.debian.org/debian/pool/main/y/yorick-gl/yorick-gl_1.1+cvs20070922+dfsg.orig.tar.gz`
  - size 163053，sha256 `211a27ae3791ec09b26f724cc50354d303a3a7ad3efbe4c41b8fa41810011eef`，
    md5 `91f96e857b11b7d72d4b533d6e1a42b3`。
  - 与 `yorick-gl_1.1+cvs20070922+dfsg-7.dsc` 公布值逐字一致（设备侧 curl 下载后复核）。
- 上游主页：https://software.llnl.gov/yorick-doc/ ；VCS：salsa.debian.org/science-team/yorick-gl。

## GL 半边阻塞（重要，实测证据）

`--no-opengl` 是本**上游 README 明确支持**的配置（"the configure script will cause
yiso3d to be built even if OpenGL cannot be found (or you force --no-opengl)"）。
之所以在本包强制它，是因为 GL 半边在**已发布依赖**上无法加载：

1. yorick-gl 的 GL 对象（`oglx.c`/`glx11setup.c`/`glx11view.c`/`glcode.c` …）引用
   Yorick **X11 版** `play`/`gist` 内部符号：
   `p_window`、`p_wincount`、`p_flush`、`p_destroy`（`play/x11/`）、
   `g_connect`、`g_disconnect`（`gist/xbasic.c`）、`x_rgb_palette`（`play/x11/pals.c`）。
2. 已发布的 `yorick/2.2.04` 以 `NO_XLIB=1` 构建（其 notes：构建时 libx11 未发布），
   这些对象**没有编译**。设备侧证据：
   - `llvm-readelf --dyn-syms <yorick包>/bin/yorick`（1968 个导出符号）中
     `p_window/p_wincount/p_flush/p_destroy/g_connect/g_disconnect/x_rgb_palette` **均缺失**；
   - `llvm-ar t <yorick包>/lib/libyor.a`（113 个成员）中**没有** `xbasic.o/pwin.o/pals.o`。
3. OHOS 动态加载器是 musl，**在 `dlopen` 时一次性完成全部重定位**（无 PLT 惰性绑定），
   因此缺一个符号整库就加载不了。实测：把 GL 版 `yorgl.so` 放进包，`plug_in, "yorgl"`
   直接报 `plug_in: unable to find dynamic library file`。

**解除条件**：需要一个 X11 使能的 `yorick` 构建（`PLAY_DIRS=x11`、不设 `NO_XLIB`，
使 `play/x11/*.o`、`gist/xbasic.o` 进入 `bin/yorick` 的导出符号）。本任务只覆盖
`yorick-gl`，不重建/重发布 `yorick`。届时把 `--no-opengl` 去掉并按下面「GL 半边构建
要点」接上 GL 依赖即可。

### GL 半边构建要点（为解除阻塞预留，已实测可行到「能编译链接」）

- 唯一同时提供 `libGL.so` 与 `GL/glx.h` 的 ohpcd 构建是 **`mesa/24.3.4.1.1.1`**
  （`mesa/26.x` 只有 EGL/GLES；glu 不需要——插件自带 `gluLookAt` 等实现在 `glustub.c`，
  `glcode.h` 把 `glu*` 映射到它们）。mesa 精确依赖 `libx11/6.4.0`、`libxext/6.4.0`。
- GL 版 `yorgl.so` 运行时闭包：`libGL.so.1 -> libgallium-24.3.4.so -> libLLVM.so.20.1`；
  mesa 把 `llvm` 标为 `visible=False`，conan 会把它列进 "Skipped binaries"，
  **必须额外 `requires("llvm/20.1.0")`** 才能让 dlopen 成功。
- 上游 `configure` 的 GL 探测选项多处有 bug（见下），头文件路径需用 `CPATH` 注入、
  库路径用 `--gllib="-L<prefix>/lib"`。

## 编译环境

- 构建系统：上游自定义 `configure`（sh 脚本）+ 手写 `Makefile`/生成的 `Makegl`，
  复用 `yorick` 包提供的构建约定（`Make.cfg` / `Makepkg` / `Makedll`）。
- 原生构建（build = target = OHOS/aarch64，铁律 #0：未使用 `--host/--build/--target`）。
- 编译器：clang 15（来自 Conan conf `tools.build:compiler_executables`，经 `make CC=...`
  命令行覆盖 yorick 包 `Make.cfg` 内硬编码的 CC）。
- Conan 2.29.1；profile `ci/conan/profiles/ohos-aarch64`。

## 构建步骤（conanfile.py）

```sh
sh ./configure --yorick=<yorick包>/bin/yorick --no-opengl   # 只需 yorick/2.2.04
make -j1 CC=<conan clang>
```

- `configure` 内部先 `yorick -batch make.i` 改写 Makefile 的 `Y_MAKEDIR`/`Y_EXE`。
- 配方在 configure 之后**断言 Makegl 含 `YISO_PKG_I` 且不含 `YGL_PKG_I`**，
  保证确实是预期中的 yiso3d-only 配置（fail-closed）。
- yiso3d 对象只依赖 libc/libm：`make` 出的 `yorgl.so` DT_NEEDED 仅 `libc.so`。

## 打包布局（package()）

```
lib/yorgl.so          # 插件（plug_in 加载 "yorgl.so"）
i0/cntrfunc.i         # PKG_I       -> <Y_SITE>/i0
i/contour.i tristruct.i   # PKG_I_EXTRA -> <Y_SITE>/i
i-start/yiso3d.i      # PKG_I_START -> <Y_HOME>/i-start
licenses/LICENSE
```

- 鸿蒙签名：仅 `os == "OHOS"` 时对 `lib/yorgl.so` 自签
  （`binary-sign-tool sign -selfSign 1`），`llvm-readelf -SW` 断言恰 1 个 `.codesign`
  段，fail-closed；签名后 `os.chmod` 恢复权限。

## 上游测试

上游有 `testgl.i` 与 `testisotree.i`，但**都依赖交互式 OpenGL 窗口**（`win3d` →
`glXCreateContext`/X display、`draw3d`、`palette3d`），且上游**没有 `check.i`**
（`make check` 在本包不成立）。OHOS 目标没有 X server / display，故本平台
**无可运行的上游测试**：`TOTAL = 0 = PASS 0 + FAIL 0 + SKIP 0 + NOT_RUN 2`
（逐项见 `test_package/MANIFEST.yml`）。

## 消费者测试（test_package）

无头真实加载 + 真实计算：

1. `plug_dir, ["<包>/lib"];` + `include` 包的 `tristruct.i`/`cntrfunc.i`/`contour.i`
   —— `cntrfunc.i` 顶部的 `plug_in, "yorgl"` 由 `yorick` 动态加载 `yorgl.so`。
2. 断言编译内建存在：`is_func(MakeContourTree)`、`is_func(PrepIsoTet)`、
   `is_func(ContourTetZone)`。
3. `PrepIsoTet()`（构建 marching-tet case 表）断言返回 0。
4. 经上游解释层 `mak_isotree(r)` 调用编译 `MakeContourTree`，在 12×12×12 径向场上
   建八叉树，断言 `tree.maxdepth >= 1`（设备实测 maxdepth = 5）。
5. 打印 `YORICKGL_CONSUMER_OK`；`test_yorick_gl.sh` 断言退出码 0 + 该标记。

> 破坏性反向验证（CI L1e）：移走包 `lib/` 后 `yorgl.so` 无法加载，测试必然失败 ——
> 证明该测试真实依赖被测包产物。

## 注意事项 / 坑

- **GL 半边阻塞**：见上「GL 半边阻塞」，根因是 `yorick/2.2.04` 为 NO_XLIB 构建，
  缺 `play/x11` + `gist/xbasic` 的导出符号；musl 的 dlopen 一次性重定位使缺一符号即失败。
- **上游 `configure` 的 GL 探测选项三处都坏**：`--glinc` 分支 `sed -e s/--glinc//`
  少了 `=`（`--glinc=/path` → `=/path`）；`--prefix` 分支把 `glinc=<prefix>/include`
  （**无 `-I`**）直接塞给编译器；而 `--glinc`/`--gllib` 的值都会被**原样拼进编译器
  命令行**，必须自带 `-I`/`-L`。用法：头文件走 `CPATH`，库走 `--gllib="-L<dir>"`。
- **mesa 版本陷阱**：`mesa/26.1.5` 只有 `libEGL/libGLESv2`，**没有 `libGL.so`/`glx.h`**；
  必须用 `mesa/24.3.4.1.1.1`。
- **mesa 的 llvm 运行时坑**：`mesa/24.3.4.1.1.1` 的 `libGL.so.1` NEEDED
  `libgallium-24.3.4.so`，后者 NEEDED `libLLVM.so.20.1`；mesa 配方把 llvm 标为
  `visible=False`，conan 不会安装/传播其二进制。做 GL 半边时必须显式
  `requires("llvm/20.1.0")`，否则 `plug_in` 的 `dlopen` 因找不到 `libLLVM.so.20.1` 失败。
- **`save_script("conanbuild")` 自引用坑**（跨库已知）：生成环境脚本必须用包私有名字
  （本包用 `yorick_gl_build`），否则 `. conanbuild.sh` 自引用导致 sh SIGSEGV。
- **OHOS `/system/bin/sh` (mksh) 不能执行 ELF**：test 包装脚本用 bash
  （`/data/service/hnp/bin/bash`）。
- **临时目录**：`generate()` 把 `TMPDIR/TMP/TEMP` 指向 build 目录内，避免 OHOS `/tmp`
  只读问题。
- **test_package 不得写回仓库**：conan 跑 `test()` 时 cwd == `test_package/`，直接
  写文件会污染源码树；本包把临时脚本/隔离 HOME 放到 `tempfile.mkdtemp()`（落在
  任务私有 `$HOME/tmp/ohpc-porting`），`test()` 只读 `test_package/` 里的资产。
