# xwax 1.10 适配笔记

## 编译环境
- 构建系统: makefile（上游自带 POSIX Makefile + 手写 `configure` shim）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，target aarch64-unknown-linux-ohos）
- 平台: OHOS / HarmonyOS PC，aarch64，**原生 build=host**（非交叉编译）
- 状态: built
- 依赖: sdl2/2.30.10、sdl2_ttf/2.24.0、alsa-lib/1.2.16.1（均已发布到 ohpcd）

## 源码
- 官方源: `https://github.com/xwax/xwax/archive/refs/tags/1.10.tar.gz`
- sha256: `5d9c7aa46582bf3bb53a4336f4b2668e7c4e4382e29989d5b902e26e7c5d76de`（90370 bytes）
- 版本核对: tag `1.10` → commit `be863572137929f70aa3ff0cef3b6b76f4973005`，CHANGES 首行 `v1.10 (2026-05-03)`（R39）
- 无补丁（`patches_applied: []`）

## 编译步骤

1. `generate()`：`AutotoolsToolchain` + `AutotoolsDeps` 生成 conanbuild 环境；
   把 sdl2 包的 `bin/` 前置到 PATH（Makefile 通过 `sdl2-config --cflags` 取 SDL2 头文件路径）。
2. `source()`：`get()` 解压官方 tarball（strip_root）。
3. `configure`：`sh ./configure --prefix / --enable-alsa`
   - 注意：上游 `configure` **不是 autoconf**，`--prefix` 接受**独立参数**（`--prefix /`），
     写成 `--prefix=/` 会被忽略，PREFIX 回落到 `$(HOME)`，导致编进二进制的 EXECDIR 错误。
   - 本平台为原生构建，**未传** `--host=/--build=/--target=`（铁律 #0）。
4. `make -j1 VERSION=1.10 SDL_CFLAGS="$(sdl2-config --cflags)" SDL_LIBS="$LIBS"`
   - `VERSION`：Makefile 用 `$(shell ./mkversion)` 经 `git describe` 生成；官方 tarball 无 `.git`，
     `mkversion` 返回失败、`.version` 不生成，故在命令行显式注入 `VERSION=1.10`。
   - `SDL_LIBS="$LIBS"`：Makefile 的 `$(SDL_LIBS)` 只覆盖 SDL 自身；`$LIBS` 是 AutotoolsDeps
     算出的**完整静态传递链接行**（`-lSDL2_ttf -latopology -lasound -lfreetype -lSDL2 -lm -lpthread -lrt`），
     真正需要的 freetype/alsa 传递库由此进入链接。
   - `-j1`（R9：HMDFS 不支持 jobserver FIFO）。
5. 上游测试：`make` 的 `all` 目标会编译 `tests/` 下 8 个手动测试程序，但上游**没有 `make check`**。
   无头、无参数可跑的在 `build()` 中逐个真跑（见下）。
6. `package()`：OHOS 上**无 `install` 命令**（coreutils `install -D` 不可用），因此不用
   `make install`，改用 conan `copy()` 落盘：`bin/xwax`、`libexec/xwax-scan`(←`scan`)、
   `libexec/xwax-import`(←`import`)、`share/man/man1/xwax.1`。

## 上游测试（R51）

上游 TAB 变量声明 8 个手动测试程序；`make all` 编译全部。逐项结果：

| # | 测试程序 | 状态 | 说明 |
|---|----------|------|------|
| 1 | tests/cues | PASS | 自包含断言（cue 点存取），`< /dev/null` 退出 0 |
| 2 | tests/external | PASS | `fork_pipe_nb()`/`get_line()` 管道读取 `/usr/bin/find` 输出，断言 `wait()==pid` |
| 3 | tests/observer | PASS | watch/fire/ignore 通知（仅输出），退出 0 |
| 4 | tests/status | PASS | status 字符串存取 + 变更通知，退出 0 |
| 5 | tests/timecoder | PASS | 时间码定义查找 + 初始化（断言 `def != NULL`），stdin 空则立即结束 |
| 6 | tests/library | NOT_RUN | 手动测试，需要 `usage: <scan> <path>` 参数与真实唱片库路径 |
| 7 | tests/track | NOT_RUN | 手动测试，需要 `usage: <command> <path>` 参数 |
| 8 | tests/ttf | NOT_RUN | 需要显示器（`SDL_CreateWindow`）与 TTF 字体；镜像内无 `/usr/share/fonts` |

**TOTAL = PASS + FAIL + SKIP + NOT_RUN = 5 + 0 + 0 + 3 = 8**

