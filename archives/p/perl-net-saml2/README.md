# perl-net-saml2 (Net::SAML2)

SAML bindings and protocol implementation for Perl.

## 简介

Net::SAML2 是一个 Perl 模块，提供 SAML 2.0 协议的实现，包括：
- Service Provider (SP) 功能
- Identity Provider (IdP) 交互
- SAML 绑定 (POST, Redirect, SOAP)
- 认证请求、断言处理、登出协议
- XML 签名和加密支持

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.83-r0 | built | 2026-06-26 | 初始编译，Conan 配方验证通过 |

## 鸿蒙平台适配说明

### 编译
- **构建系统**: perl Makefile.PL (ExtUtils::MakeMaker)
- **编译状态**: ✅ 成功 (22 个 .pm 文件)
- **Conan 验证**: ✅ 全部通过 (G0-G4 + L2/L4/L5)
- **补丁**: 无需补丁，纯 Perl 模块

### 运行时依赖
- **纯 Perl 依赖**: 29/38 已安装 ✅
- **XS 依赖**: 9 个模块需 HNP 安装 ⚠️
  - Crypt::OpenSSL::Random, Verify, X509
  - Crypt::PK::RSA (CryptX)
  - XML::LibXML, XML::Sig, XML::Enc
  - Net::SSLeay (for LWP::Protocol::https)

### 平台限制
- XS 模块的 .so 文件受 SELinux HMDFS 限制，需通过 HNP 包安装到系统目录
- 此限制与 perl-dbd-pg 相同，属于平台特性
- 详见 [0.83-r0/reports/test-report.md](0.83-r0/reports/test-report.md)

## 使用方法

```bash
# Conan 安装
conan install --requires=perl-net-saml2/0.83-r0@ohpcd/stable

# Perl 使用 (需先安装 XS 依赖)
use Net::SAML2;
use Net::SAML2::SP;
use Net::SAML2::IdP;
```

## 许可证

MIT License
