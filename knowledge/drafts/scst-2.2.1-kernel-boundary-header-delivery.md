# 运行期知识草稿：Linux 内核框架包（SCST 类）在 OHOS 的分层交付模式

> Draft: `DRAFT-SCST-221-KERNEL-BOUNDARY-HEADER-DELIVERY`
> Stem: `scst-2.2.1-kernel-boundary-header-delivery` — pairs with the same-stem `.kv`

## 问题

SCST 2.2.1（SCSI target subsystem）核心产物是 kbuild 内核模块：
顶层 `make` 走 `make -C /lib/modules/$(uname -r)/build SUBDIRS=... modules`，
include/scst.h 依赖 `linux/blkdev.h`、`scsi/scsi_cmnd.h` 等内核树专用头。
OHOS 没有 Linux 内核构建树 → 内核模块不可构建。

但直接判【无法适配】会丢掉真实可交付面：

- `include/scst_const.h`：协议常量/版本宏，只依赖 uapi 头（`linux/version.h`、
  `scsi/scsi.h`，OHOS sysroot 均有）——它是 iscsi-scst 2.2.1 用户态
  （usr/event.c）**唯一**需要的 scst 核心头。
- `include/scst_user.h`：scst_user 透传模块的用户态 ABI 头，
  `#ifdef INSIDE_KERNEL_TREE` 用户态分支仅含 `<scst_const.h>`。

## 模式（jool-modules-lts 6.18.39 先例的第二例）

1. **用户态子集 → conan 包**：`package_type = "header-library"`，只打包
   逐头审计后确认用户态可用的头；test_package 用 `_Static_assert` 锁
   版本编码（`SCST_VERSION(2,2,1,0)==0x02020100`）与 ABI 序
   （`SCST_USER_PARSE_STANDARD/CALL/EXCEPTION == 0/1/2`）。
2. **内核态边界如实申报**：内核模块保持上游源码形态（conandata.yml 官方
   SourceForge URL + sha256 可复原），notes.md/PR 用专表逐头申报排除理由
   （scst.h/scst_debug.h/scst_sgv.h → 内核树专用）。
3. **R36 拓扑序**：iscsi-scst usr 通过 `SCST_INC_DIR` 消费 `scst_const.h`
   → 先发 scst/2.2.1 头文件包，再发 iscsi-scst/2.2.1。

## 判定信号

- 顶层 Makefile 含 `obj-m` / `make -C /lib/modules` → 内核模块项目
- 同时存在 usr/、tools/ 或用户态可编译头 → 有分层交付面
- 头文件含 `#ifdef INSIDE_KERNEL_TREE` 双分支 → 明确的用户态 ABI 契约

## 验证命令

```bash
grep -rn "obj-m\|/lib/modules" Makefile          # 内核模块信号
grep -n "#include <" include/*.h                 # 逐头可用性分类
ls $SYSROOT/usr/include/linux/version.h $SYSROOT/usr/include/scsi/scsi.h
```

## 取证记录

- 包: scst 2.2.1（`archives/s/scst/2.2.1`）
- 环境: OHOS aarch64，clang 15.0.4，profile `ci/conan/profiles/ohos-aarch64`
- 先例: `archives/j/jool-modules-lts/6.18.39`（commit bbfd40ead9，已合入）
