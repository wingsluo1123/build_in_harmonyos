# SysTray-X

## 简介

SysTray-X 是 Thunderbird 邮件客户端的系统托盘伴侣程序。Thunderbird 扩展（WebExtension）负责监听新邮件与未读数，原生 Qt 应用通过 X11 在桌面托盘显示图标、未读计数与快捷操作菜单。

- 项目地址: https://github.com/Ximi1970/systray-x
- 许可证: MPL-2.0
- 构建系统: qmake（Qt5 `.pro` / `.pri`）

## OHOS 适配

- 上游在 Qt5 分支依赖 `QT += x11extras`（Qt5X11Extras 模块）获取 `QX11Info::display()`；OHOS 的 qt 包不含该模块，改为直接调用 `XOpenDisplay(NULL)`，只依赖 libX11
- 上游 KDE 集成分支依赖 KNotifications/KStatusNotifierItem；OHOS 无 KDE Frameworks，构建时定义 `NO_KDE_INTEGRATION` 走 X11 托盘路径
- OHOS 的 `ld.lld` 不读取 `LIBRARY_PATH` 环境变量，必须在 `.pro` 文件中显式追加 `LIBS += -L...`，否则链接阶段报 `unable to find library -lX11`
- `X11/Xlib.h` 引用的 `X11/X.h` 来自 xorgproto，需要通过 `QMAKE_INCDIR` 或 `CPATH` 把 xorgproto 的 include 目录传给编译器
- 源码 tarball 不含 git 仓库，`.pri` 里的 `git describe` 版本探测会失败，构建时以固定版本字符串替代

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt | 5.15.19.1 | Widgets/Gui/Core，提供 qmake 与 harmonyos-clang mkspec |
| libx11 | 1.8.13.1 | X11 客户端库，托盘与窗口操作 |
| libxcb | 1.17.0.1 | X11 协议底层传输 |
| xorgproto | 2025.1 | X11 协议头文件（`X11/X.h` 等） |

## 功能验证

```bash
# 二进制形态与加载闭包
file bin/SysTray-X
python3 test_ohos_closure.py bin/SysTray-X
```

`test_ohos_closure.py` 为鸿蒙特有消费者测试：解析 ELF64 动态段，输出架构与 `DT_NEEDED` 清单，确认 `libX11.so.6`、`libQt5Widgets.so.5`、`libc++_shared.so` 等依赖形成完整加载闭包。该测试只报告不抛断言。

## 运行说明

SysTray-X 是 GUI/X11 应用，需要可用的 X11 DISPLAY 与 Thunderbird 扩展配合，无法在无头 CI 中做交互式冒烟验证；CI 中仅验证二进制可加载性。

## 参考

- 上游仓库: https://github.com/Ximi1970/systray-x
- Thunderbird 扩展: https://addons.thunderbird.net/thunderbird/addon/systray-x/
