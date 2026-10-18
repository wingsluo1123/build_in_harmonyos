# imap

University of Washington IMAP toolkit with c-client library and IMAP/POP servers.

- Homepage: https://www.washington.edu/imap/
- Mirror: https://github.com/uw-imap/imap
- License: Apache-2.0
- Build system: custom UW Makefile (top-level OSTYPE)
- Type: library (c-client static library)

## HarmonyOS PC adaptation

- Build with \`make slx SSLTYPE=none\` (generic Linux shadow-password port, no PAM; no OpenSSL dependency).
- Only the static c-client library is packaged (renamed to libc-client.a); daemons (imapd/ipopd) need inetd, mail spool and PAM and are not packaged.
- Upstream ships no automated test suite; consumer checks in test_package validate offline c-client APIs.
