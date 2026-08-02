# spicedb 1.56.0 HarmonyOS PC notes

## Adaptation summary

- Upstream source: official GitHub tag `v1.56.0`.
- Build system: Go module command under `./cmd/spicedb`.
- OHOS strategy: build a pure Go `linux/arm64` executable with `CGO_ENABLED=0`.
- Go toolchain strategy: use `GO`, `go` in `PATH`, known harmonybrew paths, or download the pinned Go 1.26.3 archive from `mirrors.aliyun.com`.
- The recipe keeps `GOCACHE`, `GOMODCACHE`, `GOPATH`, and `TMPDIR` inside the Conan build folder.
- The recipe exports `GOROOT`, prepends the selected Go `bin` directory to `PATH`, and sets `GOTOOLCHAIN=local` so the worker does not try to auto-download another Go toolchain.
- Version metadata is injected through `github.com/jzelinskie/cobrautil/v2.Version`, matching the upstream Homebrew packaging approach.

## Validation

- `python -m py_compile` passed for the recipe and test package.
- `git diff --check` passed.
- Local `conan create` was not run because this Windows workspace does not provide the competition OHOS Conan/Go toolchain.
- The test package checks `spicedb --help` and `spicedb version` when the target binary can be executed.
