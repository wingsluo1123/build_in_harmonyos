# laptop-mode-tools

笔记本电源管理工具集（laptop_mode CLI + 33 个纯 shell 电源模块）。纯 POSIX sh
脚本应用，无编译产物。

- 上游：https://github.com/rickysarraf/laptop-mode-tools
- License：GPL-2.0-only
- 版本目录：1.74/

## OHOS 适配要点
- install.sh 环境变量门禁（INSTALL_GUI/INSTALL_UDEV/INSTALL_PM_UTILS），
  udev/systemd/init.d/acpi/apm/pm-utils/polkit/GUI 集成在 OHOS 全部排除。
- laptop_mode 运行时可移植：LMT_LOCK_DIR/LMT_RUN_DIR 可覆盖且不可写时自动回退；
  version/help 免配置运行。
- conf.d 默认关闭依赖缺失工具（hdparm/udevadm/iw/xset/setterm/HAL）的模块。

运行时注意：`/proc/sys/vm/laptop_mode` 需内核启用；事件驱动集成（udev/ACPI）
不可用，仅 CLI 手动触发。详见 1.74/notes.md。
