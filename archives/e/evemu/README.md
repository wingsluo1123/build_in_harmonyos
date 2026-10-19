# evemu

evemu（Event Emulator）是 freedesktop.org 维护的用户态输入事件工具集，提供 `libevemu`
库与一组命令行工具，用于在不编写内核驱动的前提下描述、录制与回放输入子系统
（`/dev/input/event*`）的事件流，常用于输入设备能力采集、evdev 调试与输入自动化测试。

## 功能概述

- **事件描述**：以人类可读的文本形式描述输入设备的能力位与支持的事件类型
- **事件录制**：把指定输入设备的事件流录制为 evemu 描述文件
- **事件回放**：通过 `/dev/uinput` 把描述文件回放成虚拟输入设备
- **库接口**：`libevemu` 提供 `evemu_new` / `evemu_read` / `evemu_write` /
  `evemu_play` / `evemu_get_name` / `evemu_set_name` / `evemu_delete` 等 C API

## 提供的命令行工具

| 命令 | 说明 |
|------|------|
| evemu-describe | 描述输入设备的能力与事件类型 |
| evemu-record | 录制输入设备的事件流 |
| evemu-play | 将描述文件回放为虚拟输入设备 |
| evemu-device | 依据描述文件创建虚拟输入设备 |
| evemu-event | 向输入设备注入单个事件 |

## 依赖关系

- 编译依赖：`libevdev >= 1.2.99.902`（`configure.ac` 中 `PKG_CHECK_MODULES` 硬依赖）
- 构建系统：GNU Autotools（发布归档自带 `configure`，无需 `autoreconf`）

## HarmonyOS 适配要点

- 显式钉死 `--build` / `--host` 三元组，避免调用发布归档中 2012 年快照的
  `config.guess`（该快照不识别本平台，且其临时目录策略在本平台会因属主/权限错位失败）
- `generate()` 阶段需把依赖库目录注入 `LD_LIBRARY_PATH`，否则 `configure` 自带的
  `conftest` 会因找不到 `libevdev.so.2` 而报 `cannot run C compiled programs`
- 使用上游自带开关 `--disable-python-bindings` 关闭 Python 绑定：automake 的
  `py-compile` 依赖已从 Python 3.12 移除的 `imp` 模块，且 `AM_PATH_PYTHON` 会把模块
  解析到前缀之外的路径；`libevemu` 与 5 个命令行工具不受影响
- 两条 portability 补丁以 ISO C / POSIX 等价实现替换 glibc 专属符号
  （`versionsort`、`program_invocation_short_name`），不引入平台条件宏
- 运行期打开 `/dev/input/*` 与 `/dev/uinput` 需要相应权限；测试进程不具备该权限时，
  测试面收窄到「信息面 + 设备无关 API」，并在交付说明中如实披露功能面未实测

## 版本

- 2.7.0（built，2026-10-09）

## 许可证

LGPL-3.0-or-later

## 参考资料

- 项目主页：https://www.freedesktop.org/wiki/Evemu/
- 源码归档（现行，2026-10-16 换宿主）：https://gitlab.freedesktop.org/libevdev/evemu/-/archive/v2.7.0/evemu-v2.7.0.tar.gz
