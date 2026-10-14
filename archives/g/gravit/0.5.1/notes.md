# gravit 0.5.1 适配笔记

## 编译环境
- 构建系统: autotools（发行包只含 configure.in/Makefile.am，构建时重建）
- 编译日期: 2026-10-12
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）
- 目标: OHOS / aarch64（HarmonyOS PC），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 编译步骤

```bash
# 1) autotools 重建（发行包没有 configure）
env -u PERL5LIB -u PERL -u AUTOMAKE -u ACLOCAL -u M4 ... \
  perl -I <automake>/share/automake-1.18 <automake>/bin/.aclocal-real \
       --automake-acdir=<automake>/share/aclocal-1.18 \
       --system-acdir=<automake>/share/aclocal --force -I acinclude
env -u ... autoheader --force
env -u ... perl -I <automake>/share/automake-1.18 <automake>/bin/.automake-real \
       --libdir=<automake>/share/automake-1.18 --foreign --include-deps \
       --add-missing --copy --force-missing
env -u ... autoconf --force
# 2) 修掉 autoconf 内嵌的 config.status umask 077 模板（见下）
# 3) 生成 sdl-config 外壳（AM_PATH_SDL 使用）+ 补 gl.pc（指向 OSMesa）
# 4) configure / make / make check / make install DESTDIR=<pkg>
```

configure 关键参数：`--prefix=/ --build=aarch64-unknown-linux-gnu
--host=aarch64-unknown-linux-gnu --without-agar PKG_CONFIG_PATH=<generators>`；
`CPPFLAGS` 由 AutotoolsDeps 注入依赖的 `-I/-L/-l`，并额外加 `-DOSMESA_RENDER`
与 `-I<pkg>/include/SDL`（sdl-image/sdl_ttf 的头在 `include/SDL` 下，而其
`cpp_info.includedirs` 只到 `include`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sh ./autogen.sh` 大面积失败：`Error relocating .../auto/Cwd/Cwd.so: Perl_my_cxt_init: symbol not found`、`Can't locate strict.pm in @INC (//lib/perl5/...)` | conan 的 automake 脚本 shebang 指向构建者 perl（设备 perl 5.42.0），而 perl 工具包导出的 `PERL5LIB` 指向 5.42.2 的 XS 模块；conan autoconf 包迁移后 `.autom4te-real` 的 `@INC` 也已失效。两套 perl 混用 | `env -u` 清掉工具包导出的 perl/autoconf 变量，再用同一解释器显式驱动 `automake`/`aclocal` 的 `.aclocal-real`/`.automake-real`（`-I <automake>/share/automake-1.18`），`autoconf`/`autoheader`/`m4` 用环境自带工具链（与 abx/0.1 同一做法；知识库 E116/E071/E178 同族） |
| 2 | `configure` 停在 `checking whether mmx is supported... bad number '0xunknown'` | 0.5.1 无条件是调用 `AX_EXT_SSE`，该宏用 x86 CPUID 结果做 shell 算术；aarch64 上探针返回 unknown | 补丁 0001：用 `case "$host_cpu"` 限定只在 x86 执行（源码 SSE 代码本来由 `HAVE_SSE` 守卫，语义不变） |
| 3 | `./config.status: can't create ./conffMlGne/subs1.awk: Permission denied` | autoconf 内嵌的 config.status 模板以 `umask 077` 建临时目录；setgid hmdfs 上目录属主非构建 UID，0700 对创建者也不可写 | `configure` 是构建期生成的，补丁无法覆盖 → autoconf 之后重写模板（`umask 077 && mktemp/mkdir` → 按环境 umask），模板若变化则显式报错（同 abx/0.1 `_make_config_status_tmp_writable`、achilles/3 的 0002 补丁） |
| 4 | 链接期 `duplicate symbol: video/state/view` | 自 GCC 10 / 现代 clang 默认 `-fno-common`，而 `src/gravit.h` 里是暂定定义而非 `extern` | 补丁 0005：与上游 develop 分支同名的修复（commit `0f84883`）——头文件只留 `extern`，定义只留在 `main.c` |
| 5 | `src/gravit.h` 无条件 `#include <sys/timeb.h>` 编译失败 | musl 没有 `sys/timeb.h` | 补丁 0005：按 configure 的 `HAVE_SYS_TIMEB_H` 条件包含 |
| 6 | 链接期 `undefined reference to 'rpl_realloc'`（潜在） | `AC_FUNC_MALLOC`/`AC_FUNC_REALLOC` 在不满足 gnulib 假设时把 malloc/realloc 改成 `rpl_*`，本树不含 gnulib 替换模块 | 补丁 0001：不再使用这两个宏（上游 develop 因同一原因也已移除） |
| 7 | 程序启动即 `Could not open font` → 渲染初始化失败 | `DATA_DIR`/`SYSCONFDIR` 是编译期绝对路径（`//share/gravit`、`/etc/gravit`），包安装在任意前缀下并不存在 | 补丁 0004：`findFile()` 增加"可执行文件所在前缀"与"去掉前导 `/` 后的相对路径"两条查找；补丁 0002：`commandInit()` 原本绕过 `findFile()` 直接 `fopen(MISCDIR ...)`，改为走 `findFile()` |
| 8 | configure 报 `checking for GL... no` 后会退化到 `-lGL -lGLU` 而链接失败 | mesa 未设 `pkg_config_name`，`PkgConfigDeps` 只生成 `mesa.pc`/`glu.pc`，没有 `gl.pc`，于是 `PKG_CHECK_EXISTS([gl])` 失败 | 配方在 generators 目录补一份指向 OSMesa 的 `gl.pc`（`glu.pc` 由 Conan 生成并自动 `Requires: mesa`） |
| 9 | 运行期日志出现 `SDL Error: src/gfx.c:1489 Surface doesn't have a colorkey` | sdl12-compat 在无窗口驱动下成功调用后仍留下陈旧错误串，下一帧的 `sdlCheck()` 把它打印出来 | 属上游行为、非失败（GL 侧 `glCheck()` 全程无 `glError`）；在测试中按"清空后不引入新错误"断言 |
| 10 | `libpng warning: Interlace handling should be turned on when using png_read_image` | 应用加载自带 PNG 贴图时的上游用法 | 上游行为，不影响渲染 |

