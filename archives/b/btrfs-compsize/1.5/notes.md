# btrfs-compsize 1.5 适配笔记

## 编译环境
- 构建系统: makefile（纯 C：compsize.c + radix-tree.c，无 configure/cmake/meson）
- 编译日期: 2026-10-06
- 编译器: clang 15.0.4（OHOS aarch64 profile）
- 状态: built

## 编译步骤

1. init-build: 官方 GitHub 标签归档 v1.5（SHA-256
   8b15b528f6cf95ff99d2ddfd7bce87271fd1356c875e5f5895ed83caf6952535）。
2. lang-preflight: 任务 lang=c，C 构建，通过。
3. 探索性编译（本地交叉编译验证）：用 OHOS SDK clang
   （`--target=aarch64-linux-ohos --sysroot=<sdk>/sysroot`）编译 compsize.c +
   radix-tree.c 并链接成功 → 产出 aarch64-linux-ohos ELF `compsize`
   （唯一告警为 `__always_inline` 宏重定义，无碍）。
4. conan-init 生成 makefile 型应用配方（E392 三要素：compiler_executables 字典 +
   cwd=source_folder + copy 二进制到 bin/）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `#include <btrfs/ioctl.h>` / `<btrfs/ctree.h>` 找不到 | OHOS sysroot 不含 `btrfs/` 目录（发行版由 libbtrfs-dev 提供） | OHOS sysroot 自带内核 uapi `<linux/btrfs.h>` + `<linux/btrfs_tree.h>`；配方在 generate() 生成两个薄 shim 头 `btrfs/ioctl.h`→`<linux/btrfs.h>`、`btrfs/ctree.h`→`<linux/btrfs_tree.h>`，以 `-I` 暴露 |
| 2 | `radix-tree.h` 无条件包含 `<btrfs/kerncompat.h>` | 上游用 `BTRFS_FLAT_INCLUDES` 开关区分本地/系统 kerncompat | 传 `-DBTRFS_FLAT_INCLUDES=1`，令其选用 compsize 自带的本地 kerncompat.h |
| 3 | 上游无 `make test` / 无 tests/ 目录 | compsize 无自动化测试 | 登记 `ci/config/no_official_test.txt` 豁免 L1；test_package 用 `--help`（exit 0）+ 空目录（"No files." exit 1）两条确定性 oracle 覆盖 |

## 依赖版本

无第三方依赖（仅 libc / libm，系统自带）。ioctl 由 libc 提供，无需链接 libbtrfs。

## 验证结果

```bash
# 消费者验证（test_package/test.sh）
compsize --help            # → "Usage: compsize ...", exit 0
compsize ./emptydir        # → "No files.", exit 1（空目录，不触发需 root 的 btrfs ioctl）
```

两条路径均 host-independent，不需要 btrfs 文件系统或 root，可在 OHOS CI worker
确定性复现。

## 关键知识

- **`btrfs/ioctl.h` + `btrfs/ctree.h` 可用 OHOS 内核 uapi 转包**：compsize 需要的
  全部 btrfs 符号（`BTRFS_IOC_TREE_SEARCH_V2`、`struct btrfs_ioctl_search_key/_header`、
  `BTRFS_EXTENT_DATA_KEY`、`struct btrfs_file_extent_item`、`BTRFS_FILE_EXTENT_INLINE/
  PREALLOC`）都在 OHOS sysroot 的 `<linux/btrfs.h>` 与 `<linux/btrfs_tree.h>` 中，
  两个 shim 头即可，无需 libbtrfs-dev 或 btrfs-progs 依赖。
