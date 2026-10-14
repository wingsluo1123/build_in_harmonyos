# pd-hid 0.7 适配笔记

## 上游构成

`pd-hid_0.7.orig.tar.gz` 是 Hans-Christoph Steiner 的 Pure Data USB HID 对象
**[hid]**，可读取键盘、鼠标、摇杆、手柄、游戏板等 USB HID 设备。仓库还附带 29 个
`.pd` 抽象（`mouse`/`keyboard`/`joystick`/`hid_polar` 等）与帮助补丁。

## 平台后端与依赖

上游是**按平台分文件**的实现：

- Linux：`hid_linux.c` 直接使用 **Linux evdev 接口**（`<linux/input.h>` 与
  `/dev/input/event*`），**不依赖 libhidapi**；
- macOS：`hid_darwin.c` 使用 Apple HID Utilities 框架（本次不构建）。

因此本配方**不需要三方依赖**。平台任务里标注的 `hidapi` 依赖并非 0.7 版上游
源码所需——上游从 2011 年至今的 Linux 后端始终走 evdev。OHOS sysroot 已自带
`<linux/input.h>`，编译直接通过。

> 说明：若强行引入 `hidapi` 而不改上游源码，链接器会因无引用而将其丢弃，
> 属于无效依赖，故本配方按事实不声明。

## 构建

- **Pd API 头**：制品仓 `puredata/0.54.1` 是 *application*，不暴露 `m_pd.h`；
  配方在 `source()` 额外拉取同版本 `pure-data 0.54-1` 源码树，`-I` 指向其 `src`。
- **平台识别**：老式模板用 `uname -s`；OHOS 报 `HarmonyOS`，故 `make` 命令行强制
  `UNAME=Linux`（模板对 Linux 有专门的 `hid.pd_linux: hid.o input_arrays.o
  hid_linux.o` 规则）。
- `CFLAGS` 在命令行整体给出：`-I<pd-api>/src -DPD -fPIC -O2 -w`。
- 构建产出 **1** 个 `.pd_linux`（`hid`）。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/hid.pd_linux` | [hid] 外部对象 |
| `lib/pd-externals/*.pd` | 29 个抽象 + 帮助补丁 |
| `lib/pd-externals/hid-meta.pd` | 库元数据 |

## 测试

上游无自动化测试套件（只有帮助补丁/抽象）→ 上游 N=0。

消费者测试 `test_package/test_pd_hid.sh`（2 项断言）用**真机 OHOS `pd`** 无头加载
安装后的 `[hid]`。**运行真实设备读取需要真机硬件**（`/dev/input/event*`），本测试
覆盖**类加载 + 无头实例化**：`[hid]` 在首个实例创建时会 `post` 确定性的版本横幅：

- `[hid] 0.7, written by Hans-Christoph Steiner <hans@eds.org>`
- `compiled on <date> at <time>`

真机 `conan create`：`CREATE_RC=0`，消费者 2/2。
