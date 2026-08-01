# spicedb 1.56.0 HarmonyOS PC notes

## Adaptation summary

- Upstream source: official GitHub tag `v1.56.0`.
- Build system: Go module command under `./cmd/spicedb`.
- OHOS strategy: build a pure Go `linux/arm64` executable with `CGO_ENABLED=0`.
- The recipe keeps `GOCACHE`, `GOMODCACHE`, `GOPATH`, and `TMPDIR` inside the Conan build folder.
- Version metadata is injected through `github.com/jzelinskie/cobrautil/v2.Version`, matching the upstream Homebrew packaging approach.

## Validation

- `python -m py_compile` passed for the recipe and test package.
- `git diff --check` passed.
- Local `conan create` was not run because this Windows workspace does not provide the competition OHOS Conan/Go toolchain.
- The test package checks `spicedb --help` and `spicedb version` when the target binary can be executed.
