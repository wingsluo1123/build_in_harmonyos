# NTL 11.6.0 HarmonyOS PC adaptation

- Builds the static NTL C++ number theory library with the GMP backend.
- Disables native CPU tuning and uses conservative ARM/POSIX feature values.
- Keeps configure compile/link probes but skips executing OHOS target binaries on the build host.
- Disables the optional GF2X backend to keep the dependency surface focused.
- Adds a consumer test that performs real arbitrary-precision arithmetic.

Local verification covers recipe syntax, metadata, patch applicability, source checksum, and repository static gates. The official OHOS armv8 pipeline remains authoritative for the cross-build result.
