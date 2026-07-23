# autotrace 0.31.10 adaptation notes

## Scope

- Package: autotrace/0.31.10
- Upstream version: 0.31.10
- Issue: #809
- Source: https://github.com/autotrace/autotrace/archive/refs/tags/0.31.10.tar.gz

## Adaptation

- Added a Conan custom recipe that compiles the upstream C sources directly.
- Declares `glib/2.84.0` as a Conan requirement and resolves GLib flags through `PkgConfigDeps`.
- Disables optional ImageMagick, pstoedit, png, libming, and other optional image backends to keep the package focused on the core library and CLI.
- Defaults to static library packaging.

## Tests

- Added a `test_package` layout check for the CLI, public header, static library, and pkg-config file.
- Compiles and links a C API consumer against `libautotrace.a` and GLib.
- Executes the linked API consumer, as well as the CLI version check, when target binaries are runnable.
- The test does not require image conversion fixtures.

## Local Validation

- `python -m py_compile` was run for recipe/test files.
- `git diff --check` passed.
- Full OHOS `conan create` requires the remote CI environment.
