# pd-hid — Pure Data USB HID 对象

`pd-hid` 提供 Pure Data（Pd）对象 **[hid]**，用于读取 USB HID 设备（键盘、
鼠标、摇杆、手柄、游戏板以及各种旋钮/触摸屏/红外遥控等）。随包附带 29 个抽象
（`mouse`、`keyboard`、`joystick`、`hid_polar`、`hid_smooth` 等）。

## 用法

```sh
pd -path <pkg>/lib/pd-externals        # 把外部对象/抽象目录加入搜索路径
# 在补丁中使用 [hid]，或 [joystick]、[mouse] 等抽象
```

## 平台后端与依赖

- Linux：`hid_linux.c` 使用 Linux evdev 接口（`<linux/input.h>`、
  `/dev/input/event*`），**不依赖 libhidapi**。OHOS sysroot 自带该头。
- macOS：`hid_darwin.c` 使用 Apple HID Utilities（不构建）。

因此本包**无三方依赖**。运行真实设备读取需要真机 HID 硬件。

## OHOS 适配要点

- 上游使用**老式 Pd library template Makefile**，Linux 走专门的 `hid.pd_linux` 规则。
- `puredata/0.54.1`（application）**不暴露** `m_pd.h`：配方在 `source()` 额外拉取
  `pure-data 0.54-1` 源码树，并把 `-I` 指向其 `src`。
- 模板用 `uname -s` 判平台；OHOS 报 `HarmonyOS`，故在命令行强制 `UNAME=Linux`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/hid.pd_linux` | [hid] 外部对象 |
| `lib/pd-externals/*.pd` | 抽象与帮助补丁 |

## 参考资料

- 上游：<https://puredata.info>
- 许可证：GPL-2.0-or-later
