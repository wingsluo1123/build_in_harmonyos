# xhk

xhk 是一个 Xlib 实现的「半键盘（HalfKeyboard）」解释器：以**空格键**作为修饰键，
把主键盘区另一半的按键镜像到当前手边，从而实现单手打字。上游作者 Kieran Bingham
在 2014 年肘部手术后为单手编码而编写并开源。

## 功能概述

- 按住空格键后，把对侧按键镜像为对应的另一侧按键（如 `f` ↔ `j`）
- `-m` mirror mode：所有按键反向映射
- `-d` 提高调试输出等级（可叠加）
- `-v` 打印版本、`-h` 打印用法、`-t` 运行内置 X 自检
- 基于 XInput2 枚举/识别本地键盘设备，基于 XTest 注入镜像按键事件
- 通过 `setpriority(PRIO_PROCESS, -20)` 提升实时性，保证按键响应

## 编译版本

- **1.2** (2026-10-15): HarmonyOS PC (aarch64) 适配版本

## OHOS 适配

- **构建系统**：上游 GNU autotools（`configure.ac` + `Makefile.am` + `src/Makefile.am`）。
  GitHub tag archive (`xhk-v1.2`) 不含预生成的 `configure`，配方在 `build()`
  先 `autoreconf -fi` 自举（同 `xsel/1.2.1`）。
- **依赖**：X11 头文件与库全部来自制品仓 conan 包，不依赖构建机本机 X11
  （CI worker / 设备均无系统 X11）。上游 `configure.ac` 的三个
  `PKG_CHECK_MODULES`（`x11>=1.6` / `xi>=1.6` / `xtst>=1`）对应的
  `x11.pc`/`xi.pc`/`xtst.pc` 由 `PkgConfigDeps` 生成。
- **版本线选择**：制品仓 X11 家族按 `.so` 主版本命名（`libX11.so.6.4.0` →
  `libx11/6.4.0`）。`libxtst/1.2.5` 自身 pin `libxi/6.1.0`，而 `libxi/1.8.3`
  属另一条线，两者不能同图；故统一取 6.x 线
  （`libx11/6.4.0` + `libxi/6.1.0` + `libxtst/1.2.5`），同 `xmacro`/`xclicker`。
- **签名**：OHOS 下对 `bin/xhk` 执行 `binary-sign-tool` 自签名（E549）。
- **已知限制（规则 7）**：OHOS 无 X server，xhk 的运行期功能（监听全局按键、
  XTest 注入）需要真实 X 环境，属真机验证范畴；headless 环境只做
  `-v`/`-h`/`-t` 与 ELF 平台属性的确定性验证。

## 依赖关系

- 编译/运行依赖：`libx11/6.4.0`、`libxi/6.1.0`、`libxtst/1.2.5`、`xorgproto/2025.1`
- 构建期工具：`automake/1.18`、`libtool/2.5.4`（autoreconf 自举）

## 参考资料

- 上游仓库：<https://github.com/kbingham/xhk>
- 上游文档：`doc/xhk.md`、man page `doc/xhk.1`
