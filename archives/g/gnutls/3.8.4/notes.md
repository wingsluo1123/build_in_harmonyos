# GnuTLS 3.8.4 adaptation notes

## Build

- Build system: Autotools
- Status: built
- Source: official GnuTLS 3.8.4 tar.xz release
- Source SHA-256: `2bea4e154794f3f00180fa2a5c51fe8b005ac7a31cd58bd44cdfa7f36ebc3a9b`
- Dependencies: `nettle/3.10.2` and `gmp/6.3.0`

The recipe applies two target-recognition patches for `config.guess` and
`config.sub`, configures the bundled libtasn1 implementation, disables GOST,
and passes one executable path to make through its `SHELL` variable.

## Package test

The test package runs `gnutls-cli --version` from the packaged `bin`
directory through Conan's run environment. A successful exit verifies that
the CLI was packaged and its runtime libraries can be loaded on a runnable
target.
