# libwraster 0.96.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-15
- 编译器: clang/clang++（OHOS SDK clang 15，host=OHOS 6.0 / arch=armv8）
- 状态: built

## 编译步骤

源码取自 WindowMaker 0.96.0 官方 release tarball（window-maker/wmaker）。
该 tarball 是包含整个 Window Maker 桌面环境的源码树，本配方**只构建其中的
栅格图像库子目录 `wrlib/`**（即 libwraster），WINGs 与 wmaker 本体均不构建。

1. 顶层 `configure`：由 `configure-ohos` 包装执行（`umask 077` → `umask 022`，
   适配 HMDFS 权限语义），在构建目录生成 `config.h`、顶层 `Makefile` 与各子目录
   `Makefile`：
   ```
   ./configure --host=aarch64-linux-ohos \
       --disable-debug --disable-pango --disable-magick \
       --disable-png --disable-jpeg --disable-gif --disable-tiff --disable-webp \
       --enable-xpm --disable-animations --disable-mwm-hints --disable-boehm-gc \
       --disable-xdnd --disable-wmreplace --disable-res --disable-shm \
       --disable-xinerama --disable-randr --disable-shared --enable-static
   ```
2. `make -j1 config-paths.h` —— **必须先执行**：`config.h` 末尾有
   `#include "config-paths.h"`（configure.ac 的 `AH_BOTTOM`），而生成它的规则
   只存在于顶层 Makefile 的 `BUILT_SOURCES` 中，`wrlib/Makefile` 没有该规则，
   直接 `make -C wrlib` 会报
   `config.h:285:10: fatal error: 'config-paths.h' file not found`。
3. `make -j1 -C wrlib` —— 只编译 wrlib。
4. `make -j1 -C wrlib install DESTDIR=<package_folder>` —— 安装。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.sub` 拒绝 `aarch64-unknown-linux-ohos`（`OS 'ohos' not recognized`，报错点 config.sub:1766） | 2022 年版 config.sub 的 OS 列表没有 `ohos` | `patches/0001-config.guess.patch`（识别 HarmonyOS）+ `patches/0002-config.sub.patch`（接受 `linux-ohos` 组合） |
| 2 | `config.h:285:10: fatal error: 'config-paths.h' file not found` | 该文件由顶层 Makefile 的 `BUILT_SOURCES` 规则生成，`wrlib/Makefile` 无此规则 | configure 之后先 `make -j1 config-paths.h`，再 `make -C wrlib` |
| 3 | configure 报 `No package 'xft' found` | 顶层 configure 对 Xft 是硬探针（pkg.m4，检测的是 WINGs 的需要）；wrlib 源码零引用 Xft，`wrlib/Makefile.am` 的 `LIBADD` 只含 `@GFXLIBS@ @MAGICKLIBS@ @XLIBS@ @LIBXMU@ -lm` | **不引入 libxft 依赖**：`_build_environment()` 注入 `XFT_CFLAGS`/`XFT_LIBS` 旁路该探针（假依赖不进入 requires，R26） |
| 4 | 曾误把 `libxft` 写入 `requires` → 下游消费者产物出现 `NEEDED libXft.so.2`（运行期依赖平台外库，违反 R26） | 假依赖经 `cpp_info.requires` 传递给消费者 | 移除 libxft；`readelf -d` 复核消费者产物 `DT_NEEDED`（wmglobe 复核结果 xft_needed=0） |
| 5 | autotools helper 脚本缺执行位 | 部分适配路径只保留文件内容、不保留权限位（知识 E490） | `build()` 内对 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`/`ltmain.sh` 执行 `chmod 0o755` |

## 源码修改

- `patches/0001-config.guess.patch` —— config.guess 识别 HarmonyOS，
  输出 `aarch64-unknown-linux-ohos`。
- `patches/0002-config.sub.patch` —— config.sub 的 OS 列表接受 `linux-ohos` 组合。

两个补丁均为 `refresh-patch --auto` 生成的 config 探针补丁，已回环验证
（`config.sub aarch64-unknown-linux-ohos` 返回 0）。

## 依赖版本

- libx11/6.4.0（force）
- libxext/6.4.0
- libxpm/3.5.17

无 libxft：上游 Xft 探针由 `XFT_CFLAGS`/`XFT_LIBS` 旁路，wrlib 源码零引用该库
（消费者产物已复核无 `NEEDED libXft.so.2`）。

