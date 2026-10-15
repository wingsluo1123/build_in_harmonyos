# tlsrpt

`tlsrpt` is the competition task/package name for upstream
[libtlsrpt](https://github.com/sys4/libtlsrpt), a C library that generates and
sends TLSRPT datagrams for mail transport agents (RFC 8460).

| Version | Platform | Build | Tests |
| --- | --- | --- | --- |
| [0.5.0](0.5.0/notes.md) | HarmonyOS PC / aarch64 | Autotools, static | 14 functional consumer cases |

Consumer: `find_package(tlsrpt CONFIG REQUIRED)` and link `tlsrpt::tlsrpt`.
The installed upstream headers are `tlsrpt.h` and `tlsrpt_version.h`, and the
library is `libtlsrpt.a`. There are no third-party runtime dependencies.

On HarmonyOS PC use `tlsrpt_open(&connection, "@collector-name")` and configure
the collector to bind the same abstract Unix datagram address. A normal path
still selects a pathname socket. The tested unprivileged HarmonyOS execution
domain rejects pathname socket binding on HMDFS (`EPERM`); a writable directory
alone does not remove this restriction. The collector must support abstract
addresses; the reporter service is a separate application.

This version is independent of the existing `libtlsrpt/0.5.1` package and uses
the exact official 0.5.0 release bytes.
