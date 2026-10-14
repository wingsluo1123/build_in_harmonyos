# laptop-mode-tools 1.74 适配笔记（HarmonyOS PC · 纯 POSIX sh 脚本应用）

## 定位
- laptop-mode-tools 是笔记本电源管理工具集：`laptop_mode` CLI（usr/sbin）+
  33 个电源模块（usr/share/laptop-mode-tools/modules）+ module-helpers +
  etc/laptop-mode 配置（laptop-mode.conf + conf.d/31 个模块配置）+ 5 个 man8 页。
- **纯 POSIX sh 脚本集合，无任何编译产物** → 走脚本打包路径（build_system: none）。
  上游 Makefile 仅 default/clean/version/install 四个 target，install 只执行
  `./install.sh`（DESTDIR/INIT_D/MAN_D/INSTALL/ACPI/APM/PMU/SYSTEMD 等全环境变量驱动）。

## 关键适配（3 个最小 patch，均环境变量驱动、不改变上游默认行为）

### 0001 install.sh 组件门禁
- 新增 `INSTALL_GUI`/`INSTALL_UDEV`/`INSTALL_PM_UTILS` 三个环境变量（默认 "yes"，
  与上游行为一致）；设 "no" 时跳过 polkit/GUI（desktop、lmt.py、lmt-config-gui、
  polkit action）、udev（99-laptop-mode.rules、lmt-udev）、pm-utils（sleep.d hook）。
- OHOS 无 udev/无 systemd/无 pm-utils/无 polkit+PyQt5 GUI，全部关闭。
  init.d（INIT_D=none）、systemd（SYSTEMD=no）、acpi/apm/pmu（=disabled）用上游
  既有开关，无需 patch。

### 0002 laptop_mode 运行时可移植性
- `laptop_mode` 顶部要求 `flock`（设备 /usr/bin/flock 有），锁文件在
  /var/lock —— **设备无 /var/lock、无 /var/run，/tmp 只读**，`exec 8>/var/lock/...`
  在 toybox sh 下直接终止脚本。patch 引入 `LMT_LOCK_DIR`（默认 /var/lock），
  不可写时自动回退 /tmp/laptop-mode-tools-locks → $HOME/.lmt-locks；
  状态目录引入 `LMT_RUN_DIR`（默认 /var/run/laptop-mode-tools）。
- 命令分发（status/help/version）位于 `lmt_load_config()` **之内、配置加载之后**，
  上游缺 /etc/laptop-mode/laptop-mode.conf 时 `--version` 直接 exit 1。
  patch 增加 version/help 分支免配置运行（DEBUG=0/VERBOSE_OUTPUT=0）。
- 状态目录写入（mkdir/touch/state echo）改为非致命（2>/dev/null）。

### 0003 conf.d 模块默认值
- 设备实测缺失的外部工具：hdparm、udevadm、iw、iwconfig、ethtool、mii-tool、
  xset、setterm、hal-*。上游 `ENABLE_AUTO_MODULES=1` 会激活所有 `=auto` 模块。
  patch 将依赖缺失工具的模块默认置 0：laptop-mode.conf 的 CONTROL_HD_POWERMGMT
  （hdparm/udevadm）、runtime-pm（sysfs autosuspend）、dpms-standby（xset）、
  terminal-blanking（setterm）、wireless-power/wireless-ipw-power/
  wireless-iwl-power（iw/iwconfig）、hal-polling（HAL）。ethernet/bluetooth
  上游默认已关闭，未动。

## build()/package() 流程
1. `bash -n` 全量语法检查（3 个 sbin 脚本 + 33 模块 + helpers + install.sh）。
2. patched install.sh DESTDIR staging：INIT_D=none、MAN_D=/usr/share/man、
   SYSTEMD=no、ACPI/APM/PMU=disabled、INSTALL_GUI/INSTALL_UDEV/INSTALL_PM_UTILS=no、
   INSTALL=busybox install（OHOS worker 无 coreutils install；有 DESTDIR 跳过
   root/whoami 检查，INIT_D=none 跳过 which invoke-rc.d）。
