# 依赖 `<btrfs/ioctl.h>` / `<btrfs/ctree.h>` 的包：用 OHOS 内核 uapi 转包 shim，免 libbtrfs-dev

- **草稿 ID**: DRAFT-btrfs-compsize-1.5-ohos-kernel-uapi-btrfs-header-shim
- **来源**: btrfs-compsize/1.5 适配（任务 14599；上游 compsize，GitHub `kilobyte/compsize` tag v1.5）
- **分类**: ohos / headers / portability / build-system / makefile / packaging / cross-compile
- **状态**: 草稿（随 PR 提交，待审核）
- **source_pr**: 14867

## 问题 / 错误签名

- 编译时报
  `fatal error: 'btrfs/ioctl.h' file not found` /
  `fatal error: 'btrfs/ctree.h' file not found`
  （或 `'btrfs/kerncompat.h' file not found`）。
- 消费者在发行版上靠 `libbtrfs-dev`（Debian）/ `libbtrfs-devel`（SuSE）/ btrfs-progs
  提供这些头；OHOS sysroot **没有 `btrfs/` 目录**，`conan` 制品仓也没有 `btrfs-progs`
  这个 conan 包（只有 legacy 归档），因此照搬发行版依赖会直接卡住。

## 根因

btrfs 用户空间头来自内核同一份 **uapi**：`<btrfs/ioctl.h>` 实际是内核
`include/uapi/linux/btrfs.h`，`<btrfs/ctree.h>` 里被消费者用到的磁盘结构/键值
（`BTRFS_EXTENT_DATA_KEY`、`struct btrfs_file_extent_item`、`BTRFS_FILE_EXTENT_INLINE`/
`PREALLOC`）来自 `include/uapi/linux/btrfs_tree.h`。而 **OHOS SDK sysroot 自带一整套
Linux uapi**（`<linux/btrfs.h>`、`<linux/btrfs_tree.h>` 都在），只是没有发行版惯用的
`btrfs/` 平铺目录。也就是说：**头文件内容其实都在，缺的只是路径别名。**

关键事实：compsize 这类工具 **只用到 ioctl 定义与磁盘结构体，不链接 libbtrfs**
（`ioctl()` 由 libc 提供）。所以整件事是纯头文件问题，无需 `libbtrfs-dev`、无需
`btrfs-progs` 依赖、无需任何 `.so`。

## 最小修复方案

在 `archives/b/btrfs-compsize/1.5/**` 范围内：

1. **两个薄 shim 头**（`generate()` 里生成，随 `-I` 暴露）：
   - `btrfs/ioctl.h` → `#include <linux/btrfs.h>`
   - `btrfs/ctree.h` → `#include <linux/btrfs_tree.h>`
2. **`-DBTRFS_FLAT_INCLUDES=1`**：上游 `radix-tree.h` 用
   `#if BTRFS_FLAT_INCLUDES … #include "kerncompat.h" #else … <btrfs/kerncompat.h>`，
   定义该宏即让它用 compsize 自带的本地 `kerncompat.h`，不再去找 `<btrfs/kerncompat.h>`。
   （若上游用的是 `<btrfs/kerncompat.h>` 且无此开关，则再补第三个 shim 头转包即可。）
3. **纯 Makefile 调用**：`make CC=<conf 里的 clang> CPPFLAGS="-I<shim> -DBTRFS_FLAT_INCLUDES=1" -j1`，
   产物 `compsize` 拷到 `bin/`。

## 验收判据

- 交叉编译产出 aarch64-linux-ohos ELF `compsize`；`-I<btrfs-shim>` 下
  `<btrfs/ioctl.h>`/`<btrfs/ctree.h>` 解析成功（本机 OHOS SDK clang
  `--target=aarch64-linux-ohos --sysroot=<sdk>/sysroot` 实测通过，唯一告警为
  `__always_inline` 宏重定义）。
- test_package 走两条 host-independent oracle：`compsize --help` → 打印
  `Usage: compsize` 且 exit 0；`compsize <空目录>` → 打印 `No files.` 且 exit 1。
  二者都不触碰 btrfs 文件系统、不需要 root（README 所述
  `BTRFS_IOC_TREE_SEARCH_V2` 需 root，该路径不触发）。

## 适用与不适用

- **适用**：消费者仅需 btrfs **ioctl 定义 / 磁盘结构体**（不链接 libbtrfs）的包——
  compsize、btrfs 诊断/解析类小工具。
- **不适用**：真正要调 `libbtrfs` / `libbtrfsutil` **库函数**的消费者——那需要一个
  真正的 `btrfs-progs` conan 包（含 `.so`），shim 头不解决问题。
