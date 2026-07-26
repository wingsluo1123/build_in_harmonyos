# Icecast 2.4.4 adaptation notes

## Configuration

- Build a static command-line server with POSIX sockets and threads.
- Supply a target-aware `xslt-config` wrapper from Conan dependency paths.
- Disable YP publishing, URL authentication, and optional Theora/Speex formats; keep Ogg Vorbis, TLS, XML, and XSLT support.

## Verification

- The recipe builds the two standalone upstream programs from
  `src/avl/test.c` and `src/log/test.c` and executes both whenever the target
  profile is runnable.
- A focused test-only patch fixes obsolete pointer casts and the stale logging
  macro without changing the scenarios exercised by either upstream program.
- The consumer test executes `icecast --version` without opening a listening socket.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
