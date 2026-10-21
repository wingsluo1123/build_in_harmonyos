# libuser

用户与组账户管理的标准化接口库（libuser）及 `luseradd`/`lusermod`/`lgroupadd` 等账户命令行工具。

- 上游：https://pagure.io/libuser/
- 版本源：Debian 快照 `0.64+git20241106~dfsg`（上游 git 2024-11-06 + dfsg 重打包）
- 许可证：LGPL-2.0-or-later
- 类型：库 + 命令行工具（产物含 `bin/luseradd` 等 12 个账户工具）

## 功能概述

- `libuser.so`：`lu_start`/`lu_user_add`/`lu_group_add`/`lu_user_lookup_name` 等账户管理 API（见 `libuser/user.h`）
- 后端模块：`files` / `shadow`（`lib/libuser/` 下的 dlopen 插件）
- CLI：`luseradd`、`lusermod`、`luserdel`、`lgroupadd`、`lgroupmod`、`lgroupdel`、`lpasswd`、`lchage`、`lchfn`、`lchsh`、`lid`、`lnewusers`

## OHOS 适配

- Autotools 构建；`glib`（PKG_CHECK_MODULES 需 PkgConfigDeps 补 `.pc`）、`popt`、`linux-pam` 由 Conan 依赖提供。
- Python 绑定、LDAP/SASL 后端、SELinux、Linux audit、NLS 按 OHOS 运行时裁剪关闭（configure 开关，无源码补丁）。
- 后端模块目录经上游原生 `LIBUSER_CONF` 机制指向包内 `lib/libuser`（test_package 在运行时生成配置文件）。

## 依赖

- `glib/2.84.0.1`、`popt/1.16`、`linux-pam/1.7.2`

## 参考

- 上游主页：https://pagure.io/libuser/
- Debian 源码：https://salsa.debian.org/debian/libuser
- 各版本详情见 `0.64-git20241106-dfsg/notes.md`
