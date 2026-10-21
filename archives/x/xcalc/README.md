# xcalc

xcalc 是 X.Org 官方发布的 X11 科学计算器（Athena/Xaw 小程序）：用
Xaw Form/Label/Command/Toggle 控件绘制计算器界面，支持中缀与 RPN
（HP 风格）两种输入模式。本仓库提供其在 HarmonyOS PC (aarch64) 上的
Conan 配方。

## 官网

https://gitlab.freedesktop.org/xorg/app/xcalc

## 许可证

X11（X Consortium 许可，见源码包 COPYING）

## 功能概述

- 四则运算与科学函数（三角/对数/指数等，见 `math.c`）
- 中缀与 RPN 两种模式（`-rpn` 选项 / `XCalc` 资源）
- 反色（LCD）与背景点画（`-stipple`）显示选项
- 计算结果可通过 X selection 复制（PRIMARY 选择）
- `-version` / `-help` 无需 X server 即可运行（供无头验证）

## OHOS 适配

- 构建系统：autotools（tarball 自带预生成 `configure` / `Makefile.in`，
  无需 autoreconf），原生 build=host（不使用 `--build/--host/--target`）。
- `config.guess`（2024-07-27）不识别 `uname -s HarmonyOS`，且对 `Linux|GNU`
  分支用编译探针写 `$TMPDIR`（HMFS 上失败）→ 补丁 0001 教它输出
  `aarch64-unknown-linux-ohos`，并把临时目录 umask 放宽为 022。tarball 自带
  `config.sub`（2024-05-27）已接受 `ohos*`/`linux-ohos*`，无需 config.sub 补丁。
- HMDFS 下 conan 缓存父目录对 `getcwd()` 不可达，autoconf 2.72 生成的
  `configure` 顶部严格 `pwd` 判定会 abort；`config.status` 用 `umask 077`
  创建 `./confXXXXXX` 临时目录在 HMFS 上不可写 → 补丁 0002 加 `$PWD` 回退
  并放宽 umask（E011/E114）。
- `PKG_CHECK_MODULES(XCALC, [xaw7 xt x11 xproto >= 7.0.22])` 通过
  `PkgConfigDeps` 生成的 `.pc` 满足；`libxmu` 组件名与 `xorgproto` 在消费端
  重命名为 `xmu` / `xproto`。
- `app-defaults` 安装目录由 `--with-appdefaultdir=/share/X11/app-defaults`
  固定（conan `xt.pc` 无 `appdefaultdir` 变量，自动探测为空会装到 `/`）。
- 无 X server 环境（CI/真机无 X）下仅验证 `-version`/`-help` 路径
  （与 xfontsel 1.1.2、xterm 410 同款处理）。

## 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| libxaw | 1.0.14 | X Athena Widgets（组件 xaw7），提供 xaw7.pc 与 Xaw 头 |
| libxt | 1.3.1 | Xt Intrinsics（`XtAppInitialize`），提供 xt.pc |
| libx11 | 1.8.13 | Xlib 核心库，提供 x11.pc |
| libxext | 6.4.0.1 | X11 扩展库（libxaw 传递链） |
| libxmu | 1.3.1.1 | Xmu 工具库（libxaw 传递链） |
| xorgproto | 2025.1 | X11 协议头（提供 xproto.pc） |
| libxcb / libxau / libxdmcp | 1.17.0 / 1.0.11 / 1.1.5 | libX11 运行时闭合（run 依赖，仅供 test_package） |

编译期与运行期依赖均来自 ohpcd 已发布的 OHOS/armv8/clang15 制品
（libxmu/libxpm/libice/libsm 由 libxaw 传递引入）。

## 参考资料

- 官网 / 源码：https://gitlab.freedesktop.org/xorg/app/xcalc
- 发布归档：https://xorg.freedesktop.org/archive/individual/app/
