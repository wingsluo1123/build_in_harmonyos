# zps

A small utility for listing and reaping zombie processes on GNU/Linux.

- **Homepage**: https://github.com/orhun/zps
- **License**: MIT
- **Language**: C
- **Build system**: CMake / Makefile
- **Description**: zps 是一个用于在 GNU/Linux 系统上列出和清除僵尸进程的小型实用程序。它通过读取 /proc 文件系统获取进程状态，并支持通过信号机制清除僵尸进程。

## 已编译版本

| 版本 | 状态 | 日期 | 构建系统 |
|------|------|------|----------|
| 2.0.0 | built | 2026-06-25 | cmake |

## 功能选项

- `-v, --version`: 显示版本
- `-h, --help`: 显示帮助
- `-a, --all`: 列出所有用户空间进程
- `-r, --reap`: 清除僵尸进程
- `-s, --signal <sig>`: 向僵尸进程父进程发送信号
- `-p, --prompt`: 交互式选择进程
- `-q, --quiet`: 静默模式
- `-n, --no-color`: 禁用颜色输出