## 源码修改

补丁共 5 个（均为可移植性修复，无平台宏）：

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-configure.in.patch | `configure.in` | 去掉硬编码的 `/usr/local` 头/库路径；移除 `AC_FUNC_MALLOC`/`AC_FUNC_REALLOC`；SIMD 探针只在 x86 执行 |
| 0002-src-command.c.patch | `src/command.c` | `commandInit()` 经 `findFile()` 定位 `commandhelp.txt` |
| 0003-src-gfx.c.patch | `src/gfx.c` | OSMesa 离屏 GL 后端（`OSMESA_RENDER`，由配方定义）：软件 SDL 表面 + OSMesa 上下文 + 帧拷贝取代 `SDL_GL_SwapBuffers()` + GL 入口经 `OSMesaGetProcAddress()`；无桌面模式时回落到默认尺寸 |
| 0004-src-tool.c.patch | `src/tool.c` | `findFile()` 增加可执行文件前缀/相对 cwd 两条查找 |
| 0005-src-gravit.h.patch | `src/gravit.h` | `sys/timeb.h` 条件包含；去掉暂定定义（上游 `0f84883` 同款 `-fno-common` 修复） |

## 依赖版本

- sdl12-compat/1.2.68（SDL 1.2 API 提供者，sdl-image/sdl_ttf 亦链接它）
- sdl-image/1.2.12、sdl_ttf/2.0.11
- lua/5.2.4（上游 0.5.1 起支持 Lua 5.2）
- libpng/1.6.58（PNG 截图）
- glu/9.0.3、mesa/24.3.4.1（OSMesa 离屏 GL）
- 传递依赖：sdl2/2.30.10、freetype/2.14.3、libjpeg-turbo/3.2.0、libtiff/4.7.2、libwebp/1.6.0、zstd/1.5.7、zlib/1.3.1.1、expat/2.8.2.1.1

`agar`（可选 GUI，1.4.1+）制品仓未发布，按上游支持以 `--without-agar` 构建，
使用内置控制台界面。

## 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
...
gravit/0.5.1: Package 'cda1b75c16792ad4b5c86f7575aefed1d6887d03' created
$ # test_package（conan create 内置执行）
test_cli: 5 consumer cases, 5 passed, 0 failed
test_headless_render: 3 consumer cases, 3 passed, 0 failed
test_gl_stack: 3 consumer cases, 3 passed, 0 failed
$ # 本地 CI 复验（rule12 用例化改造后，HEAD 5e68ce9b7f）：
$ #   G0/KC/JC/L0/L1/L5 pass · L2 skip · L4 warn(非阻断) · Pass rate 100.0% (1/1)
$ #   .ci-result.json exit_code=0, integrity_hash=fd78aabc894c5647,
$ #   log_sha256=f9339e4b028883d1af4aedb6888a2e2799b97359ff5be27508d98bede79c3cad
$ #   （sha256sum reports/w3-local-ci.log 实测值与该值一致）

