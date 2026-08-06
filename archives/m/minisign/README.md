# minisign — Dead Simple File Signing Tool

## 软件简介

minisign 是由 Frank Denis 开发的极简文件签名与验签工具，使用 Ed25519 数字签名算法（基于 libsodium）。它旨在提供一个简单、可靠、安全的签名验证方案，适用于软件发布、配置文件验证等场景。

**主要功能**：
- 使用 Ed25519 算法对文件进行数字签名
- 验证文件签名的有效性
- 支持可信签名（trusted comment）机制
- 支持密钥加密保护

## 构建信息

| 项目 | 值 |
|------|-----|
| 构建系统 | CMake |
| 目标平台 | ohos-aarch64 |
| 源码地址 | https://github.com/jedisct1/minisign |
| 许可证 | ISC |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libsodium | 1.0.22 | 现代加密库（NaCl） |

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.12-r1 | built | Conan 适配版 |
