# spicedb

Open-source, Google Zanzibar-inspired permissions database.

## Version

- 1.56.0

## Build notes

- Builds the upstream Go command from the official `v1.56.0` source archive.
- Uses `CGO_ENABLED=0` and maps the Conan target arch to Go's `GOARCH`.
- Uses `GO`, `go` in `PATH`, known harmonybrew locations, or a pinned Go 1.26.3 archive from `mirrors.aliyun.com` when the worker has no system Go.
- Installs the `spicedb` executable to `bin/`.

## Test notes

The Conan `test_package` verifies the installed executable exists and, when runnable, checks both the CLI help text and the version command.
