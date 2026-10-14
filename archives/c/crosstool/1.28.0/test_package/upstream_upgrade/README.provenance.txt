# test_package/upstream_upgrade/ — vendored upstream test fixtures (verbatim)

These files are copied byte-for-byte from upstream tag crosstool-ng-1.28.0
(2025-09-06). No edits. They are the DATA consumed by the faithful Python
port of testing/upgrade/run.sh in ../conanfile.py
(_run_upstream_upgrade_suite); only the driver was ported (run.sh needs
bash associative arrays, unavailable at test time), assertion semantics
are identical.

Origin (verified 2026-09-30, sizes match the GitHub API listing):
  https://raw.githubusercontent.com/crosstool-ng/crosstool-ng/crosstool-ng-1.28.0/testing/upgrade/samples/v0-0000.config  (16834 bytes, 36 ## assertions)
  .../v0-0001.config  (16895 bytes, 27 ## assertions)
  .../v0-0002.config  (16683 bytes, 13 ## assertions)
  .../v0-0003.config  (10024 bytes,  7 ## assertions)
  .../v0-0004.config  ( 9052 bytes,  3 ## assertions)
  .../v0-0005.config  ( 8697 bytes,  3 ## assertions)
  .../v0-0006.config  (11040 bytes,  5 ## assertions)
  https://raw.githubusercontent.com/crosstool-ng/crosstool-ng/crosstool-ng-1.28.0/testing/upgrade/kconfig-list/3  (58664 bytes)

Negative evidence (why the options-set case is expected to fail):
  .../testing/upgrade/kconfig-list/4  -> HTTP 404 at the same tag, while
  ct-ng.in declares `export CT_CONFIG_VERSION_CURRENT=4`. run.sh fails the
  options-set case when the reference file is absent, on any platform.

3 `## BARE_SYMBOL` lines (v0-0000.config) match neither run.sh case pattern
(`## *=*` nor `## * is not set`) and are ignored by upstream too; the port
replicates that (94 effective `## OPT=val` assertions total).
