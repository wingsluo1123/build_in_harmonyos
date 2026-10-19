# scst 2.2.1 适配笔记

## 适配定位（内核态边界如实申报）

SCST（SCSI target subsystem）是 Linux 内核 SCSI target 框架，**核心产物是内核模块**
（scst.ko 等，需 Linux 内核构建树 `/lib/modules/$(uname -r)/build` + `insmod`）。
HarmonyOS PC（aarch64-linux-ohos）没有 Linux 内核构建树，内核模块不可构建。

本包按「用户态分层交付」模式（jool-modules-lts 6.18.39 已合入先例）交付 scst 核心
include/ 树中**用户态可消费的子集**：

| 头文件 | 用户态可用 | 说明 |
|--------|-----------|------|
| `scst_const.h` | ✅ | 协议常量/版本宏，OHOS sysroot 有 `linux/version.h`+`scsi/scsi.h`，clang 零修改编译通过；**iscsi-scst 2.2.1 用户态唯一需要的 scst 核心头**（usr/event.c） |
| `scst_user.h` | ✅ | scst_user 透传模块用户态接口；`#ifdef INSIDE_KERNEL_TREE` 用户态分支仅含 `<scst_const.h>` |
| `scst.h` | ❌ 排除 | 含 `<linux/blkdev.h>` `<scsi/scsi_cmnd.h>` 等内核树专用头 |
| `scst_debug.h` | ❌ 排除 | 含 `<linux/autoconf.h>` `<linux/bug.h>` |
| `scst_sgv.h` | ❌ 排除 | scatter-gather 内部接口，依赖内核树环境 |

## 编译环境
- 构建系统: 无构建/打包族（header-only，源码头文件直通打包）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（profile ohos-aarch64，os=OHOS / armv8）
- 状态: built（本地 conan create + conan-verify 通过；upload 由 CI release 执行）

## 编译步骤

无编译步骤（header-only）。验证路径：

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# test_package 编译 test.c（static assert + 运行期断言）并执行 → 全部通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | scst.h 等头文件在用户态无法编译 | 依赖 linux/blkdev.h、linux/autoconf.h 等内核树专用头 | 用户态消费子集（scst_const.h/scst_user.h）打包，其余如实排除并在 notes/PR 申报 |
| 2 | 内核模块不可交付 | OHOS 无 Linux 内核构建树（内核态边界） | 分层交付：本包交付头文件；内核模块保持上游源码形态（conandata.yml 官方源可复原），边界在 PR 如实申报 |

## 源码修改

无补丁（`patches/` 为空）：源码零修改，头文件原样打包。

## 依赖版本

无外部依赖（header-only）。

## 上游测试清点（R51）

上游**无测试套件**。清点证据：

```bash
find scst-2.2.1 -iname '*test*' -o -iname '*check*'   # → 0 命中
grep -n '^check\|test:' scst-2.2.1/Makefile            # → 0 命中（无 check 目标）
```

依据 R51「上游确无测试须附清点证据并自行补齐测试」：test_package/test.c 补齐
9 项断言（静态断言 5 + 运行期断言 4，见 test_package/MANIFEST.yml）。

## 验证结果

```bash
conan create ... → test_scst 输出 "test scst 2.2.1: OK (headers ... usable from userspace on OHOS)"
# 9/9 断言通过（见 .ci-result.json 与 test-report）
```

## 交付物

| 文件 | 说明 |
|------|------|
| include/scst_const.h | 协议常量/版本宏（iscsi-scst usr 依赖） |
| include/scst_user.h | scst_user 用户态接口 |
| licenses/COPYING | GPL-2.0 许可证文本 |

## 知识积累

- ✅ 内核框架包分层交付模式（用户态头文件子集 conan 包 + 内核态边界如实申报）已沉淀 → DRAFT-SCST-221-KERNEL-BOUNDARY-HEADER-DELIVERY（jool 先例第二例）
- ✅ 多头文件 include/ 树逐头用户态可用性审计方法（include 闭包分类 + sysroot 实证 + 单头编译冒烟 + 静态断言锁契约）已沉淀 → DRAFT-SCST-221-UAPI-HEADER-USABILITY-AUDIT
- ✅ scst/2.2.1 与 iscsi-scst/2.2.1 的 R36 拓扑序依赖关系已写入 manifest/notes，iscsi-scst PR 须待本包发布后进行

## 对话记录

### 对话 #1：适配路径判定

- 时间: 2026-10-03 01:00-01:20
- 结论: SCST 核心是 kbuild 内核模块，OHOS 无 Linux 内核构建树 → 内核模块不可交付；include/ 逐头审计发现 scst_const.h/scst_user.h 用户态可用（sysroot 有 linux/version.h + scsi/scsi.h）→ 采用分层交付（jool-modules-lts 6.18.39 已合入先例）：header-library conan 包 + 内核态边界申报，适配路径 = 部分适配（头文件包），非无法适配。

### 对话 #2：验证链执行

- 时间: 2026-10-03 01:25-01:40
- 命令: `conan create archives/s/scst/2.2.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
- 结果: G1-G4 + L2/L4/L5 全绿；test_package 1/1 Passed（9 断言），见 reports/test-report.md
- 遇到的问题: ① G1 要求 export_sources/apply_conandata_patches 仓库范式 → 补齐（空补丁集 no-op）；② test.c 静态断言缺分号 → 修复；③ W3 JC6 因 fork main 落后误算 60 包 → 同步 fork main 后在 feat 分支提交归档解决；④ G0 tar xf 报 toybox 错误（环境 quirk，tar 实际为 toybox applet）→ 非阻塞，源码完整性已由 conan create 的 get()+sha256 校验实证
- 编译结束: 2026-10-03 01:35（conan-verify 全绿 + .ci-result.json 生成）

## 注意事项

- **本包是 iscsi-scst/2.2.1 的前置依赖（R36 拓扑序）**：iscsi-scst 2.2.1 用户态构建
  通过 `SCST_INC_DIR` 消费 `scst_const.h`（usr/event.c 引用 SCST_SYSFS_KEY_MARK 等）。
  iscsi-scst PR 必须待本包合入并发布到制品仓后才能通过 R36/PF4 门禁与 CI。
- 上游 `make install` 的惯例布局是 `$prefix/include/scst/`；本包采用 conan 惯例平铺
  `include/`，iscsi-scst 配方通过 `SCST_INC_DIR=<conan include>` 对齐。
- SCST_INTERFACE_VERSION 是 iscsi-scst 自有宏（其 include/iscsi_scst_itf_ver.h），
  不属 scst 包契约，勿混淆。
---

**编译结束**: 2026-10-03 01:44
**最终状态**: built
