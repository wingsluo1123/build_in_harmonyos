# Test Report — haproxy 3.2.0

## Build Test
- Build result: SUCCESS
- Binary: haproxy (ELF 64-bit LSB arm64, dynamic linked libc.so)

## Smoke Test (L2)
- haproxy -vv: Shows version 3.2.0, HarmonyOS HongMeng Kernel, OpenSSL 3.5.6
- haproxy -c -f test_config.cfg: Config validation passed

## Dependencies
- openssl/3.5.6.1, zlib/1.3.1.1, pcre2/10.45: all statically linked
