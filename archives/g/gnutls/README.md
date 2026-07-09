# GnuTLS TLS Library

> GNU Transport Layer Security library for secure communications

## 简介
GnuTLS is a secure communications library implementing TLS, SSL and DTLS protocols. It provides:
- `gnutls-cli`: TLS client tool
- `gnutls-serv`: TLS server tool
- `libgnutls`: Core TLS library

## OHOS 适配要点
1. Requires libtasn1, nettle, gmp dependencies
2. May have unresolved symbols on HarmonyOS

## 依赖
| 依赖 | 版本 | 说明 |
|------|------|------|
| libtasn1 | 4.19 | ASN.1 parsing |
| nettle | 3.10 | Cryptographic library |
| gmp | 6.3.0 | Large integer arithmetic |

## 功能验证
```bash
gnutls-cli --version
```
