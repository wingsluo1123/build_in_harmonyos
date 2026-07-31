# ol-notmuch 2.1.4

## Summary

`ol-notmuch` is an Emacs Lisp extension that adds Org links to Notmuch
buffers. The package installs `ol-notmuch.el`, `README.org`, and `LICENSE`
under `share/ol-notmuch`.

## Tests

The local `test_package` checks that the Lisp source and documentation are
installed, and verifies that `ol-notmuch.el` provides `ol-notmuch`.

## OHOS notes

No native code is compiled. Runtime use requires target-side Emacs, Org mode,
and Notmuch integration outside this package.

## New Port Validation

Date: 2026-07-31

Validated on the new OHOS device port `33332` with isolated job
`ol-notmuch-2.1.4-newport-r1`.

- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-2.1.4-ol-notmuch-2.1.4-newport-r1-conan-20260731-175644-45407`
- Command:
  `zsh ci/conan/build_and_test.sh archives/o/ol-notmuch/2.1.4`
- Result: `Build Summary` success, 1 package built, 0 failed
- Full package reference:
  `ol-notmuch/2.1.4#db103909b625bd9f323d253d9f33bb1c:fc3eeb021243959114a0318489539cad6d087e28#2be42eba48abf62579d94f516b29c365`
- Gate summary:
  `L0=pass`, `L1=pass(test_package executed)`, `L2=skip(no bin/ dir)`,
  `L4=pass(no patches)`, `L5=warn(no bin/lib artifacts; share-only package)`