3. staging 清单校验：33 模块、>=2 helpers、31 conf.d、man8、且
   etc/init.d、lib/udev、lib/systemd、usr/lib/pm-utils、usr/share/polkit-1 必须不存在。
4. 冒烟：staged laptop_mode --version 输出 "Laptop Mode Tools 1.74"。
5. package：staged 树原样打包 + usr/sbin/* 另行暴露到 bin/（Conan CLI 消费者、
   CI L2 直跑）+ COPYING licenses/ + README.md。

## 设备实测（2026-09-26）
- /proc/sys/vm/laptop_mode 不存在（内核未启用 VM laptop_mode sysctl）→ 核心功能
  真机受限，脚本可运行但调权写节点会失败（非致命，log ERR 继续）。
- /sys/class/power_supply 存在但当前用户无读权限 → 电源状态探测回退"假定 AC"。
- `--version`/`--help`（patched）真机通过；toybox sh 与 hnp bash 均可解释。

## 风险点
| # | 风险 | 处置 |
|---|------|------|
| 1 | /var/lock、/var/run 缺失，/tmp 只读 | 0002 patch 锁目录自动回退 + LMT_LOCK_DIR/LMT_RUN_DIR 可覆盖；状态写入非致命 |
| 2 | /proc/sys/vm/laptop_mode 不存在 | 内核层面限制，脚本报错但继续；核心调权功能需内核启用后真机验证 |
| 3 | 事件驱动（udev/ACPI 事件）不可用 | 组件不打包；仅 CLI 手动/timer 触发 |
| 4 | hnp bash 在部分上下文 getcwd 失败 | 测试/冒烟显式传 PWD；脚本默认 /bin/sh(toybox) 不受影响 |

## 上游测试 discovery（NO_UPSTREAM_TESTS）

- **discovery.status**: EVIDENCE_COMPLETE
- **结论**: 上游（rickysarraf/laptop-mode-tools，tag 1.74 与官方 release 资产）不提供任何测试套件，无可运行的官方测试。
- **已检查入口/证据**:
  1. 官方 release 资产 laptop-mode-tools_1.74.tar.gz 全量文件清单（144 个条目（113 个文件 + 31 个目录））：无 tests/、无 test 目录、无 CI workflow（.github/ 下仅 ISSUE_TEMPLATE/laptop-mode-tools-bug-report.md）。
  2. Makefile 全部 target 实读：default（提示文本）、clean（空）、version、install（仅 ./install.sh）——无 check/test 目标。
  3. release-checklist 文件为发布手工步骤，非测试。
  4. Scout 独立实证：grep 仓库与归档无 CI yml/yaml（命中仅为 pcie-aspm.conf 误匹配）。
- **替代验证（已实际执行）**: `bash -n` 全量语法检查 + staged `laptop_mode --version`
  冒烟（VERSION 硬编码 LMTVERSION=1.74）+ test_package 11 项消费者断言。
- **证据路径**: 本机 `D:/ohos_zcode/runs-v2/laptop-mode-tools-1.74/`
  （scout-notes.md、laptop-mode-tools_1.74.tar.gz、all-scripts.txt）；
  设备 `/storage/Users/currentUser/tmp/oh-device-porting-v2/laptop-mode-tools-1.74/`
  （SHA256=a1c53b82c7660b1feff9f7e42525c91f8d991e5388d6260df52d9b55b471cc4a，
  本机与设备两次独立 sha256sum 一致）。

## 编译步骤

```bash
conan create archives/l/laptop-mode-tools/1.74 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 配方内 build()：bash -n 全量语法检查 → install.sh DESTDIR staging →
# 清单校验 → laptop_mode --version 冒烟
```
