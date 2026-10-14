# GPT fdisk (gptfdisk)

GPT fdisk 是 Rod Smith 开发的 GPT/MBR 磁盘分区工具集，用于处理 GUID 分区表
（GPT）磁盘，也支持 MBR 到 GPT 的转换与修复。

| 工具 | 说明 |
|------|------|
| `gdisk` | 交互式分区编辑器（文本菜单，支持 GPT 与 MBR 转换） |
| `cgdisk` | 全屏 curses 交互式分区编辑器 |
| `sgdisk` | 脚本化/命令行分区工具（适合自动化） |
| `fixparts` | 修复 MBR/GPT 混合问题的专用工具 |

## 在 HarmonyOS PC 上使用

```sh
conan install --requires=gptfdisk/1.0.10
# 四个可执行文件安装到包的 bin/ 目录
```

## 适配信息

- 版本: 1.0.10（上游源码包，SourceForge 官方分发）
- 构建系统: 上游 consolidated Makefile（`TARGET=linux`）
- 依赖: libuuid / popt / ncurses（制品仓静态包，静态链接）
- 适配要点与测试证据见 `1.0.10/notes.md`

## 上游

- 主页: https://www.rodsbooks.com/gdisk/
- 源码: https://sourceforge.net/projects/gptfdisk/files/gptfdisk/
- 许可: GPL-2.0-or-later
