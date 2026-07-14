# lhasa — OpenHarmony 编译档案

## 软件简介

Lhasa 是一个解析 LHA/LZH 归档文件的 C 语言库，同时提供兼容 Unix LHA 工具接口的命令行工具 `lha`。当前版本支持读取和解压 LHA/LZH、LArc、PMarc 等归档格式。

- 官方主页: https://github.com/fragglet/lhasa
- License: ISC
- 类型: 库 + 命令行工具

## OHOS 适配要点

- Autotools `configure` 需要显式传入 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`，避免 HarmonyOS 运行时 `config.guess` 无法识别系统。
- OHOS/HMDFS 下 `umask 077` 创建的临时目录会导致后续文件写入权限失败，构建前将 `configure` 中的 `umask 077` 替换为 `umask 022`。
- OHOS 不支持 GNU make jobserver FIFO，构建使用 `make -j1`。
- 命令行工具产物为 `lha`，同时安装静态库 `liblhasa.a`、头文件和 pkg-config 文件。

## 已编译版本

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|----------|----------|
| 0.6.0 | built | 2026-07-14 | autotools |

## 使用方法

```bash
lha l archive.lzh
lha x archive.lzh
lha p archive.lzh file.txt
```

## 参考资料

- [Lhasa GitHub](https://github.com/fragglet/lhasa)
- [Lhasa 0.6.0 Release](https://github.com/fragglet/lhasa/releases/tag/v0.6.0)
