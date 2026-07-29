# NSD 4.15.0

- Builds the authoritative DNS server and validation utilities with the
  published OpenSSL package.
- Optional dnstap, systemd, XDP, external libevent, recvmmsg, TCP Fast Open,
  and x86 SIMD kernels are disabled for a portable OHOS build.
- The official 4.15.0 release tarball omits `tpkg`, and its `make test` target
  is intentionally empty. The consumer checks the version, parses a minimal
  configuration, and validates a real zone file.
- Local OHOS arm64 `conan create` completed successfully: OpenSSL, NSD, and
  five packaged NSD tools were built for AArch64. The three consumer checks
  were prepared by the test package; runtime execution is not applicable
  locally because no OHOS arm64 HDC target is connected.
- Native OHOS builds use the worker `TMPDIR`, restore its generated directory
  to mode `0700`, and set `umask 022` so `config.status` can read temporary awk
  files while generated build files retain normal permissions.
- Official OHOS test and CI results remain pending.
