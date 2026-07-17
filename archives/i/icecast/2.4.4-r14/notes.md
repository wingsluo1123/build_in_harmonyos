# Icecast 2.4.4-r14 adaptation notes

## Configuration

- Build a static command-line server with POSIX sockets and threads.
- Supply a target-aware `xslt-config` wrapper from Conan dependency paths.
- Disable YP publishing and optional Theora/Speex formats; keep Ogg Vorbis, TLS, XML, XSLT, and curl support.

## Verification

- The consumer test executes `icecast --version` without opening a listening socket.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
