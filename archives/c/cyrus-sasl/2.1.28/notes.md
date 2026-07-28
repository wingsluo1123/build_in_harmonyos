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
