# 运行期知识草稿：多头文件 include/ 树的"用户态可用性审计"方法

> Draft: `DRAFT-SCST-221-UAPI-HEADER-USABILITY-AUDIT`
> Stem: `scst-2.2.1-uapi-header-usability-audit` — pairs with the same-stem `.kv`

## 问题

把上游 include/ 树整目录打成 header-library 时，混在其中的内核树专用头
（依赖 `linux/blkdev.h`、`linux/autoconf.h`、`scsi/scsi_cmnd.h`——这些只在
内核构建树里存在，musl sysroot 没有）会让消费者在第一次编译时就失败，
等于交付了不可用产物。

scst 2.2.1 的实测分类结果：

| 头 | 闭包特征 | 判定 |
|---|---|---|
| scst_const.h | `linux/version.h` + `scsi/scsi.h`（sysroot 均有） | ✅ 用户态可用 |
| scst_user.h | `#ifdef INSIDE_KERNEL_TREE` 双分支，用户态仅 `<scst_const.h>` | ✅ 用户态可用 |
| scst.h | `linux/blkdev.h`、`scsi/scsi_cmnd.h`、`linux/interrupt.h`... | ❌ 内核树专用 |
| scst_debug.h | `linux/autoconf.h`、`linux/bug.h` | ❌ 内核树专用 |
| scst_sgv.h | 内核 SG 内部接口 | ❌ 内核树专用 |

## 方法（可复用清单）

1. **逐头列闭包**：`grep -n "#include <" include/*.h`
2. **sysroot 实证**：候选依赖头逐一 `ls $SYSROOT/usr/include/...` 验证存在
3. **单头编译冒烟**：`echo '#include "x.h"' | clang -fsyntax-only -`
4. **双分支头**：核对 `#ifdef INSIDE_KERNEL_TREE` 用户态分支的真实依赖
5. **test_package 锁契约**：`_Static_assert` 锁版本编码/ABI 序，
   `strcmp` 断言锁字符串常量（防上游静默漂移）
6. **布局对齐消费方式**：上游 `make install` 装到 `$prefix/include/scst/`，
   conan 包平铺 `include/`，下游以 `-I<conan include>`（或 SCST_INC_DIR）
   等价对齐

## 取证记录

- 包: scst 2.2.1（`archives/s/scst/2.2.1`）
- 环境: OHOS aarch64，clang 15.0.4，sysroot `ohos-sdk_26.0.0.18/ohos/native/sysroot`
- 证据: `reports/conan-create.log`（test.c 9/9 断言通过）
