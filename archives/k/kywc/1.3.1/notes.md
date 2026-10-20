# kywc 1.3.1 适配笔记

## 为什么只打包 libkywc

kywc 是麒麟的 Wayland 合成器（kylin-wayland-compositor）。OHOS 侧唯一
消费者是 ukui-quick 4.22.0.1 的 `modules/window-thumbnail`：它在
CMakeLists.txt:38 用 `pkg_check_modules(... REQUIRED kywc)` 查找，源码里
`#include <libkywc.h>`，调用 `kywc_context_create()` 取输出/窗口/工作区
缩略图。该查找没有版本下限。

合成器本体（`src/`、`examples/`、顶层 `kylin-wlcom`）要求
wlroots `>=0.17.0,<0.18.0`，以及 xkbcommon、libdrm、libinput、pixman、
json-c、libsystemd、cairo、pango、librsvg、libjpeg、libudev、libunwind、
xcb 一整套桌面栈；这些在 OHOS 制品仓里都不存在，OHOS 侧也没有任何消费者
需要合成器。因此本配方只构建 `libkywc/`，产物是：

- `lib/libkywc.so`（无版本号实体文件）
- `include/libkywc.h`
- `lib/pkgconfig/kywc.pc`
- 四个协议生成文件编进库内（`kywc-capture/output/toplevel/workspace-v1`）

## 源码与版本号

上游 tarball 取自官方仓库的 archive 接口（openKylin 托管于 Gitee，属官方
托管源）：

```
https://gitee.com/openkylin/kylin-wayland-compositor/repository/archive/upstream/1.3.1.tar.gz
sha256 1bee5ccd84be11bda7659d35cb66d3bb7b1df93b5cd686cd1e881213dccbef0c
```

根目录 `kylin-wayland-compositor-upstream-1.3.1/`，LF 行尾（补丁按 tarball
原文生成）。Gitee 的接入层对 conan 默认 User-Agent 返回 HTML 页面（HTTP 200、
text/html，约 46 KiB），sha256 必然不匹配；source() 对该 URL 显式带
`User-Agent: curl/8.5.0`，真机实测可取回 560436 字节的 tarball
（sha256 与 conandata 一致）。

上游打了 `upstream/1.3.1` tag 但 `meson.build` 的
`project(version:)` 仍是 `1.3.0`（漏 bump）；补丁 0001 顺手对齐成 `1.3.1`，
使 `kywc.pc` 的 `Version` 与包版本一致，消费者用
`pkg-config --modversion kywc` 或版本下限时不会得到旧值。

## 补丁

### 0001 — meson 增加 libkywc_only / wayland_scanner_path / kywc_install_rpath

顶层 `meson.build` 在 `add_project_arguments('-DKYWC_VERSION=...')` 之后、
`wlroots = dependency(...)` 之前插入：

```meson
if get_option('libkywc_only')
  subdir('libkywc')
else
  ...上游原文（data/protocols/src/examples + kylin-wlcom）...
endif
```

`meson_options.txt` 增加三个选项：`libkywc_only`（boolean，默认 false，
上游行为不变）、`wayland_scanner_path`（string，默认空，空时仍走
`find_program('wayland-scanner')`）与 `kywc_install_rpath`（string，默认空，
下节说明）。

### 0002 — libkywc 本地生成协议 + 去掉版本化 .so

合成器构建里，四个协议代码由 `protocols/meson.build` 生成，`libkywc/`
通过 `protocols_code` / `protocols_client_header` 两个字典引用。
libkywc-only 模式不进入 `protocols/`，所以补丁在 `libkywc/meson.build`
里就地生成同样的四个文件：

| 协议 | XML |
|---|---|
| kywc-capture-manager-v1 | protocols/kywc-capture-v1.xml |
| kywc-output-manager-v1 | protocols/kywc-output-v1.xml |
| kywc-toplevel-manager-v1 | protocols/kywc-toplevel-v1.xml |
| kywc-workspace-manager-v1 | protocols/kywc-workspace-v1.xml |

输出落在 `libkywc/` 构建目录（Meson 自动把它放进该目标的 include 路径），
文件名与源码里的 `#include "kywc-*-v1-client-protocol.h"` 完全对应。

同一补丁去掉 `shared_library(..., version: meson.project_version())`：
版本参数会生成 `libkywc.so.1.3.1` 与 `libkywc.so` 软链，HMDFS 用户卷上
创建软链报 EPERM。去掉后只有 `libkywc.so` 一个实体文件，与已发布 OHOS
库的形态一致。同一处顺手把目标的 `install_rpath` 接到
`kywc_install_rpath` 选项（默认空，上游行为不变），原因见下节：加载
.so 同样会校验 `.codesign` 段。

补丁为纯 unified diff（`--- a/…` / `+++ b/…` 两行头，无 `diff --git`），
strip=0（conan 2.29 patch 引擎默认，patch_ng 自动剥 `a/`/`b/` 前缀），
hunk 行号对应 tarball 原文（0002 在 0001 之后应用，行号按前序补丁后的
状态计算）。

## 依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| wayland | 1.22.0 | `dependency('wayland-client')`；与 qtbase/qtwayland/kwayland 的钉版一致，避免图冲突 |
| libffi | 3.4.4 | `wayland-client.pc` 的 `Requires.private`；pkg-config 解析 `--cflags` 时需要其 .pc，故提升为直接依赖（chayang/hyprpicker 先例） |
| meson | 1.11.0（tool_requires） | 设备无系统 meson |

