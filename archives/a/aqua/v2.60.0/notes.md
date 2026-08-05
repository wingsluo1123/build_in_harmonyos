# aqua 编译笔记

## 基本信息

- 软件名: aqua
- 版本: v2.60.0
- 类型: go 工具 (prebuilt binary)
- 编译日期: 2026-08-05
- 上游仓库: https://github.com/aquaproj/aqua

## 编译过程

### 编译方式

使用上游预编译的 linux/arm64 二进制包：
- 上游发布: https://github.com/aquaproj/aqua/releases/download/v2.60.0/aqua_linux_arm64.tar.gz
- SHA256: 695e04849161feced95cda06f37f8032287168b19b6eebf2c75c8fe0069e23d1
- OHOS CI worker 不提供 Go 工具链，使用上游预编译二进制

### 二进制签名

- 使用 /data/service/hnp/bin/binary-sign-tool 对二进制进行 OHOS 平台签名
- 使用 /data/service/hnp/bin/llvm-objcopy 移除 .codesign 段

### 验证

- 二进制文件: bin/aqua
- 功能验证: aqua --help ✅, aqua version ✅ (本地 conan create 验证通过)
- test_package: 3/3 通过 (test_aqua.py: --help, version)
- binary-sign-tool: ✅ 签名成功，二进制可在 HarmonyOS 上执行

## 制品信息

- 制品包: aqua-v2.60.0-ohos-aarch64 (Conan 包)
- 内容: bin/aqua, licenses/LICENSE, share/doc/aqua/README.md

## 备注

此软件通过上游预编译二进制打包创建，无需本地 Go 工具链。
---

**编译结束**: 2026-08-05 01:17
**最终状态**: built