$ # 无头真实渲染（真实输出节选）
Offscreen GL context: 3.3 (Compatibility Profile) Mesa 24.3.4
Your video mode is 320x240x32
OpenGL video driver: vendor=Mesa; renderer=softpipe; version=3.3 (Compatibility Profile) Mesa 24.3.4
multi-threaded rendering: max threads = 20.    Found 20 processors.
screenshot saved to $HOME/.gravit/screenshots/gravit00000.png
# 截图 320x240，非黑像素 75894/76800，颜色数 12930（某次运行示例，真实场景）
```

## 鸿蒙特有测试（rule12）

上游无测试，验证由 `test_package/` 的**11 条具名端到端消费者用例**承担，每条用例按
「构造输入 → 真实执行 → 产出结果 → 校验内容」四段式组织（不是断言清单）：

| 用例 | 内容 | 参考（独立来源） |
|------|------|------------------|
| CLI-1 version-banner | `bin/gravit "echo 1" -v` 的完整输出 | 上游 `src/command.c` 版本/版权字面量，逐字节 |
| CLI-2 help-screen | `-h` 的完整帮助屏 | 上游 `data/commandhelp.txt` + usage 文本，逐字节 |
| CLI-3 long-option-aliases | `--version`/`--help` 与短写法等价 | 同 CLI-1/CLI-2 的参考输出 |
| CLI-4 quit-command | `quit`：退出码 0 且无输出 | 上游 console 的 quit 语义 |
| CLI-5 unknown-command | 未知命令 + 无视频驱动时的提示 | 上游 `src/command.c`/`src/gfx.c` 提示文本 |
| HD-1 offscreen-run-and-self-quit | 真实无头运行 ~11s，内置定时器自行退出 | 被测源码离屏路径与定时器打印点（7 项证据行） |
| HD-2 screenshot-png-structure | 独立解码截图（zlib + 反滤波 + 逐 chunk CRC） | 请求的离屏模式 320x240x32 与 PNG 规范 |
| HD-3 frame-content-real-scene | 帧统计（某次运行示例：非黑 75894/76800、颜色 12930；判据为阈值 非黑>半数、颜色>1000） | 与离屏模式绑定的帧内容判据 |
| GS-1 offscreen-frame-render | OSMesa 离屏渲染 + glReadPixels 回读 | 用例给定的清屏色/四边形色常量 |
| GS-2 windowless-sdl-blit | `gfxOffscreenSwap()` 式整帧拷贝到 SDL 软件表面 | GS-1 渲染帧的给定常量 |
| GS-3 png-roundtrip | libpng 写出/读回往返 | GS-1 渲染帧的给定常量 |

> rule12 整改（2026-10-13）：原实现是三份「断言清单」（19/14/21 条断言，汇总行
> `N executed, M failed`），评审判定「仅断言、不算完整消费者用例」。现改为 11 条
> 具名消费者用例，汇总行输出 `N consumer cases, M passed, K failed`；
> `MANIFEST.yml`/`manifest.yaml` 的申报口径同步由断言数改为用例数
> （`harmony_consumer_case_count: 11`）。`assertion_count` 仅保留为次要追溯口径
> （用例内部的逐项内容比对条数），不作为申报单位。

## 上游测试清点（R51）

上游 0.5.1 **没有**测试套件：tar 内 0 个含 `test` 的路径、`Makefile.am` 中
`TESTS`/`check_PROGRAMS` 命中 0 处、源码树内 0 个名字含 test 的文件或目录；
`make check` 可执行但不注册任何用例（conan create 日志中 `make check` 之后
直接是 `Package built`）。`conanfile.py` 仍执行 `make check` 以保留上游测试
入口的执行痕迹；验证由 `test_package/` 的 11 条消费者用例承担（见上节）。

## 注意事项

- 运行必须设 `SDL_VIDEODRIVER=dummy`（无窗口系统）；渲染走 OSMesa 离屏路径。
- 命令行 `COMMAND` 在视频初始化**之前**执行；需要运行中执行的命令用内置定时器
  `timeradd <name> <sec> <reps> <cmd>` 调度（鸿蒙测试即用 `screenshot` + `quit`）。
- `-v`/`-h` 的输出经内置控制台，需先 `echo 1` 打开 stdout 模式才会打印到标准输出。
- OSMesa 为软件渲染，`softpipe` 会被上游的驱动黑名单识别并自动降级视觉效果
  （tailLength=0、particleRenderMode=2），属预期行为。
---

**编译结束**: 2026-10-12 14:00
**最终状态**: built
