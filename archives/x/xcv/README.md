# xcv — OpenHarmony 编译档案

## 软件简介
xcv 是一个 bash 脚本，在命令行提供“剪切 / 复制 / 粘贴文件”：`xcv x|c|v|l`。
所有暂存文件放在 `$HOME/.xcv`，每次剪切或复制都会清空该目录后重建。

## OHOS 适配要点
- 纯脚本，无需编译；`package()` 直接安装 `bin/xcv`。
- 上游 shebang `#!/bin/bash` 在 OHOS 上不存在，改为 `#!/usr/bin/env bash`。
- 运行时依赖 `bash/5.3`。
- 脚本会 `rm -rf $HOME/.xcv`，测试一律使用临时 HOME。

## 依赖关系
- 运行时：bash/5.3
