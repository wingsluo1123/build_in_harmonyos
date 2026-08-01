# spicedb

Open-source, Google Zanzibar-inspired permissions database.

## Version

- 1.56.0

## Build notes

- Builds the upstream Go command from `./cmd/spicedb`.
- Uses a pure Go cross-build path with `CGO_ENABLED=0` and isolated Go caches under the Conan build folder.
- Installs the `spicedb` executable to `bin/`.

## Test notes

The Conan `test_package` verifies the installed executable exists and, when runnable, checks both the CLI help text and the version command.
