# autotrace 0.31.10 adaptation notes

## Scope

- Package: autotrace/0.31.10
- Upstream version: 0.31.10
- Issue: #809
- Source: https://github.com/autotrace/autotrace/archive/refs/tags/0.31.10.tar.gz

## Adaptation

- Added a Conan custom recipe that compiles the upstream C sources directly.
- Declares `glib/2.84.0` and `libpng/1.6.58` as Conan requirements and resolves their flags through `PkgConfigDeps`.
- Retains the native PNG input backend through libpng while disabling optional ImageMagick, pstoedit, libming, and other optional image backends.
- Defaults to static library packaging.

## Tests

- Added a `test_package` layout check for the CLI, public header, static library, and pkg-config file.
- Compiles and links a C API consumer against `libautotrace.a` and GLib.
- Runs the complete upstream `tests/runtests.sh` regression driver against the
  newly built CLI whenever the target binary is runnable.
- Executes the linked API consumer and CLI version check when target binaries are runnable.
- Reuses upstream `tests/github-#34/watch.png` for a real PNG-to-SVG conversion
  and verifies that a missing PNG input fails with a non-zero exit status.
- Upstream 0.31.10 reports 7 successful scenarios, 2 expected-failure
  scenarios, and 1 conditionally skipped stdin scenario without Magick support.

## Local Validation

- `python -m py_compile` was run for recipe/test files.
- `git diff --check` passed.
- Native Linux Release and Debug `conan create` runs execute the upstream
  regression driver and the complete `test_package`.
- Full OHOS validation still requires the supported OHOS environment.
