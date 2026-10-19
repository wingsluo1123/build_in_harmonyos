# Asio 1.38.2

Upgrade task 15224, standalone C++17/header-only configuration. No Boost or
OpenSSL package is required by this selected core configuration. Optional SSL,
Boost stackful coroutines and C++20 feature configurations are not claimed as
tested. The recipe explicitly constrains the validated build profile to C++17.

The GitHub tag archive does not contain generated configure/Makefile.in files.
Headers and tests are at root/include and root/src; the old asio/include and
asio/src paths are compatibility symlinks, not another source tree. No generated
file or upstream test is patched.

The test runner evaluates original src/tests/Makefile.am and properties/Makefile.am
conditions for the selected upstream configuration, fails on unknown conditions,
resolves every enabled target to unchanged source files, and keeps compile-only
targets distinct from runtime TESTS. It builds all 353 enabled programs, runs
the 347 registered runtime programs, and binds source/binary/log hashes. It does
not count inner assertions or six compile-only targets as extra runtime tests.

Native asio-conan-w3-20261015-r1 passed 347/347 and 353/353 compilation checks,
then packaged-header consumers passed event posting/timer and a real loopback
TCP exchange with an exact Unicode payload and graceful EOF. All twelve
transaction phases were validated and released. See reports/test-report.md.
## 编译结束

Official finish also ran in asio-finish-w3-20261015-r3: conan-verify and actual
W3 CI passed, followed by complete frozen twelve-phase validation and release.
Full collected log SHA-256 is
63a8c3ab308d1234ae002a4202339fbf39a90ccbee457f712a05f6d459054dfd.
The aggregate finish remains PARTIAL_POST_W3 for shared pre-existing graph
warnings (step5b/step8); the candidate's new paired draft has its own blocking
Pre-PR validation. No shared framework or graph entry was altered to hide them.
Only the exact official mirror-list rewrite was restored to the original
candidate URL bytes, preserving the official source hash and all other inputs.
Original CI proof/log were copied exactly. A real Conan cache save package
export remains locally ignored under packaging/, not part of the software PR.
Platform Review/CI and publication remain separate later gates.
