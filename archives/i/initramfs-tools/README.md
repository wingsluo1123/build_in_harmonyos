# initramfs-tools

## 软件描述
`initramfs-tools` 是 Debian 的 **initramfs 构建工具集**：把内核模块、固件、脚本按配置打包成 initramfs（早期用户空间），并按内核版本维护/更新，同时提供解包与查看工具。主要产物为 shell 工具 + 一个 C 程序，GPL-2.0-or-later。

## 功能概述
| 产物 | 作用 |
|---|---|
| `mkinitramfs` | 生成 initramfs 镜像（**由源码模板经 `@VERSION@`/`@BUSYBOX_PACKAGES@` 替换而成**） |
| `update-initramfs` | 按内核版本更新/删除已生成的 initramfs |
| `lsinitramfs` | 列出 initramfs 内容 |
| `unmkinitramfs` | 解包 initramfs（本包唯一的编译产物，C） |
| `share/initramfs-tools/{hooks,scripts,hook-functions,init}` | initramfs 构建期的 hooks 与启动脚本框架 |
| `etc/initramfs-tools/{initramfs.conf,update-initramfs.conf}` | 主配置与更新配置 |
| `share/bash-completion/completions/initramfs-tools/` | bash 补全脚本 |

## OHOS 适配

### 打包方式
- **Debian native 包**（无独立上游仓库）：不跑 dh（OHOS 无 dh/debhelper），按 `debian/initramfs-tools*.install` 的映射直接安装
- **Makefile 极简**：`all: unmkinitramfs`（隐式规则 + `$(CC)`）→ 只需把交叉工具链的 `CC/CFLAGS` 放进环境（配方的 `generate()` 用 `AutotoolsToolchain`）
- **占位符替换**：`mkinitramfs` 是模板，按 Debian `override_dh_install` 的做法替换 `@VERSION@`（本包 0.151）与 `@BUSYBOX_PACKAGES@`

### 关键攻坚点
1. **模板化脚本**：直接原样打包会把占位符带进产物 → 配方做替换 + 消费者校验断言"无残留且含版本号"
2. **测试框架属"测试专用依赖"**：Build-Depends 里的 `shunit2 <!nocheck>` 仓库/制品仓都没有，但它不是运行期/构建期必需 → 按"缺环境就下"在 build() 内取（**钉真实 sha256**）仅用于跑上游 `tests/functions_test`（6 个用例），**不进产物**
3. **产物分布广**：`bin/`+`sbin/`+`etc/`+`share/initramfs-tools/`+`share/bash-completion/`+`share/man/`+`share/bug/` 都要按清单装齐
4. **零 Conan 依赖**：Build-Depends 的三项都不是"外部库/工具缺口"，Depends 是同源子包

### 与 Linux 的差异
- 脚本层跨平台（POSIX sh）；差异集中在**打包方式**（不跑 dh、照抄 install 映射 + 模板替换）
- 唯一编译产物 `unmkinitramfs` 用交叉工具链正常编译（消费者校验里核对 64 位 AArch64 ELF）

## 依赖关系
- **Conan requires**：无
- **测试框架**（仅 build 期）：`shunit2 2.1.8`（Debian orig tarball，sha256 `b2fed28b…`，不进产物）
- **运行期**：`/bin/sh`；`initramfs-tools-core` 等同源子包（不在本包依赖范围内）

## 版本记录
| 版本 | 状态 | 打包日期 | 备注 |
|------|------|---------|------|
| 0.151 | built | 2026-10-08 | Debian native 包范式 + mkinitramfs 模板替换 + 上游 tests/functions_test（shunit2）真跑 |

## 参考资料
- Debian 包页: https://tracker.debian.org/pkg/initramfs-tools
- 上游（Debian salsa）: https://salsa.debian.org/kernel-team/initramfs-tools
