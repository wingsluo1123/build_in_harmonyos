# cyrus-sasl 2.1.28 adaptation notes

## Source

- Official release tarball:
  `https://github.com/cyrusimap/cyrus-sasl/releases/download/cyrus-sasl-2.1.28/cyrus-sasl-2.1.28.tar.gz`
- SHA256:
  `7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c`

## Dependency decisions

- The first pass keeps the core `libsasl2` library self-contained.
- `saslauthd`, `pwcheck`, authdaemon, PAM, LDAP, SQL, Berkeley DB/GDBM,
  Kerberos/GSSAPI, OPIE, DES, OpenSSL, NTLM, SRP, OTP, and sample programs are
  disabled to avoid external service and credential-store dependencies.
- Static SASL support is enabled for the default package so validation does not
  depend on OHOS runtime plugin directory discovery.

## OHOS build adjustments

- `0001-configure-ohos-tempdir.patch` changes the autoconf temporary directory
  creation umask from `077` to `022`, matching the OHOS/HMDFS build-directory
  permission workaround while keeping the change tracked in `patches/`.
- `0002-lib-Makefile.in-copy-linksrcs.patch` replaces the generated static
  archive symlink step with a copy operation so package creation does not depend
  on symlink support.
- The recipe passes `MKDIR_P`, `INSTALL`, `INSTALL_PROGRAM`, and `INSTALL_DATA`
  to `make`/`make install` for OHOS instead of rewriting generated Makefiles in
  the build tree.
- `CC_FOR_BUILD` is derived from `tools.build:compiler_executables` when
  available and otherwise falls back to the PATH-visible `clang` name; no
  absolute build-machine compiler path is hard-coded.

## Upstream tests

The release includes upstream test and sample sources such as:

- `utils/testsuite.c`
- `saslauthd/testsaslauthd.c`
- `sample/client.c`
- `sample/server.c`
- `sample/sample-client.c`
- `sample/sample-server.c`

These are not executed in the first cross-buildable package because they depend
on sample programs, daemon paths, plugin/backend configuration, or interactive
client/server negotiation. The Conan `test_package` instead validates the public
consumer API without system-authentication services.

## Validation status

PR CI build #11317 initially failed in `source()` before the consumer test ran
because the conandata patches were not present in the exported source folder.
The `exports_sources = "patches/*"` correction was included in subsequent CI
build #11333, which passed the Conan `test_package` and L0/L1 gates on recipe
commit `65f19f2b`. Later commits do not have a separate CI result. This archive
therefore uses
`status: built`; that remote result does not claim a successful local Conan
build, package upload, or OpenHarmony runtime test.
