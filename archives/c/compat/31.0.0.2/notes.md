# compat 31.0.0.2

## Summary

`compat` is a pure Emacs Lisp compatibility library. It is needed by modern
Emacs Lisp packages such as `ol-notmuch`, and is the first reusable dependency
for the Emacs batch testing path.

The recipe uses the upstream GitHub tag archive instead of the GNU ELPA package
archive because the ELPA archive does not include the upstream test suite. The
GitHub tag contains `compat-tests.el` and the upstream `Makefile`.

## Upstream Tests

Upstream validation is run during `build()` with `emacs/29.1`:

- `make compile`
- `make test`
- `make check`

`compat-tests.el` contains 223 ERT tests.

The recipe rewrites the build-local `make check` comparison files from
`/tmp/compat-*` to `$(TMPDIR)/compat-*`. This keeps the same checks but makes
them runnable on OHOS, where `/tmp` is not a valid writable scratch location in
the runner.

The patch is limited to upstream tests: two TRAMP mock checks assume the
mock remote can use `/tmp`. The OHOS runner cannot access `/tmp`, so the recipe
sets `COMPAT_OHOS_SKIP_TRAMP_TMP=1` and those checks are reported as skipped
rather than failed. The rest of the ERT suite still runs normally.

The recipe runs the tests from a build-local `compat-31.0.0.2` directory. This
preserves the upstream `package-get-version` assumption that package sources are
inside a `<name>-<version>` directory, while keeping the downloaded Conan source
tree unchanged for packaging.

## Package Environment

Installed Lisp files live under `share/emacs/site-lisp/compat-31.0.0.2`.

`package_info()` exports:

- `COMPAT_LISPDIR`
- `EMACSLOADPATH`, prepended with the installed compat Lisp directory

The same values are exported in both Conan build and run environments so
downstream packages can run upstream Emacs batch commands without hard-coding
dependency paths.

## OHOS Validation

Validated on OHOS PC through the repository Conan CI scripts.

- SSH port: `56267`
- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-compat-31.0.0.2-r13-20260803-140029-24622`
- Package:
  `compat/31.0.0.2#9ac87ab03d9c3a199d797b994c978f41:da39a3ee5e6b4b0d3255bfef95601890afd80709#194805efb3ae8dbf12a4c07ae9b50616`
- Upstream commands: `make compile`, `make test`, `make check`
- Upstream ERT result: 223 registered and executed, 221 expected results,
  0 unexpected results, 2 skipped
- Skipped ERT tests: `compat-make-nearby-temp-file`,
  `compat-temporary-file-directory`
- Skip reason: the OHOS runner cannot access `/tmp` through the mock TRAMP
  remote used by those upstream checks
- `make check`: passed after redirecting temporary comparison files to
  `TMPDIR`
- `test_package`: passed; output included
  `compat consumer load validation OK` and
  `compat Emacs batch load validation OK`
- CI gates: L0 pass, L1 pass, L2 skip because the package has no `bin/`, L4
  pass, L5 warn because this pure Emacs Lisp package has no `bin/` or `lib/`
  artifact directory

The validation used the already-built local `emacs/29.1` and `ncurses/6.5`
packages in the isolated Conan cache. Remote CI will require those dependencies
to be published in the package registry.
