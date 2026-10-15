# libXaw

libXaw 是 X.Org 的 **Athena Widgets** 工具包 —— X11 最经典的 widget 库，为
Xt Intrinsics 提供按钮、菜单、文本、面板等基础控件，是 xterm/xdu/xmix 等
传统 X11 客户端的 GUI 基础。

## 功能概述

- **两套 ABI**：`libXaw6`（旧 ABI，`-DOLDXAW`）与 `libXaw7`（现代默认，支持
  Xft/Tip/Tree 等新 widget）；同名 SONAME 分别为 `libXaw.so.6` / `libXaw.so.7`。
- **Widget 集合**：AsciiText、Box、Command、Dialog、Form、Label、List、Menu
  （SimpleMenu/Sme/SmeBSB/SmeLine/MenuButton）、Paned、Panner、Porthole、
  Repeater、Scrollbar、StripChart、Toggle、Tree、Viewport、Tip 等。
- **输入/转换**：`XawInitializeWidgetSet()` 注册 pixmap loader 与字符串/类型
  转换器；`XawInitializeDefaultConverters()`（仅 Xaw7）注册默认转换器表。
- **资源文件**：`X11/Xaw/*.h` 公共头 + `xaw6.pc` / `xaw7.pc` 两套 pkg-config。

## OHOS 适配

- **构建系统**：autotools（tarball 自带预生成 `configure`，无需 autoreconf）。
- **交叉 configure**：`/system/bin/sh <build>/configure-ohos --host=aarch64-linux-ohos
  --build=aarch64-unknown-linux-gnu`；显式交叉确保 autoconf 不 RUN conftest 二进制。
- **umask 补丁**：`configure` 中 `umask 077`→`022`（config.status 的
  `./confXXXXXX` 0700 临时目录在 HMFS 上写被拒，见 DRAFT-E565）。
- **libtool `.la` 重定位**：`generate()` 建立 build-local linker-view，把依赖
  `.la` 的 `libdir` 与 `dependency_libs` 改写为 view 内相对形式，`LDFLAGS=-L<view>`
  注给 configure；`package()` 删除 `libXaw6.la` / `libXaw7.la`。
- **pkg-config 模块名**：在消费侧把 libxmu 的组件 PC 覆写为上游模块名 `xmu`
  （另有 x11/xext/xpm 同理），使 `PKG_CHECK_MODULES(XAW*, ...)` 通过。
- **已知差异**：OHOS 无 X server 时库本身可正常链接/加载；真实渲染与需要 display
  的程序不在自动化测试范围内（CI worker 为 headless）。注意 1.0.14 上游 tarball
  并不包含 `examples/` 目录（1.0.16 才有）。
- **上游无自动化测试**：`make check` 为空操作；本仓用免 display 的 widget-set
  契约测试（`test_package/xaw{6,7}_contract.c`）验证两条 ABI 的符号与类名契约。

## 依赖关系

编译期（Conan）：

| 依赖 | 用途 |
|------|------|
| libx11 | Xlib 客户端库 + `Xlib.h` |
| libxt | Xt Intrinsics（`X11/Intrinsic.h`） |
| libxmu | Xmu 工具函数（XAW6/XAW7 都需要） |
| libxpm | XPM 图像（仅 XAW7） |
| libxext | X11 扩展（XShape 等） |
| xorgproto | xproto / xextproto 头 |

传递：libxau、libxcb、libxdmcp、xtrans、libsm、libice。

运行期：上述 `.so`（`libXaw.so.6` / `libXaw.so.7`）+ 运行中的 X server
（后者在 OHOS 上由已移植的 xorg-server 提供）。

## 参考资料

- 上游仓库：https://gitlab.freedesktop.org/xorg/lib/libxaw
- 官方发布：https://xorg.freedesktop.org/releases/individual/lib/
- 本仓版本：`1.0.14`（Debian/Ubuntu 现行版本）
