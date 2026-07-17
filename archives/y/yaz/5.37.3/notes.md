# YAZ 5.37.3 adaptation notes

## Configuration

- Build static YAZ client/server libraries with GnuTLS, ICU, XML, and XSLT support.
- Disable TCP wrappers, Redis, memcached, and documentation toolchain discovery.
- Use Autotools dependency metadata generated from Conan packages.

## Verification

- The consumer test calls `yaz_version` and verifies version 5.37.3.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
