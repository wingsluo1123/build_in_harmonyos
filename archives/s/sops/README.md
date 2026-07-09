# SOPS (Secrets OPerationS)

SOPS is an editor of encrypted files that supports YAML, JSON, ENV, INI and BINARY
formats and encryption with AWS KMS, GCP KMS, Azure Key Vault, age, and PGP.

## 功能概述

- **多格式支持**: YAML, JSON, ENV, INI, BINARY 文件格式
- **多后端加密**: AWS KMS, GCP KMS, Azure Key Vault, age, PGP
- **密钥轮换**: 支持密钥轮换操作
- **差异比对**: 支持明文/密文差异比对
- **集成友好**: 可作为命令行工具或 Go 库使用
- **GitOps 兼容**: 加密文件可直接提交到版本控制系统

## OHOS 适配

### 构建方式
- **构建系统**: Go (module: `github.com/getsops/sops/v3`)
- **Go 版本**: 1.24.4 (linux/arm64)
- **CGO**: 禁用 (`CGO_ENABLED=0`)，生成纯静态二进制
- **编译参数**: `-trimpath -ldflags '-s -w'` (去除调试符号和路径信息)

### 平台特殊处理
- **ELF 签名**: OHOS 平台要求 ELF 二进制签名后才能直接执行。未签名二进制需通过 `elfldr` 包装器运行。
- **包装器方案**: conanfile.py 在 `package()` 中创建 shell 包装脚本 (`bin/sops`)，通过 `elfldr` 调用实际二进制 (`bin/sops.real`)，实现透明执行。
- **无补丁**: sops 3.11.0 在 OHOS 上无需任何源码补丁。

### 已知问题
- `sops --version` 会尝试连接 GitHub API 检查更新，在无网络或受限环境下会产生警告（不影响功能）。
- Go 静态二进制为 EXEC 类型（非 PIE），L4 安全扫描 PIE=disabled，属 Go 编译器默认行为。

## 依赖关系

### 编译依赖
- Go 1.24.0+ (go.mod 要求)
- 无 C/C++ 依赖 (CGO_ENABLED=0)

### 运行依赖
- 无 (纯静态二进制，自包含所有依赖)

## 参考资料

- **官网**: https://github.com/getsops/sops
- **源码**: https://github.com/getsops/sops
- **License**: MPL-2.0
- **Go Module**: `github.com/getsops/sops/v3`
