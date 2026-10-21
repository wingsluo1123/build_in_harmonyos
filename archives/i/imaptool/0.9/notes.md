# imaptool 0.9 — OHOS 适配笔记

## 1. 源码核验（W0）

| 项 | 值 |
|---|---|
| 上游原站 | `http://www.sspitzer.org/imaptool/` — **不可达**（2026-10-19 实测 `curl` rc=000） |
| 源码来源 | Debian 稳定源包 pool：`https://deb.debian.org/debian/pool/main/i/imaptool/imaptool_0.9.orig.tar.gz` |
| sha256 | `8c2726d1e10c7bda8d1b145bf503bd4394ab4a6b460e216d1cdd167339cfb1b5` |
| md5 | `8e716c8b8af4486f71b33c30a62de2ab`（与 Debian 源包 `imaptool_0.9-24.dsc` 声明一致，dsc 30897 字节） |
| 解包顶层目录 | `imaptool-0.9.orig/`（配方 `strip_root=True`） |
| 文件清单 | 13 个：`LICENCE.TXT Makefile dgif_lib.c file2pixmap.c file2pixmap.h gif_err.c gif_hash.h gif_lib.h gifalloc.c icon iconmask imaptool.c imaptool.man` |
| 语言 | 纯 C（5 个 `.c`，`lang-preflight` 判定 `detected_language="c"`；平台标签 `cpp` 不采用） |

上游原站已停分发，源码以 Debian 维护的 orig tarball 为准；主版本 0.9 与任务 version 一致。

## 2. 依赖（制品仓 `conan list -r=ohpcd` 实测）

| 依赖 | 版本 | os/arch | 用途 |
|---|---|---|---|
| libx11 | 1.8.13（force） | OHOS/armv8/clang15 | Xlib（`Xlib.h`/`Xutil.h`/`cursorfont.h`） |
| libxt | 1.3.1 | OHOS/armv8/clang15 | X Toolkit Intrinsics（`XtVaAppInitialize` 等） |
| libxaw | 1.0.14 | OHOS/armv8/clang15 | Athena 部件（`X11/Xaw/*`） |
| libxmu | 1.3.1.1 | OHOS/armv8/clang15 | 上游 Makefile `-lXmu` |
| libxext | 6.4.0.1 | OHOS/armv8/clang15 | 上游 Makefile `-lXext` |
| xorgproto | 2025.1 | 头文件 | `X11/X.h`/`Xatom.h`/`Xos.h`/`Xosdefs.h` |
| libjpeg | 10（static） | OHOS/armv8/clang15 | `file2pixmap.c` 的 `-DUSE_JPEG_LIB`（`jpeglib.h`/`jerror.h`） |
| libxcb/libxau/libxdmcp | 1.17.0 / 1.0.11 / 1.1.5 | OHOS/armv8/clang15 | `run=True` 运行期闭包 |

该 X11 图与 `archives/x/xfontsel/1.1.2` 相同。GIF 解码用上游内嵌 `dgif_lib.c`/`gif_err.c`/`gifalloc.c`，无外部 giflib 依赖。

## 3. 手工 Makefile 的处理（核心适配点）

上游 `Makefile` 把 X11R6 路径写死：

```
CC=gcc -I/usr/X11R6/include/
JPEG_INCLUDE=-I/usr/local/include/
JPEG_CHOICE=-DUSE_JPEG_LIB $(JPEG_INCLUDE)
LIBRARIES=-lXt -lXaw -lXmu -lXext -lX11 -ljpeg -lm
LIBDIR=-L/usr/local/lib -L/usr/X11R6/lib
```

配方**不改 Makefile、不打补丁**，只在 `make` 命令行用同名变量覆盖（命令行定义优先级最高，
且 `JPEG_CHOICE` 内部的 `$(JPEG_INCLUDE)` 会展开为命令行值）：

```
make -j1 \
  CC="/data/service/hnp/bin/clang -O2 -I<依赖 include 目录…>" \
  JPEG_INCLUDE="-I<依赖 include 目录…>" \
  LIBDIR="-L<依赖 lib 目录…>"
```

`LIBRARIES` 保持上游原样（这些库全部由已声明依赖提供）。实际编译命令行（本次实测，节选）：

```
/data/service/hnp/bin/clang -O2 -I<...libxaw/include> -I<...libxmu/include> -I<...libxt/include> \
  -I<...libsm/include> -I<...libice/include> -I<...libxext/include> -I<...libx11/include> \
  -I<...libjpeg/include> -I<...xorgproto/include> -c imaptool.c
/data/service/hnp/bin/clang -O2 -I<...> -c file2pixmap.c -DUSE_JPEG_LIB -I<...>
/data/service/hnp/bin/clang -O2 -I<...> -c dgif_lib.c
/data/service/hnp/bin/clang -O2 -I<...> -c gif_err.c
/data/service/hnp/bin/clang -O2 -I<...> -c gifalloc.c
/data/service/hnp/bin/clang -O2 -I<...> -o imaptool -L<依赖 lib 目录…> imaptool.o file2pixmap.o \
  dgif_lib.o gif_err.o gifalloc.o -lXt -lXaw -lXmu -lXext -lX11 -ljpeg -lm
```

