# perl-crypt-openssl-rsa

RSA encoding and decoding using the OpenSSL libraries (Perl XS module).

## Versions

| Version | Status | Date |
|---------|--------|------|
| 0.37 | built | 2026-07-03 |

## Description

Crypt::OpenSSL::RSA provides RSA encryption, decryption, signing and verification
using the OpenSSL library. It is a Perl XS module with C extension code.

## OHOS Adaptation

On OHOS, SELinux (hishell_hap:s0) blocks dlopen() of shared libraries at runtime.
A C helper executable (rsa_helper) is compiled alongside the XS module, linking
libssl/libcrypto at startup. A pure-Perl wrapper module delegates RSA operations
to this helper via IPC, providing full API compatibility.

See `0.37/notes.md` for detailed adaptation information.
