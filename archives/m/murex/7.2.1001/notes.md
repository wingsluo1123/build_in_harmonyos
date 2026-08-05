# murex 7.2.1001 HarmonyOS PC notes

## Adaptation summary

- Upstream source: official GitHub tag `v7.2.1001`.
- Build system: Go module, single `murex` command from the repository root.
- OHOS strategy: build a pure Go `linux/arm64` executable with `CGO_ENABLED=0`.
- The recipe keeps `GOCACHE`, `GOMODCACHE`, `GOPATH`, and `TMPDIR` inside the Conan build folder so the worker does not depend on writable global cache paths.
- The fallback Go toolchain is chmod-normalized recursively after extraction so the toolchain root directories are traversable and `go/bin/go` plus bundled host tools remain executable on OHOS/HMDFS workers.

## Validation

- `python -m py_compile` passed for the recipe and test package.
- `git diff --check` passed.
- CI #13020 still failed with `PermissionError: [Errno 13] Permission denied` for `go/bin/go`; the recipe now normalizes the whole fallback toolchain tree, including parent/root directories, and verifies `go/bin/go` is executable before invoking `go build`.
- Local `conan create` was not run because this Windows workspace does not provide the competition OHOS Conan/Go toolchain.
- The test package runs `murex -c "echo ohpcd"` and `murex -version` when the target binary can be executed.