链接结果为 OHOS aarch64 ELF，`DT_NEEDED = libXt.so.6, libXaw.so.7, libXmu.so.6, libXext.so.6, libX11.so.6, libc.so`
（`libjpeg` 为静态库，被链入本体，不出现在 `DT_NEEDED`）。

### 编译告警（无 error，clang 15 实测 15 条）

上游是 1996–2000 年的老 C 代码，clang 15 下产生告警但不报错，未打补丁（无 error、不改行为）：

- `gifalloc.c:24` `-Wimplicit-int`（函数缺返回类型，ISO C99 起为告警）
- `dgif_lib.c`/`gifalloc.c` 多处 `-Wimplicit-function-declaration`（`malloc`/`free`/`realloc`/`memcpy`/`memset`/`memcmp` 隐式声明）
- `imaptool.c:663`、`dgif_lib.c:897/899` `-Wpointer-sign`
- `imaptool.c:806` `-Wvoid-pointer-to-int-cast`

> 风险提示：这些隐式声明在 clang 15（OHOS 当前工具链）下是告警；若未来工具链升级到
> C23/clang 16+（隐式函数声明转为错误）需补 `<stdlib.h>`/`<string.h>`。本版本不改动上游源码。

## 4. 鸿蒙签名

`package()` 对 `bin/imaptool` 做 OHOS 自签（`binary-sign-tool sign -selfSign 1`），随后用
`llvm-readelf -SW` 断言**恰有 1 个 `.codesign` 段**，fail-closed；签后 `os.replace` 并
`os.chmod` 恢复原权限。实测日志：`add codesign section success`。

## 5. 上游测试

**N = 0（上游无自动化测试）**，证据：

- `Makefile` 目标仅 `imaptool / imaptool.o / file2pixmap.o / dgif_lib.o / gif_err.o / gifalloc.o / clean`，无 `check`/`test`；`make -n check` 报 `No rule to make target 'check'`（rc=2）。
- 发行包 13 个文件，无 `test/`、`tests/` 目录，无 `*_test` 源文件。
- `imaptool.man` 仅描述交互式用法。

`TOTAL=PASS+FAIL+SKIP+NOT_RUN = 0+0+0+0 = 0`。

## 6. 消费者测试（test_package）

无 X server（设备与 CI worker 镜像内无 Xorg/Xvfb，制品仓未发布 OHOS xorg-server）。
且 `imaptool.c` 在 `parseparams()` **之前**调用 `XtVaAppInitialize()`（`imaptool.c:171` → `:178`），
连 `-h`/`-v` 也需要 display —— 因此无 DISPLAY 路径是本环境唯一可运行路径。

`test_imaptool.py` 真实执行被测二进制并断言（**11/11 通过**）：

1. 二进制存在、可执行；
2. `readelf -d` 的 `DT_NEEDED` 含 `libXaw`/`libXt`/`libX11`（证明链接到 Conan X11 依赖，非系统 X11）；
3. `readelf -SW` 恰 1 个 `.codesign` 段；
4. 无 DISPLAY 运行：`rc=1` 且输出 `Error: Can't open display:`（证明整条动态链
   `libXaw7→libXmu/libXext/libXt→libX11→libxcb→libXau/libXdmcp` 已加载并执行到 Xt 显示初始化，不挂起、不静默成功）；
5. 伪造 `DISPLAY=:9999` 运行：`rc=1` 且输出 `Error: Can't open display: :9999`；
6. 安装的 `share/man/man1/imaptool.1` 存在。

运行期依赖经 `LD_PRELOAD`（依赖图内全部实体 `.so`）+ `VirtualRunEnv` 注入，规避 HMFS 符号链接
materialise 与 OHOS 加载器对 Conan cache 路径 `LD_LIBRARY_PATH` 的不确定性。

## 7. 已知限制

- imaptool 是 GUI 工具，**窗口与图像映射交互无法在本环境运行**（无 X server）；消费者测试覆盖的是
  无 DISPLAY 的 Xt 初始化路径 + ELF 元数据，非窗口功能。这与 `coolmail 1.3`、`xfontsel 1.1.2` 同属
  框架内已接受的形态。
- 平台任务标签 `lang=cpp`，源码实测为纯 C（不采用平台标签）。

## 8. 验证记录

见本目录 `manifest.yaml` 的 `verification` 段与任务回执
`$HOME/.local/share/ohpc-porting/claude-control/receipts/port-imaptool-20261019-1.md`
（含 `conan create` 与 CI 同构门禁 `ci/conan/build_and_test.sh` 的逐条命令、原始输出与退出码）。
