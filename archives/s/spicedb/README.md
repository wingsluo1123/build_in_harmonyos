# spicedb

Open-source, Google Zanzibar-inspired permissions database.

## Version

- 1.56.0

## Build notes

- Packages the upstream linux/arm64 release archive published by AuthZed.
- Avoids requiring a Go toolchain on the OHOS CI worker, which currently does not provide `go`.
- Installs the `spicedb` executable to `bin/`.

## Test notes

The Conan `test_package` verifies the installed executable exists and, when runnable, checks both the CLI help text and the version command.
