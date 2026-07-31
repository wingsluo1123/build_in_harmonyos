# ol-notmuch 2.1.4

## Summary

`ol-notmuch` is an Emacs Lisp extension that adds Org links to Notmuch
buffers. The package installs `ol-notmuch.el`, the upstream `Makefile`,
`README.org`, and `LICENSE` under `share/ol-notmuch`.

## Tests

The release tarball has no standalone test directory. Upstream validation is the
Makefile `lisp` target, which runs Emacs batch byte-compilation, autoload
generation, and `check-declare`.

The OHOS runner used here does not provide Emacs. The local `test_package`
checks that the upstream Makefile compile entry is packaged and verifies the
main Lisp integration markers: `(require 'ol)`, `(require 'notmuch)`,
`org-link-set-parameters`, and `(provide 'ol-notmuch)`.

## OHOS notes

No native code is compiled. Runtime use requires target-side Emacs, Org mode,
and Notmuch integration outside this package.

## New Port Validation

Date: 2026-07-31

Validated on the new OHOS device port `33332` with isolated job
`ol-notmuch-2.1.4-upstreamtests-r1`.

- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-2.1.4-ol-notmuch-2.1.4-upstreamtests-r1-conan-20260731-204101-55189`
- Command:
  `zsh ci/conan/build_and_test.sh archives/o/ol-notmuch/2.1.4`
- Result: `Build Summary` success, 1 package built, 0 failed
- Full package reference:
  `ol-notmuch/2.1.4#54f1c223e4b3c05f6ce533b9404502c8:fc3eeb021243959114a0318489539cad6d087e28#00a8d5f480759f2939960a005fac757f`
- Gate summary:
  `L0=pass`, `L1=pass(test_package executed)`, `L2=skip(no bin/ dir)`,
  `L4=pass(no patches)`, `L5=warn(no bin/lib artifacts; share-only package)`
- Test evidence: `test_package` ran
  `test_ol_notmuch.py` and printed
  `ol-notmuch upstream compile entry and Emacs Lisp files are packaged`.
