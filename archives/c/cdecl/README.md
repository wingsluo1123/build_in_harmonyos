# cdecl — OpenHarmony 编译档案

## 软件简介

cdecl 是用于解释和生成 C/C++ 声明、类型转换表达式的命令行工具，可将复杂声明转换为英文描述，也可根据英文描述生成 C 声明。

## OHOS 适配要点

1. Autotools 平台识别需显式传入 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`。
2. HMDFS 文件系统下 `configure` 使用 `umask 077` 创建临时目录会导致 `config.status` 无法写入，补丁改为 `umask 022`。
3. `readline` 和 `curses` 仅用于交互体验，批处理命令行功能可通过 `--without-readline --disable-term-size` 禁用，避免引入未发布依赖。
4. HMDFS 不支持 GNU make jobserver `mkfifo`，Conan 构建使用 `make -j1`。

## 构建配置

- 构建系统：Autotools
- 配置参数：`--without-readline --disable-term-size --disable-dependency-tracking --prefix=/`
- 依赖：无

## 命令声明

该软件安装 `cdecl` 与 `c++decl` 可执行文件，已按 R38 在软件级目录提供 `commands.json`。
