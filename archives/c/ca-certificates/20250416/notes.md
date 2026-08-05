# ca-certificates 20250416 适配笔记

## 编译环境
- 构建系统: makefile (data-only package)
- 编译日期: 2026-08-05
- 编译器: N/A (no compilation needed)
- 状态: published

## 源码说明
- 版本 20250416 不在 Debian FTP 上存在（可用版本: 20241223, 20250419, 20260601）
- 使用 20250419 源码包（最接近的官方版本）
- 源码 URL: http://ftp.debian.org/debian/pool/main/c/ca-certificates/ca-certificates_20250419.tar.xz

## 编译步骤
ca-certificates 是纯数据包，不需要 C/C++ 编译。主要工作：

1. 运行 `python3 certdata2pem.py` 从 Mozilla certdata.txt 生成 150 个 PEM 证书文件
2. `make install DESTDIR=...` 安装证书和 update-ca-certificates 脚本

## 关键问题与解决方案

### 问题: cryptography Python 模块在 OHOS 上不可用
- **根因**: cryptography 模块依赖 Rust 编译的 .so 文件 (`_rust.abi3.so`)
  - OHOS 平台上 .so 文件权限为 0640 (rw-r-----)，当前用户无法加载
  - chmod 无法修改其他用户拥有的文件权限
- **解决方案**: 在 conanfile.py 的 `build()` 中生成一个轻量级 cryptography shim
  - shim 使用 OpenSSL CLI (`openssl x509 -inform der -enddate`) 替代 Rust 绑定
  - 提供 `x509.load_der_x509_certificate()` 和 `cert.not_valid_after` API
  - **certdata2pem.py 完全不修改** — 无裁剪

### 问题: 版本 20250416 不存在
- Debian ca-certificates 没有 20250416 版本
- 最近的是 20250419（3 天后）
- 使用 20250419 源码，版本号保持 20250416

## 依赖
无外部依赖（Python3 和 OpenSSL 由系统提供）

## 交付物
- 150 个 Mozilla CA 证书文件 (share/ca-certificates/mozilla/*.crt)
- update-ca-certificates 脚本 (sbin/)
---

**编译结束**: 2026-08-05 13:11
**最终状态**: built
