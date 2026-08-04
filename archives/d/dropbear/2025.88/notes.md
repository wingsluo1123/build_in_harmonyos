# Dropbear 2025.88 adaptation notes

## Source

- Upstream: https://matt.ucc.asn.au/dropbear/dropbear.html
- Archive: `dropbear-2025.88.tar.bz2`
- SHA-256: `783f50ea27b17c16da89578fafdb6decfa44bb8f6590e5698a4e4d3672dc53d4`

## Build configuration

The recipe uses the upstream Autotools build and the bundled libtomcrypt/libtommath implementations. Linux keeps the available zlib, openpty and accounting features; OHOS disables the APIs which are unavailable there.

For OHOS builds, the recipe generates `localoptions.h` with `DROPBEAR_SVR_PASSWORD_AUTH=0`. The OHOS C library does not provide `crypt()`, while Dropbear requires it when server password authentication is enabled. Linux builds do not generate this override and retain the upstream password-authentication default. Public-key authentication remains enabled on both platforms.

The two existing portability patches guard `getpass()` and `getspnam()` for OHOS environments where headers may be present without the corresponding functions.

## Validation

- Conan export succeeds with the source and patch metadata.
- OHOS builds recognize `HarmonyOS` directly in Autotools `config.guess` and accept the canonical `linux-ohos` triplet in `config.sub`. The portability patches replace `config.sub` here-document parsing and route Autoconf `config.status` temporary files through `TMPDIR`, which avoids HMDFS permission failures. The recipe redirects `TMPDIR` to a Conan-local directory for the remaining Autotools and test steps.
- The Conan L1 test verifies `dropbear`, `dbclient`, `dropbearkey`, and `dropbearconvert` are packaged.
- Autotools maps both `bindir` and `sbindir` to the package `bin` directory; the L1 test verifies that directory and all four executables.
- On a native runnable target, the test invokes `-h` for all four binaries and checks their usage output, then performs a real public-key SSH client/server round trip.
- The L1 test passes absolute package paths to the shell script and prints captured command output when a help or SSH check fails.
- The ASLR test uses the Linux-compatible `/proc` interface directly instead of building `psutil`, which has no usable OHOS wheel in the CI environment.
- The upstream test venv drops `asyncssh` because it pulls `cryptography`, whose wheel build fails under HMDFS `getcwd`. `test_concurrent` is skipped via `pytest.importorskip("asyncssh")` when the package is unavailable, so `make check` still runs the remaining 50 tests.
- For OHOS builds the recipe rewrites the upstream `test/Makefile.in` `venv/bin/pytest` rule in `build()` (after patches apply) so the venv is created with `python3 -m venv --without-pip --system-site-packages venv`. HMDFS rejects `getcwd` mid-`ensurepip`, which crashed the original `init` bootstrap before any wheel build could start; inheriting the system site-packages reuses the already-installed `pytest` without invoking `pip` or `ensurepip`. The rewriter is inlined in `conanfile.py` because Conan's vendored `patch_ng` rejected a standalone diff for `Makefile.in`.
- Cross builds perform executable presence checks and leave execution to the target CI worker.

The upstream `make check` target now passes with `51 passed, 1 xfailed`. The test setup supplies an isolated authorized-keys directory and Dropbear-format client keys, converts one key to OpenSSH format for AsyncSSH, uses stderr logging for server readiness, explicitly calls the inherited `socketserver.TCPServer.server_close()` after joining each server thread, and closes parameterized TCP listeners before the next case. The Conan build also completes the packaged-binary consumer test successfully.