（`tests/midi` 仅在 `ALSA=yes` 时单独构建，不在 `TESTS` 列表内、`make all` 不构建，故不计入。）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./mkversion` 失败、`VERSION` 为空 | 官方 tarball 无 `.git`，`git describe` 失败 | 命令行注入 `VERSION=1.10` |
| 2 | 头文件找不到 `SDL.h` / `SDL_ttf.h` | Makefile 经 `sdl2-config --cflags` 取路径；sdl2 包 include 目录是 `include/SDL2` | `generate()` 把 sdl2 包 `bin/` 加入 PATH |
| 3 | 链接缺 `freetype`/`asound` 符号 | Makefile 只把 `$(SDL_LIBS)` 放进 LDLIBS，不含传递静态库 | `SDL_LIBS="$LIBS"`（AutotoolsDeps 完整链接行） |
| 4 | `sh ./configure --prefix=/` 未生效 | 上游 configure 是手写脚本，`--prefix` 是独立参数 | 改为 `--prefix /` |
| 5 | `package()` 报 `copy() got an unexpected keyword argument 'rename'` | Conan 2 的 `files.copy()` 无 `rename` 参数 | 用 `copy()` + `files.rename()` 两步重命名 |
| 6 | `make install` 不可用 | OHOS 无 coreutils `install`（`install -D`） | 不用 `make install`，`package()` 直接 `copy()` |

## 源码修改

无。未改任何上游源文件，`patches_applied: []`。

## 依赖版本

- sdl2/2.30.10（静态，提供 `sdl2-config`）
- sdl2_ttf/2.24.0（静态）
- alsa-lib/1.2.16.1（共享；传递依赖含 `libatopology.so`）
- freetype/2.14.3.1（共享，经 sdl2_ttf 传递）

## 验证结果

```
$ ohc-run.py lang-preflight xwax 1.10 --src <extract> --lang cpp
  detected_language=c（平台标签 cpp 未采信；源文件 36 个 .c）

$ conan create archives/x/xwax/1.10 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing
  ...
  tests/cues < /dev/null        → rc=0
  tests/observer < /dev/null    → rc=0
  tests/status < /dev/null      → rc=0
  tests/timecoder < /dev/null   → rc=0
  tests/external < /dev/null    → rc=0
  Launching test_package → Running test()
  [test] xwax --help rc=0
  [test] version banner OK: xwax 1.10
  [test] usage text OK
  [test] --dummy option listed
  [test] helper scripts packaged OK
  [test] PASS: xwax consumer smoke test (5 assertions)

$ ohc-run.py conan-verify xwax 1.10 --profile <ohos-aarch64> --project-dir <worktree>
  G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS → "配方验证通过: xwax 1.10"
```

## 注意事项

1. **运行期需要依赖动态库路径（E019）**：`xwax` 链接了共享的
   `libasound.so`/`libatopology.so`/`libfreetype.so.6`（SDL2 与 SDL2_ttf 为静态；
   ohpcd 上 alsa-lib / freetype 只发布了 shared 变体）。这些 `.so` 位于 Conan 缓存包目录，
   不在加载器默认搜索路径，直接运行会报 `Error loading shared library libatopology.so`。
   按 E019：OHOS musl 的 ld.so **不展开 `$ORIGIN`**，无法用相对 RPATH 自救；正确做法是设置
   `LD_LIBRARY_PATH`（或经 `conan install` 生成的 runenv）——`test_package` 即在 `conanrun` 环境下执行。
   这与本仓库既有音频类应用（aeolus / darkice / ant-phone 等同样依赖共享 alsa-lib）的处理方式一致；
   CI 的 L2 单二进制 smoke（不带 runenv）会因此该项跳过/告警，属非阻断项。
2. **`EXECDIR` 编译期固定为 `/libexec`**：`xwax` 用 `EXECDIR`（`--prefix /` → `/libexec`）作为
   `--scan` / `--import` 的默认路径。Conan 包是 relocatable 的，实际安装在包目录下，因此运行时
   需显式传 `--scan <包目录>/libexec/xwax-scan --import <包目录>/libexec/xwax-import`
   （或把 helper 部署到 `/libexec`）。上游本身即假定 prefix 为真实安装前缀。
3. **音频设备**：本平台构建启用 ALSA（`--enable-alsa`），JACK/OSS 关闭；另有内建 `--dummy` 无设备模式。
   运行期是否有可用的 ALSA 设备取决于目标机，不属本次构建门禁范围。
4. **字体**：`xwax` 启动界面需要 DejaVu 系列 TTF 字体（`interface.c` 的 `font_dirs[]`）；
   目标镜像未随附 `/usr/share/fonts`，完整图形界面运行需额外提供字体。`xwax --help` 不需要字体。
