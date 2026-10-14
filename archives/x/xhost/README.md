# xhost

X.Org's command-line utility for querying and changing the access-control list of an X server.

## Version

- `1.0.10` — HarmonyOS AArch64 Conan application package

## Source

- Upstream: https://gitlab.freedesktop.org/xorg/app/xhost
- Official release archive: https://xorg.freedesktop.org/archive/individual/app/xhost-1.0.10.tar.xz
- SHA-256: `a8afd70059479c712948b895e41c35a4a8bfcede3ba2d5a4b855c88bbb725be1`

## Runtime

The package installs `bin/xhost`. It requires a reachable X server for access-control operations; `xhost -help` and the no-display diagnostic are covered by the consumer test.