# DRAFT-autotools-pkgincludedir-absolute-header-relocation — Avoid absolute paths in installed Autotools headers

> **Status**: source-audited draft; installed-package relocation and consumer execution are NOT-RUN. This is a NO-DEVICE session because the device seats are held by `fix-opm-common-15330` and `work-mpich-544`. CI #98007 on pre-fix head `fdbecef7` failed during configure before consumer tests because `config.guess` could not write `dummy.c` under the worker's Home cache temp path.
> **Source event**: libthreadar 1.6.1 HarmonyOS PC dependency task #14347.

## Knowledge type and promotion boundary

This is a Path B knowledge draft. It is stored only in `knowledge/drafts/`; it does not reserve a formal E-number, modify the formal graph, or claim promotion. Maintainers and reviewers decide whether to promote it.

## Symptom

A Conan consumer can compile against an Autotools package in its current cache location, but its public headers stop compiling after the package folder is moved or recreated under another prefix. A nested header include still names the old absolute package include directory.

## Root cause

Some older Autotools projects install headers through a custom `install-data-local` rule rather than a standard header install target. A `sed` command may rewrite every quoted include to `$(pkgincludedir)/...`. Configure substitutes the absolute installation prefix into that variable before `DESTDIR` staging, so the resulting installed header contains the build-time package folder as source text. Staging changes where files are written; it does not make that embedded include path relative.

In libthreadar 1.6.1, `src/Makefile.am` copied `config.h` to `libthreadar_config.h`, then rewrote all quoted header references to include `$(pkgincludedir)`. Thus references between co-located headers such as `mutex.hpp` and `exceptions.hpp` acquired the configured absolute prefix.

## Recommended method

Keep same-directory public-header references as basenames. Rewrite only the generated configuration-header reference, for example from `config.h` to `libthreadar_config.h`; let the consumer's declared include root locate the package's header directory. Add a package-time scan that rejects absolute `#include` directives, then verify a small consumer after moving the package prefix.

For libthreadar 1.6.1, patch 0002 changes the custom installer to rewrite only `config.h`. The paired `test_package` scans installed `.h` and `.hpp` files for absolute include directives before compiling its consumer program. The source-level repair and scan are present in the candidate; runtime execution is NOT-RUN because CI #98007 failed during configure on the pre-fix head and this session did not use the device.

## Scope and limits

- Applies to custom Autotools header installation rules that inject `pkgincludedir` or another configured absolute include root into header contents.
- Does not replace `cpp_info.includedirs` or pkg-config metadata; consumers still need the correct package include root.
- Does not apply when an absolute include is an intentional platform SDK path or when sibling headers are installed into different directories requiring a separately designed relative layout.
- A text scan is a guard, not a substitute for compiling a consumer after package relocation.

## Difference from existing knowledge

E364 covers build-worker include paths persisted into MPICH wrapper metadata. This draft covers a different source: upstream's custom header installer rewrites sibling header includes using the configured package prefix. Both can cause package relocation failures, but they require different source-level checks and repairs.

## Evidence source

- Upstream tag `v1.6.1`, `src/Makefile.am`, `install-data-local` loop.
- Candidate patch `archives/l/libthreadar/1.6.1/patches/0002-keep-installed-header-includes-relative.patch`.
- Candidate consumer guard `archives/l/libthreadar/1.6.1/test_package/conanfile.py`.
- Runtime relocation and test-package results: NOT-RUN; CI #98007 on pre-fix head `fdbecef7` did not reach tests, and device seats were held by `fix-opm-common-15330` and `work-mpich-544`.
