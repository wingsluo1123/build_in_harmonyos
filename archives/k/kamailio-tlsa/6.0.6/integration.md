# TLSA 6.0.6 runtime integration

Load `lib/kamailio/modules/tlsa.so` in a **matching Kamailio 6.0.6 core**
with the same module ABI flags. Kamailio 6.1.3 is not a compatible host.
Keep the upstream module ABI check enabled. This package contains only TLSA,
its example configuration, license and integration instructions.

On the tested OHOS HNP runtime, core daemonization closes runtime-owned file
descriptors and subsequently breaks TCP worker startup. Apply the included
`0001-src-core-daemonize.c.patch` to the matching core and run it under a
foreground supervisor using `-DD -E -Y <private-runtime-dir>`. The patch keeps
inherited descriptors in foreground mode; the normal daemon path is unchanged.
The core and `sl` used by `test_package` are built from the same official source
in the test build directory. They are test fixtures and are not packaged.

Use the OHOS platform definitions recorded in `conanfile.py`, including
`DEFS=-UHAVE_RESOLV_RES`, when building the core. A native compiler, make,
flex and bison are required. Run `conan create` with the repository's
`ci/conan/profiles/ohos-aarch64` host and build profiles to reproduce the test.

TLSA keeps its embedded OpenSSL function and data symbols local. Its fork
handler detaches only keys created through references linked into TLSA;
unrelated module keys remain intact. External dynamically loaded OpenSSL
providers are outside this ownership boundary. FIPS, PKCS#11, WSS application
routing and every optional Kamailio module are not covered by the test suite.
