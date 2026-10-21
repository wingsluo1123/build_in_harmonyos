# mfiutil 1.0.15-rivoreo-r2-rc-20250214-e8c6289 - 测试报告

> **测试日期**: 2026-10-17
> **测试环境**: WSL 原生 ext4，qemu-aarch64 user-mode binfmt（`/usr/libexec/qemu-binfmt/aarch64-binfmt-P`，enabled）
>   + OHOS guest runtime，真实执行 AArch64 OHOS 二进制
> **测试类型**: 消费者视角冒烟（test_package/test.sh，真实调用打包产物）

## 上游测试审计

上游正式测试为 0：归档 19 个文件无 tests/ 目录，Makefile 仅 default/clean/install
目标（无 check/test），全文件无 ctest/pytest/autotools 测试设施；FreeBSD 原版与
Debian sid 打包（debian/tests 为空）同样无测试。详见 test_package/MANIFEST.yml。

mfiutil 功能执行依赖 MegaRAID 控制器硬件（`/dev/megaraid_sas_ioctl_node` ioctl），
测试机无此硬件，故只覆盖可确定执行的用户land路径与硬件缺失时的真实失败路径，
不伪造硬件响应。

## 测试结果汇总

| 类别 | 通过 | 失败 | 跳过 |
|------|------|------|------|
| 用户land路径 | 4 | 0 | 0 |
| 硬件缺失失败路径 | 2 | 0 | 0 |
| **总计** | **6** | **0** | **0** |

`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh test.sh <mfiutil-bin>","discovered":6,"passedCount":6}`

## 详细测试结果

| # | 测试项 | 命令 | 结果 | 实测输出 |
|---|--------|------|------|----------|
| 1 | 产物 ELF magic | `head -c 4` | ✅ PASS | `7f454c46` |
| 2 | 版本串精确 | `mfiutil version` | ✅ PASS | rc=0，`mfiutil version 1.0.15-rivoreo-r2`（`mfiutil.h` 中 `LOCAL_VERSION "-rivoreo-r2"` 拼接） |
| 3 | 无参 → usage + 非零 | `mfiutil` | ✅ PASS | rc=255，stderr 打印 `Usage: mfiutil …` |
| 4 | 未知命令 → 非零 | `mfiutil definitely-not-a-command` | ✅ PASS | rc=1，`Unknown command` |
| 5 | 无控制器 show adapter → 非零 | `mfiutil show adapter` | ✅ PASS | rc=1，`mfiutil: mfi_open: No such file or directory`（真实走到 ioctl 设备打开失败） |
| 6 | 非法选项 → 非零 | `mfiutil -Z version` | ✅ PASS | rc=255，`unrecognized option: Z`（libc 措辞；断言兼容 glibc `invalid option` 与 OHOS libc `unrecognized option` 两种措辞） |

## 已知限制

- 装有真实 MegaRAID 控制器硬件后，`version` 之外的命令才能完整工作；
  OHOS 上 megaraid_sas 驱动的可用性不在本仓库验证范围。
- 运行时如系统加载了 megaraid_sas 模块，程序会尝试 `mknod
  /dev/megaraid_sas_ioctl_node`（需要 root），失败仅 warn 不退出。