libxmu 不需要：唯一调用 `XmuLookupStandardColormap`（context.c）被
`#ifdef HAVE_LIBXMU` 保护，未定义时走回退路径。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify libwraster 0.96.0
G0 ✅  G1 ✅  G2 ✅(conan create)  G3 ✅  G4 ✅  L2/L4/L5 ✅
✅ 配方验证通过: libwraster 0.96.0
```

`test_package/` 下两层测试均在目标平台实际构建并执行：

1. `test_package/test.c`（`libwraster_test`）——通过真实 wraster API
   （`RCreateImage` / `RClearImage` / `RPutPixel` / `RGetPixel` / `RScaleImage` /
   `RMessageForError` / `RReleaseImage`）执行 15 条断言，非空壳测试。
   X 相关的入口（`RLoadImage` / `RConvertImage` / `RCreateXImage` /
   `RGetImageFromXPMData`）需要 Display，不在本层覆盖，留给下游 wmglobe 集成复核。
2. `test_package/consumer.c`（`libwraster_consumer`）——**端到端消费者用例**：
   用 4 种规格色构造 4x4 图标 → `RScaleImage` 放大到 8x8 → `RClearOperation`
   打出 2x2 全透明窗口 → 由库自身 `RSaveImage(path, "XPM")` 写出真实 XPM 产物，
   同时用 `RGetPixel` 回读全图并落 `consumer-report.txt`。`test()` 随后用
   **独立实现的 XPM 解析器**解码产物（不调用库），与回读的内存镜像逐像素比对，
   再对照输入规格（象限核心色、透明窗口、调色板）校验，并重跑第二次要求两份产物
   sha256 完全相同。

   实测（aarch64-linux-ohos 交叉编译产物，`conan test` 环境）：产物
   `dockapp-icon.xpm` 215 字节，sha256
   `b1f2e5df31f88882801b7afbf4e035d3734239e3e999ebe43f08aef409884f8b`，
   8x8 RGBA、4 种规格色 + 2x2 透明窗口，两份产物字节一致。

## 上游测试清点（R51 三步法）

- **清点**：上游 `wrlib/tests/` 共 4 个测试程序（`testdraw`、`testgrad`、`testrot`、`view`）
  与 3 个数据文件（`test.png`、`tile.xpm`、`ballot_box.xpm`）；`wrlib/Makefile.am` 为
  `SUBDIRS = . po`，tests 目录仅以 `EXTRA_DIST` 分发。
- **注册情况**：4 个程序在 `wrlib/tests/Makefile.am` 中声明为 `noinst_PROGRAMS`，
  未纳入 automake 的 `TESTS`/`check_PROGRAMS`，因此 `make check` 不会自动运行它们。
- **实跑情况**：**已实跑 4/4**（2026-10-16，OHOS aarch64 本机 + Xvfb 21.1.15 虚拟显示
  `:99 1024x768x24`，TCP 连接；上游源码零修改）。testdraw/testgrad/view 退出码 0；
  testrot 为设计上的无限动画循环，timeout 10s 主动终止，185 帧无崩溃。
  详见 `reports/upstream-test.md`（含完整日志）。
  Xvfb 经 cmd-pkgs 预编译包安装于用户级 prefix（不污染共享系统）；
  XKB 数据来自 xkeyboard-config 2.42 预编译包。
- **本包测试覆盖**：`test_package/` 两层测试均在建产物上实际执行——`test.c`
  （15 条断言，覆盖与 X 无关的加载/转换核心路径）与 `consumer.c`
  （端到端消费者：构造→缩放→打透明孔→库自身写出 XPM→独立解码校验，见「验证结果」）。

## 注意事项

- 只构建 `wrlib/`；上游 tarball 中同时携带 WINGs 与 wmaker，不纳入本包。
- 使用方（wmglobe / wmjupiter）以 `-lwraster` 链接，依赖 12 个 `R*` 函数
  （`RLoadImage`/`RCreateImage`/`RScaleImage`/`RConvertImage`/`RPutPixel`/
  `RClearImage`/`RCreateXImage`/`RDestroyXImage`/`RPutXImage`/
  `RGetImageFromXPMData`/`RReleaseImage`/`RRetainImage`/`RMessageForError`）。
- 默认产物为静态库（`shared=False`）；`shared=True` 时 `package()` 会清理构建期 RPATH。
- **alpha 写入语义**：`ROperateRectangle` 走 `wrlib/draw.c` 的快速路径分支
  （`color->alpha == 255 || operation == RCopyOperation`）时会把 alpha 强制写成 255，
  即使传入颜色的 alpha 为 0 —— 即 `RCopyOperation` **产不出透明像素**（实测传
  `{0,0,0,0}` 回读得到 `000000ff`）。需要真正透明区域必须用 `RClearOperation`
  （走 `operatePixel`，写 `rgb=0, a=0`，实测回读 `00000000`）。XPM 写出器对 RGBA
  图像无条件在色表中输出 `None` 项，透明像素以空格符号编码。
---

**编译结束**: 2026-10-16 21:33
**最终状态**: built
