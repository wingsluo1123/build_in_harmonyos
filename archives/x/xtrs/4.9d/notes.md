# xtrs 4.9d — HarmonyOS PC (OHOS aarch64) 适配笔记

## 1. 这是什么软件

`xtrs` 是 **TRS-80 Model I/III/4/4P 模拟器**（基于 Z80）。核心是纯 C 的 Z80
指令解释器 `z80.c`；用户界面是 X11 客户端（`trs_xinterface.c`/`trs_keyboard.c`）。
上游用手写 `Makefile` + `Makefile.local` 构建四个程序：

| 程序 | 说明 | 是否可无头运行 |
|---|---|---|
| `xtrs` | 模拟器本体（X11 客户端，链 `libX11`） | 否（需 X display） |
| `mkdisk` | 生成空白 TRS-80 软盘镜像 | 是 |
| `hex2cmd` | Intel-HEX → TRS-80 `.cmd` | 是 |
| `cmddump` | 反汇编/转储 `.cmd` | 是 |

- 源码身份：Ubuntu multiverse 源包 `xtrs_4.9d.orig.tar.gz`（上游 4.9d，
  sha256 `3985f233…`）。上游 4.9d 只在 tim-mann.org 以 tarball 分发（无对应 git tag）。
- 许可：Clarendon Hill Software 的自定义许可（源码头注释：保留版权即可使用/再分发）。
- 内建 ROM：`fakerom.hex`（Model I/III/4 打印“无 ROM”提示）与 `xtrsrom4p.hex`
  （Model 4P 最小自由 ROM），构建时由 `compile_rom` 转成 `trs_rom*.c`；无需 `zmac`。

## 2. 上游测试清点（R51）

上游**没有任何自动化测试**：无 `tests/`、无 `make check`/ctest，`Makefile` 只有
`all/clean/install` 等目标。结论：上游测试用例数 **N = 0**，无可移植用例；由本次适配
新增**鸿蒙特有消费者测试**（见第 5 节，5 项断言）。

## 3. 关键坑：OHOS 定义 `__linux`，误激活 Linux-only 特性块

OHOS clang（target `aarch64-unknown-linux-ohos`）预定义了：

```
#define __OHOS__ 1
#define __linux  1
#define __linux__ 1
#define linux    1
```

而 xtrs 用 `#if __linux` 作为“在 Linux 上启用某特性”的开关。在 OHOS 上这些块
被误判为“在 Linux 上”而编译进去，于是 `#include` 到 Linux 内核/驱动专有头：

| 位置 | 归属特性 | 误激活后需要 | OHOS |
|---|---|---|---|
| `trs_cassette.c`（`HAVE_OSS`/`OSS_SOUND`） | OSS 声音/卡带直读 | `<sys/soundcard.h>` | 无此头 |
| `trs_disk.c`（物理软驱控制器） | `/dev/fd*` 原始软驱 | `<linux/fd.h>`、`<linux/fdreg.h>` | 无此头 |

→ 编译期 `fatal error: 'sys/soundcard.h' file not found` /
`'linux/fd.h' file not found`。

### 修法：按**能力**探测，而非平台身份

**不要**引入 `__OHOS__` 等平台宏判分支（仓库 R8/PF5：补丁新增行不得出现私有平台宏，
应以 POSIX/能力探测适配）。改用 `__has_include` 探测所需头是否真实存在：

```c
/* trs_cassette.c */
-#if __linux
+#if defined(__linux) && __has_include(<sys/soundcard.h>)

/* trs_disk.c */
-#if __linux
+#if defined(__linux) && __has_include(<linux/fd.h>)
```

补丁 `0001`（2 文件 10 处）只保留所需头真实存在时的 Linux 特性；软件路径（磁盘镜像、
卡带文件、Z80 核心）不受影响；被停用的仅是依赖 Linux 内核/驱动的能力（OSS 声音、
物理软驱）。`trs_uart.c` / `trs_xinterface.c` 中的 `#if __linux` 只影响设备名/X 资源
选项，不需要（也不应）改动，故补丁不再触碰。

> `__has_include` 是 clang 内建操作符；OHOS 工具链为 clang，直接可用。

## 4. 构建

- 只编 4 个程序：`make -j1 CC=<clang> DEBUG="-O2" IFLAGS="…" LDFLAGS="…" XLIB="-lX11"
  READLINE= READLINELIBS= xtrs mkdisk hex2cmd cmddump`
  （`manpages` 目标需 `nroff/colcrt`，跳过；man 源按 `.1` 安装）。
- **X11 头来自两处**：libX11 自身（`Xlib.h`/`Xutil.h`/`Xresource.h`）与
  `xorgproto`（`X11/keysym.h`/`keysymdef.h`/`X.h`）。`xorgproto` 是 `libx11` 的**传递依赖**，
  配方聚合所有依赖的 include 目录（`-I<libx11>/include -I<xorgproto>/include`），否则
  报 `fatal error: 'X11/keysym.h' file not found`。
- 依赖：`libx11/1.8.13`（制品仓预编译，传递拉入 `libxcb/libxau/libxdmcp/xorgproto`…）。
- 关闭可选的 readline/ncurses（调试器用），减少依赖。

## 5. 产物与消费者测试

产物：

| 路径 | 说明 |
|------|------|
| `bin/xtrs` | 模拟器（`DT_NEEDED libX11.so.6`） |
| `bin/mkdisk` `bin/hex2cmd` `bin/cmddump` | 无头 CLI 工具 |
| `share/man/man1/*.1` | man 页（由 `*.man` 改名） |
| `licenses/README` | 上游 README |

消费者测试 `test_package/test_xtrs.sh`（5 项断言，鸿蒙特有）：

| 断言 | 期望 |
|------|------|
| `hex2cmd fakerom.hex > rom.cmd` | 154 字节 |
| `cmddump rom.cmd` | 打印 `loaded 0x…` |
| `cmddump rom.cmd` | 打印 `transfer address = 0x…` |
| `mkdisk -3 disk3.dsk` | 8704 字节 |
| `xtrs`（无 DISPLAY） | 打印 `Unable to open display`（证明 X11 链接完整、能加载到显示初始化） |

真机 `conan create`：`CREATE_RC=0`，消费者 **5/5**。

## 6. 已知限制

- **模拟器运行需 X display**：OHOS 无头环境只做“加载并报告缺 display”的验证；
  GUI 交互不在自动化范围内（与其它 X11 软件一致）。
- OSS 声音、物理软驱按第 3 节在 OHOS 上停用（依赖 Linux 驱动）。

---
**编译结束**: 2026-10-12
**最终状态**: built
