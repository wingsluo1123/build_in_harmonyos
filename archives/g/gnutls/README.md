# GnuTLS TLS Library

> GNU Transport Layer Security library for secure communications

## 简介
GnuTLS is a secure communications library implementing TLS, SSL and DTLS protocols. It provides:
- `gnutls-cli`: TLS client tool
- `gnutls-serv`: TLS server tool
- `libgnutls`: Core TLS library

## OHOS 适配要点
1. Uses the bundled libtasn1 support from the GnuTLS source tree.
2. Requires the published `nettle/3.10.2` and `gmp/6.3.0` Conan packages.

## 依赖
| 依赖 | 版本 | 说明 |
|------|------|------|
| libtasn1 | bundled | ASN.1 parsing |
| nettle | 3.10.2 | Cryptographic library |
| gmp | 6.3.0 | Large integer arithmetic |

## 功能验证
```bash
gnutls-cli --version
```
