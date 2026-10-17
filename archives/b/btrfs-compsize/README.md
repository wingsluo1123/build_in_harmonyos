# btrfs-compsize

compsize — 报告 btrfs 文件集在压缩 / reflink / 部分覆盖 extent 下的实际磁盘占用。

## 软件信息

- **名称**: btrfs-compsize（上游项目名 `compsize`）
- **描述**: 统计一组 btrfs 文件占用的压缩类型与有效压缩比，输出各算法（none/zlib/zstd/…）的磁盘用量
- **主页**: https://github.com/kilobyte/compsize
- **类别**: filesystem / tool

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.5 | built | 2026-10-06 | 官方 tag v1.5；纯 Makefile C 程序 |

## 工具列表

编译后可用命令：

- `compsize` - 统计 btrfs 文件的压缩 / 重删空间占用

## 编译说明

- **构建系统**: 纯 Makefile（无 configure / CMake / meson）
- **第三方依赖**: 无（仅 libc / libm，系统自带）
- **头文件来源**: 上游 `#include <btrfs/ioctl.h>` + `<btrfs/ctree.h>`；OHOS sysroot
  无 `btrfs/` 目录，但自带内核 uapi `<linux/btrfs.h>` + `<linux/btrfs_tree.h>`，
  配方以两个薄 shim 头转包（见 `notes.md`）。

```bash
make CC=<clang> CPPFLAGS="-I<btrfs-shim> -DBTRFS_FLAT_INCLUDES=1" -j1
```

## 依赖

无。

## 注意事项

- compsize 的 `BTRFS_IOC_TREE_SEARCH_V2` ioctl 需要 root 且需真实 btrfs 文件系统；
  OHOS 上 Btrfs 内核支持情况另计。本包仅保证可编译、安装、被调用（`--help` /
  空目录扫描），逐文件统计能力取决于目标机内核与文件系统。
