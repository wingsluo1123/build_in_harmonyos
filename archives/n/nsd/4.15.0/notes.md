# NSD 4.15.0

- Builds the authoritative DNS server and validation utilities with the
  published OpenSSL package.
- Optional dnstap, systemd, XDP, external libevent, recvmmsg, TCP Fast Open,
  and x86 SIMD kernels are disabled for a portable OHOS build.
- The official 4.15.0 release tarball omits `tpkg`, and its `make test` target
  is intentionally empty. The consumer checks the version, parses a minimal
  configuration, and validates a real zone file.
- Official OHOS test and CI results remain pending.