不需要 wayland-protocols：本包只用仓库内自带的四个 kywc 协议 XML。

## 静态 wayland-scanner

制品仓 wayland 包里的 scanner 在设备上无法执行：它的 DT_NEEDED 固化了
构建机 Conan 缓存里 libexpat 的绝对路径，execve 返回 EPERM。按 chayang
先例，从 wayland 1.22.0 源码自编一个 `-static` 的 scanner（只依赖
libc/expat）：

- `config.h` / `wayland-version.h` 手工生成，`wayland.dtd.h` 由上游
  `embed.py` 生成
- 编译 `src/scanner.c` + `src/wayland-util.c`，链接
  `/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`
- 产物放在 generators 目录，绝对路径经 `wayland_scanner_path` 选项传给
  `find_program()`

## kywc.pc

`meson install` 以 `--prefix=/ --destdir=<package_folder>` 执行，生成的
`kywc.pc` 里 `prefix=/`，`-I${includedir}` 会解析到 `/include`。package()
在安装后把 `prefix` 改写为 `${pcfiledir}/../..`，使 .pc 完全可重定位。
`Name: kywc`、`Version: 1.3.1`（由 0001 对齐）、`Libs: -L${libdir} -lkywc`
保持不变。

## 安装期 rpath 清除与 ELF 签名

OHOS 加载器在 dlopen 时同样校验 ELF 的 `.codesign` 段：链接之后的任何
字节改动都会让签名失效，加载返回 EACCES（dlerror 文本只有
"Permission denied"，容易误判成权限或沙箱问题）。

meson 会把 pkg-config 的 `-lwayland-client` 解析成
`<wayland 包>/lib/libwayland-client.so` 绝对路径再链接（
`mesonbuild/dependencies/pkgconfig.py` 的既定行为，为了能算 rpath），
所以链接命令带 `-Wl,-rpath,<wayland 包>/lib`。`meson install` 时
depfixer 把该目录当作构建期 rpath：默认 install_rpath 为空，于是删除
DT_RUNPATH 条目、并把 rpath 字符串原地填成等长 `X`——文件被改写，
`.codesign` 失效，包内 `libkywc.so` 无法加载。构建目录里的原件可以
加载，是定位这个问题的抓手。

配方在 generate() 里把 `kywc_install_rpath` 设为该 wayland 包的 lib
目录，即 depfixer 本来要删除的同一字符串：old == new，depfixer 把同样
的字节写回原处，安装产物与带签名的构建产物逐字节一致。真机上直接用
depfixer 验证过：new == old 时 sha256 不变（a2f47e07…），new 为空时
变为 0992b335…（正是失败包内文件的哈希）。

## 上游测试

全树递归检查（`grep "test(" --include=meson.build`）命中 0 处，也没有
tests 目录或 benchmark——上游没有测试套件。build() 末尾仍以
`meson test -C <build 目录>` 执行，日志留下权威计数
（`No tests defined.`）；退出码非 0 时构建直接失败（不降级为
warning），避免测试配置坏掉而包照发。运行时验证由 test_package 的
消费者测试承担：真机起进程内 Wayland 服务端，逐项调用 libkywc 公开
API，逐例打印 CHECK PASS/FAIL 与 TEST SUMMARY，任一失败整体退出非 0。

## 真机验证

2026-10-20 在 HarmonyOS PC（aarch64，os.version 6.0，clang 15）上执行
`python3 scripts/ohc-run.py conan-verify kywc 1.3.1`：

- G1 / G0 / G2 / G3 全部 PASS，报告 Verdict PASS
- `conan create` 内 test_package 真实执行：`TEST SUMMARY: 25 passed,
  0 failed`，含 global_remove 触发后的 fd 可读性与 kywc_context_process
  派发两项
- 包内 `lib/libkywc.so` 与构建目录带签名的产物 sha256 一致
  （`a2f47e07…`），确认 install 期的 rpath 处理没有改动 ELF

离线检视整改后同日复验（meson test 严格化、native-file 注入校验、
测试前置失败快停）：

- G0/G1/G2/G3/G4 与 L2/L4/L5 全部 PASS，报告 Verdict PASS
- `conan-create.log` 中 `RUN: meson test -C "<build-release 目录>"`
  之后输出 `No tests defined.`（退出码 0）；消费者测试
  `TEST SUMMARY: 25 passed, 0 failed`
- 包内 .so 与构建产物 sha256 仍完全一致（`a2f47e07…`，`cmp` 相同），
  证明改动不影响安装期 rpath 与 ELF 签名路径

第二轮离线检视整改后同日复验（事件循环退出由 eventfd 回调驱动、唤醒通道
改为硬前置、native/cross 两份 machine file 逐份注入 ar/ranlib）：

- G0/G1/G2/G3/G4 与 L2/L4/L5 全部 PASS，报告 Verdict PASS
- `conan_meson_native.ini` 的 `[binaries]` 实际含
  `ar = '/data/service/hnp/bin/llvm-ar'` 与
  `ranlib = '/data/service/hnp/bin/llvm-ranlib'`，注入逻辑确已执行
- `RUN: meson test -C "<build-release 目录>"` 之后输出 `No tests defined.`
  （退出码 0）；消费者测试 `TEST SUMMARY: 25 passed, 0 failed`，程序
  经回调终止事件循环后正常退出，pthread_join 未出现挂起
- 包内 .so 与构建产物 sha256 仍完全一致（`a2f47e07…`）
