# installation-report

## 软件描述
`installation-report` 是 Debian 的**安装报告工具集**：在 Debian 安装器（d-i）或已装好的系统里收集硬件与安装日志信息，生成可提交给 Debian 的安装报告（install-report）。纯 POSIX shell 脚本，GPL-2.0-or-later。

## 功能概述
| 产物 | 作用 |
|---|---|
| `report-hw` | 硬件探测报告：读取 `/proc`、`/sys` 与可选工具（`lspci`/`lsusb`/`dmidecode`），对**命令缺失或异常自行降级** |
| `usb-list` | 列出系统中的 USB 设备（基于 `/sys/bus/usb`，源自 Greg KH 的 usb-devices 脚本） |
| `httpd` | 极简 Web 服务器（默认 `PORT=80`、`DOCROOT=/var/log`），供安装器把日志通过 HTTP 取走 |
| `pre-pkgsel.d/50save-logs`、`finish-install.d/94save-logs` | 安装器钩子：在选包阶段与安装收尾阶段保存日志 |
| `bug/installation-report/{control,script}`、`bug/installation-reports/script` | 让 `reportbug` 能自动附带安装器日志 |
| `install-report.template` | debconf 模板数据（同时被 `installation-report` 与 `save-logs` 两处引用） |
| `report-hw.1` | man 页 |

## OHOS 适配

### 打包方式
- **Debian native 包**（无独立上游仓库）：源码 = 顶层脚本 + `debian/`（含 `debian/po/` 的多语言模板），`debian/rules` 只有 `%: dh $@`
- **不跑 dh**（OHOS 无 dh/debhelper）：按 `debian/*.install`、`*.manpages`、`*.links` 声明的映射直接安装产物（与同族 `init-system-helpers` 同一做法）
- **零 Conan 依赖**：脚本只用 `/bin/sh`；`lspci`/`lsusb`/`dmidecode` 是脚本内可选调用

### 关键攻坚点
1. **产物映射分散且跨清单**：同一数据文件 `install-report.template` 被 `installation-report.install` 与 `save-logs.install` 分别装到 `share/installation-report/` 与 `share/save-logs/`；`bug/` 子树要保留层级装到 `share/bug/`；安装器钩子落在 `lib/pre-pkgsel.d`、`lib/finish-install.d`
2. **软链也要还原**：`debian/installation-report.links` 要求 `share/doc/installation-report/install-report.template` 指向 `../../installation-report/install-report.template`，属产物的一部分
3. **上游无测试**：如实记 N/A（附清点证据），构建期以 `sh -n` 语法检查兜底，验证主要放在消费者校验
4. **消费者校验的 SKIP 口径**：只有**具名环境信号**（超时/无执行权限/权限拒绝）才 SKIP；`httpd` 因默认绑特权端口 `:80` **按设计不跑**并明确说明，避免把环境限制记成缺陷、也避免把缺陷放行

### 与 Linux 的差异
- 脚本跨平台（POSIX sh + `/proc`/`/sys` 读取）；差异集中在**打包方式**（不跑 dh、照抄 install/links 映射）与**校验口径**（具名信号才 SKIP）
- 脚本在宿主可真正执行：消费者校验里 `usb-list`/`report-hw` 真跑通过（`httpd` 除外，见上）

## 依赖关系
- **Conan requires**：无
- **运行期**：`/bin/sh`（系统自带）；`lspci`/`lsusb`/`dmidecode` 为**可选**（缺失时 `report-hw` 自动降级）

## 版本记录
| 版本 | 状态 | 打包日期 | 备注 |
|------|------|---------|------|
| 2.98 | built | 2026-10-08 | Debian native 脚本包范式（不跑 dh + 照抄 install/links 映射）；上游无测试记 N/A |

## 参考资料
- 上游（Debian salsa）: https://salsa.debian.org/installer-team/installation-report
- Debian 包页: https://tracker.debian.org/pkg/installation-report
