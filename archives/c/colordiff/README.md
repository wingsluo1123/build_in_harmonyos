# colordiff

colordiff 是一个 `diff` 的包装器/替代工具，为 diff 输出添加颜色高亮，便于阅读代码差异。它是纯 Perl 脚本项目，无需编译。

## 功能概述

- 为 `diff` 输出添加 ANSI 颜色高亮
- 支持 `svn diff`、`git diff`、`cvs diff` 等版本控制差异
- 可自定义颜色方案（深色/浅色背景）
- 提供 `cdiff` 分页包装器脚本
- 纯 Perl 脚本，无需编译

## OHOS 适配

- **Shebang 修复**: colordiff.pl 使用 `#!/usr/bin/perl`，在 OHOS 上 Perl 安装在 `/data/service/hnp/bin/perl`，通过补丁修改为 `#!/usr/bin/env perl` 实现跨平台可移植性
- **无编译步骤**: 纯 Perl 脚本项目，仅通过 `make install` 安装脚本和配置文件
- **安装路径**: 通过 `INSTALL_DIR`、`MAN_DIR`、`ETC_DIR` 参数指定安装路径，配合 `DESTDIR` 实现 staging 隔离

## 依赖关系

- **编译依赖**: 无第三方依赖
- **运行依赖**: Perl (v5.42.0)、diffutils (系统自带)
- 无 Conan 包依赖

## 参考资料

- 官网: https://www.colordiff.org/
- 许可证: GPL-2.0-or-later
