# uuidgen 2.42.2 adaptation notes

## Scope

- Package: `uuidgen/2.42.2`
- Upstream source: `util-linux-2.42.2.tar.xz`
- Task name: `uuidgenC++`
- Branch: `feat/uuidgen-2.42.2`
- Build system: Autotools

## Upstream identity

`uuidgen` is not an independent C++ project. It is a C command in the util-linux suite. The task name's `C++` suffix is a language annotation, not the upstream repository name. The actual source is the official util-linux 2.42.2 release.

## Build

Only `uuidgen` and its internal `libuuid` dependency are enabled:

```text
--disable-all-programs
--enable-uuidgen
--enable-libuuid
```

All other util-linux libraries and programs are disabled. The recipe builds a static internal `libuuid` and packages only the `uuidgen` command.

## OHOS adaptation

- Reuses the proven util-linux 2.42.2 `config.guess` HarmonyOS detection patch.
- Applies the E011 configure fix by replacing `umask 077` with `umask 022`.
- Uses a build-folder `TMPDIR` so configure does not write to OHOS's read-only `/tmp`.

Knowledge used:

- `E011`: configure umask and HMDFS temporary-directory behavior.
- `DRAFT-autotools-config-guess-two-generation-formats`: util-linux config.guess patch form and location.
- `DRAFT-util-linux-ts-runsh-ohos-bash-xargs-driver`: why the focused package runs the two uuidgen ts scripts directly instead of the full util-linux `make check` driver.

## Upstream tests

The relevant upstream test scripts are:

1. `tests/ts/uuidgen/uuidgen` — 8 subtests for `-r`, `-t`, `-6`, `-7`, `--random`, `--time`, `--time-v6`, and `--time-v7`.
2. `tests/ts/uuidgen/oids` — 4 deterministic namespace/hash output checks.

Total: 12 upstream subtests.

## Consumer test

`test_package/test_uuidgen.sh` executes the installed `uuidgen` command and validates:

- 8 random/time UUID output shapes.
- 4 deterministic namespace/hash UUID outputs.

Total: 12 consumer assertions.

The upstream and consumer assertions intentionally use the same command surface, but the consumer script executes the installed package rather than the build-tree binary.

## Dependencies

No external Conan dependencies.

## Verification

Local verification on 2026-10-12:

- `conan create archives/u/uuidgen/2.42.2 -pr:h=ohos-local -pr:b=default --build=missing`: PASS.
- Source download, patch application, configure, build, packaging, and test-package installation all succeeded.
- The packaged binary is `ELF 64-bit LSB pie executable, ARM aarch64`, dynamically linked with `/lib/ld-musl-aarch64.so.1`.
- Because this is a macOS-to-OHOS cross build, target runtime execution and the 12 upstream subtests were skipped locally. They remain pending for the HarmonyOS worker/CI.

`ohc-run.py conan-verify --profile ohos-local` is not usable for this local cross build because the tool passes the same profile as both host and build profiles. The direct Conan command above is the local W3 evidence.
