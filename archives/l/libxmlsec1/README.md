# libxmlsec1

## 简介
libxmlsec1 (XML Security Library) 是一个 C 语言实现的 XML 安全标准库，提供 XML 数字签名（XMLDSig）和 XML 加密（XMLEnc）功能。它基于 libxml2 和 libxslt，支持多种加密后端（OpenSSL、GnuTLS、NSS）。

## 主要组件
- **libxmlsec1**: XMLSec 核心库
- **libxmlsec1-openssl**: OpenSSL 加密后端
- **libxmlsec1-gnutls**: GnuTLS 加密后端
- **xmlsec1**: XMLSec 命令行工具

## 依赖
- **libxml2** >= 2.9.13
- **libxslt** >= 1.1.35
- **openssl** >= 1.1.1（或 gnutls >= 3.8.3）

## 编译信息
- **版本**: 1.3.11
- **构建系统**: autotools（有修改）
- **编译器**: clang
- **链接器**: GNU ld.bfd
- **构建类型**: 静态库（HMDFS 限制）

## 平台适配要点
1. 使用 `--host=aarch64-linux-ohos` 绕过 HMDFS 执行限制（平台硬性限制）
2. 修改 config.status 使用绝对路径临时目录
3. 使用 `--disable-shared` 构建静态库（libtool 在 HMDFS 上无法创建共享库）
4. 使用 `--disable-crypto-dl` 禁用动态加载功能
5. 使用 GNU ld.bfd 代替 lld（lld 依赖 libxml2）

## 特殊说明
- 由于 HMDFS 文件系统限制，本版本为**静态库版本**
- xmlsec1 可执行文件需要 ELF 签名才能运行
- pkg-config 文件已正确配置

## 资源
- 官方网站: https://www.aleksey.com/xmlsec/
- GitHub: https://github.com/lsh123/xmlsec
- 文档: https://github.com/lsh123/xmlsec/wiki