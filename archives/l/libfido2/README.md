# libfido2 FIDO2 Library

> Library for FIDO2 authentication devices

## 简介
libfido2 provides library and tools for FIDO2/U2F authentication:
- `fido2-token`: Token management tool
- `fido2-cred`: Credential management
- `fido2-assert`: Assertion handling

## OHOS 适配要点
1. Requires libcbor and openssl
2. USB device access may require permissions

## 功能验证
```bash
fido2-token -L
```
