# vamp-sdk 2.10.0 · HarmonyOS PC

## Source and dependency

The recipe uses the official Vamp Plugin SDK 2.10.0 release tarball, pinned by
the SHA-256 in `conandata.yml`. The SDK libraries have no external link
dependency. Upstream's example host and regression suite use libsndfile, so
the recipe requires the published `libsndfile/1.2.2` package. A clean Conan
installation of that package succeeded on the HarmonyOS PC before development.

The official regression script uses the separately published
`vamp-test-plugin`. Its source files are vendored under `upstream-test-plugin/`
so the test is reproducible without a second network fetch. Only its Makefile
SDK path is adjusted at build time; the plugin source, regression script, and
22 expected result files are unchanged.

## Upstream test inventory

The SDK's `make test` target lists available plugins as a smoke test. The
independent `test/run-test-plugin-regression.sh` runs 22 cases against the
external test plugin and provides 22 expected text outputs. The recipe runs
the latter and compares every output byte for byte. The upstream script alone
does not reliably signal a comparison failure through its exit status, so the
recipe also checks the case counts, failure files, and all expected outputs.

## HarmonyOS adaptations

Autoconf's generated `configure` uses `umask 077` for its temporary directory.
The HarmonyOS PC user-storage filesystem prevents the shell from writing to
that directory. A two-line portability patch changes the temporary-directory
mask to `007`; no build or test logic is altered. New shells on the same
filesystem cannot discover their current directory with `getcwd`, so the
recipe passes the physical source path through `PWD` before running configure.
Upstream's Makefile is run serially because GNU Make's parallel jobserver
cannot create its FIFO on this filesystem.

The package contains the SDK headers, static and shared SDK libraries, and
the example plugin. The example host is built and used during upstream
validation but is not delivered as a command-line product.

## Verification

On HarmonyOS PC AArch64 with the repository's `ohos-aarch64` host and build
profiles, `conan create` completed with exit code 0. Upstream output
comparisons: **22/22**. The installed-package consumer loaded the delivered
ZeroCrossing plugin, processed eight synthetic samples, and verified four
crossings and their timestamps. The separate HarmonyOS case persisted those
features in the device's user-storage directory and reopened the file.
Consumer cases: **2/2**, including **1/1 HarmonyOS-specific**.

See `reports/test-report.md` for the exact command and test classification.
---

**编译结束**: 2026-10-14 11:10
**最终状态**: built
