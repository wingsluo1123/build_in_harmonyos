# linux-firmware-brcm 20260622 测试报告

## Status

本报告基于真实的 `conan create`（含 test_package）执行结果生成，日志见
`.ci_logs/conan_build_linux-firmware-brcm_20260622.log`。该库为纯固件资源包
（firmware-resource-package），无编译产物、无构建系统、无传统测试框架，
上游功能测试按 0/0（N/A）记录；资源完整性以新增 25 项 smoke 断言验证。

## 测试环境

- 平台：OHOS aarch64（profile: `ci/conan/profiles/ohos-aarch64`，clang 15 / libc++）
- Conan 版本：2.29.1
- 构建方式：`conan create archives/l/linux-firmware-brcm/20260622`（test_package 随包执行）

## 上游测试统计（0/0，N/A）

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 固件资源包，无测试框架 |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | **0/0（N/A）** |

已核验上游无功能测试入口（无 test/、tests/、make check；check_whence.py 等属元数据/许可证校验）。

## 新增 smoke 测试统计（25/25，100%）

| 测试类型 | 用例数 | 通过 | 失败 | 说明 |
|----------|-------:|-----:|-----:|------|
| 目录存在性/非空 | 2 | 2 | 0 | res/brcm/ 存在且非空 |
| 许可证检查 | 2 | 2 | 0 | LICENCE.broadcom_bcm43xx 存在 + Broadcom 再分发条款 |
| 关键固件存在性 | 7 | 7 | 0 | brcmfmac4366c-pcie.bin 等抽样 |
| 非空检查 | 7 | 7 | 0 | 同上 7 个文件逐字节大小断言 |
| SHA256 逐文件校验 | 4 | 4 | 0 | 与上游基线 hash 比对 |
| 无 ELF 检查 | 1 | 1 | 0 | ELF count = 0 |
| 文件总数/类型分布 | 1 | 1 | 0 | 56 文件（23 .bin + 2 .fw + 1 .hcd + 30 .txt） |
| 文件名格式 | 1 | 1 | 0 | 无控制字符异常 |
| **合计** | **25** | **25** | **0** | **25/25（100%）** |

## 验证结果

- 编译状态：通过（conan create RC=0）
- 上游测试用例通过率：0/0（N/A）
- 新增测试用例通过率：25/25（100%）
- 打包产物：`packaging/linux-firmware-brcm-20260622-ohos-aarch64.tar.gz`（含 res/brcm 全部 56 个固件文件）

本报告仅记录本地测试事实，不声明 CI 或制品发布结果。
