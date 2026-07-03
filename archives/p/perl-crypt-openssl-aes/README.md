# perl-crypt-openssl-aes

Perl XS module providing a wrapper around OpenSSL's AES (Advanced Encryption Standard) library.

## Description

Crypt::OpenSSL::AES is a Perl XS module that provides AES encryption and decryption
functionality by wrapping OpenSSL's libcrypto AES functions. It supports 128, 192,
and 256-bit key sizes.

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0.21-r1 | published | 2026-07-03 | CPAN 0.02 + OpenSSL 3.5.6, AES 功能 C API 验证通过 |

## Dependencies

- Perl >= 5.42.0
- OpenSSL >= 3.5.6 (libcrypto)

## Installation

```bash
# Conan install
conan install --requires=perl-crypt-openssl-aes/0.21-r1@ohpcd/stable

# Or manual
perl Makefile.PL PREFIX=$HOME/usr/local INC="-I$HOME/usr/local/include" LIBS="-L$HOME/usr/local/lib -lcrypto"
make && make install
```

## 功能测试结果 (2026-07-03)

| 项目 | 结果 | 说明 |
|------|------|------|
| 编译产物完整性 | ✅ PASS | ELF 结构、符号、依赖正确 |
| AES 加密 | ✅ PASS | C API 验证，与 CPAN 测试向量一致 |
| AES 解密 | ✅ PASS | 正确还原明文 |
| 往返测试 | ✅ PASS | encrypt→decrypt 正确 |
| Perl 模块加载 | ❌ FAIL | OHOS SELinux dlopen 策略限制 |
| CPAN 测试套件 | ❌ SKIP | 依赖模块加载 |

详细报告: `0.21-r1/reports/functional-test-report.md`

## OHOS 平台运行时限制

XS .so 文件在用户路径下无法被 Perl dlopen 加载，根因为 **OHOS SELinux dlopen 策略**：

- 用户路径 (`/storage/Users/...`) 文件标签: `u:object_r:hmdfs:s0` → dlopen Permission denied
- 系统路径 (`/data/service/hnp/...`) 文件标签: `u:object_r:hnp_file:s0` → 正常加载
- 此限制影响**所有**用户路径下的 Perl XS 模块，非本软件特有问题
- 解决方案: 将 .so 安装到系统路径（需 root 权限）或修改 SELinux 策略

**注意**: 此前文档中 "SELinux E046" 的诊断为误诊。实际根因为 dlopen 策略限制，非 chmod/文件权限问题。

## Notes

- OpenSSL 3.x deprecation warnings for AES_* functions are expected and non-blocking
- AES 加密/解密功能通过 C 直接调用 OpenSSL API 验证正确
