# autotrace 0.31.10 adaptation notes

## Scope

- Package: autotrace/0.31.10
- Upstream version: 0.31.10
- Issue: #809
- Source: https://github.com/autotrace/autotrace/archive/refs/tags/0.31.10.tar.gz

## Adaptation

- Added a Conan Autotools recipe.
- Runs upstream `autogen.sh` because the tag tarball ships `configure.ac` but no generated `configure` script.
- Disables optional ImageMagick, pstoedit, and png integrations to keep the package focused on the core library and CLI.
- Defaults to static library packaging.

## Tests

- Added a `test_package` layout check for the CLI, public header, static library, and pkg-config file.
- The test does not require image conversion fixtures.

## Local Validation

- `python -m py_compile` was run for recipe/test files.
- `git diff --check` passed.
- Full OHOS `conan create` requires the remote CI environment.
