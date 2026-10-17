# sispmctl

## 一句话描述
控制 GEMBIRD (m)SiS-PM 系列 USB 电源插座（排插）的命令行工具：开关插座、
查询状态、定时规划、设置蜂鸣器，并自带 Web 管理界面。

## 功能概述
- `-o/-f/-t` 开关/切换指定插座的电源
- `-g/-m` 查询插座状态与电源状态
- `-s` 扫描所连接的 GEMBIRD SiS-PM 设备
- `-a/-A` 查看/设置插座定时规划（schedule）
- `-b` 开关内置蜂鸣器
- `-v/-h` 打印版本与帮助
- Web 管理界面（三套皮肤）

## OHOS 适配
- 依赖 **libusb-0.1 API**（`usb.h` / `-lusb`），由 `libusb-compat/0.1.7` 提供；
  configure 的 `PKG_CHECK_MODULES(LIBUSB, libusb >= 0.1.11)` 因 libusb-compat
  生成的 `libusb.pc` 版本为 0.1.7 而无法通过，配方在 `generate()` 中注入
  一个报告上游 libusb-0.1 API 版本 **0.1.12** 的 pc shim（并同时链接
  `-lusb-1.0` 以完成静态传递链）。
- `admin/config.guess`、`admin/config.sub` 需补充 `aarch64-unknown-linux-ohos`
  识别（配方 build() 内完成）。
- 预生成的 `configure` 经 bash 直跑，`config.status` umask 077→022，
  并预建 `.libs/.deps` 目录。
- 实际插座控制功能依赖物理 GEMBIRD USB 设备；真机/CI 无此硬件，消费者测试
  只覆盖纯库 API（schedule 往返）与二进制 `-v` 版本路径。

## 依赖关系
- 编译/运行依赖：`libusb-compat/0.1.7`（→ `libusb/1.0.27`）

## 参考资料
- 官网：https://sispmctl.sourceforge.net/
- 上游源码：https://sourceforge.net/projects/sispmctl/
