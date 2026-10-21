# GNU Mailutils 3.20 for HarmonyOS PC

## Source integrity

- GNU official archive: https://ftp.gnu.org/gnu/mailutils/mailutils-3.20.tar.xz
- SHA-256: `a8f3faab1edda5188bb5ca3e4e9c0c5bc72cd0dadf4e1f4799d27fa75c6ae829`
- Downloaded over HTTPS on the HarmonyOS device, checksum-verified, and passed `xz -t`.
- The matching `.sig` was downloaded, but verification was unavailable because neither `gpg` nor `gpgv` is installed on the device or local host.

## Build environment

- Target: HarmonyOS PC, `aarch64-linux-ohos`
- Build system: GNU Autotools
- Conan profile: `ohos-aarch64`
- Independent Conan home: `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-mailutils`
- Native-filesystem Conan package storage: `/data/storage/el2/base/cache/mailutils-8661-r6/p` (passed as `core.cache:storage_path`; HMDFS does not preserve the chmod semantics required by the upstream permission tests)
- Per-run native build/test workspace: `/data/storage/el2/base/cache/mailutils-3.20-nvdqbud4`; the recipe probes `mkfifo`, copies the patched source tree there, and sets `TMPDIR`/`TMP`/`TEMP` inside it. This keeps libtool and Autotest operations off HMDFS.
- Command: `conan create "$HOME/work/psj/archives/m/mailutils/3.20" -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --conf tools.build:jobs=2 -cc core.cache:storage_path=/data/storage/el2/base/cache/mailutils-8661-r6/p`

## Adaptation

1. Add HarmonyOS recognition to `config.guess` and accept `linux-ohos` in `config.sub`.
2. Change Autoconf's temporary-directory umask from `077` to `022`; HMDFS maps directory ownership in a way that otherwise prevents writes by the build process.
3. Probe `getspnam()` and `getutxent()` and guard shadow and utmpx code paths on those function checks; OHOS libc does not provide these functions.
4. Make comsat use the utmpx path only when both the header and `getutxent()` are available.
5. Keep the distribution's generated Texinfo files by neutralising the `stamp-vti` regeneration rule; Toybox `ls` output breaks `mdate-sh`, and `makeinfo` is unavailable on the worker.
6. For dotlock, fall back to atomically creating the lock file with `O_EXCL` when HMDFS rejects `link(2)` with an unsupported-operation or permission error.
7. When DBM backends are disabled, exclude Sieve's `uidnew` extension because upstream otherwise retains an unconditional dependency on `libmu_dbm.la`.
8. Disable optional Python, PAM, TLS, GSSAPI, readline, FriBidi, database, LDAP, and Guile integrations. No SQL module is selected; upstream leaves SQL disabled by default.
9. Harden the upstream `testsuite/cwdrepl.c` test helper: skip an unset `PWD` and stop using the uninitialized buffer when `getcwd()` fails. The upstream `.at` assertions are unchanged.
10. Preserve the toolchain-produced ELF files during packaging. The device has no `patchelf`, binary signer, or `llvm-objcopy`, and post-link ELF rewriting can invalidate OHOS code signatures. Conan's run environment supplies the package library directory through `LD_LIBRARY_PATH`.
11. The upstream install hook attempts `chown root:mail` and setuid mode for `sbin/mda`; the device has no `chown`, and the hook ignores that error. The packaged file is mode `750` without setuid, so privileged local delivery is not covered by the consumer checks.
12. Run HarmonyOS configure, compilation, and upstream Autotest from a per-run workspace on native cache storage after confirming `mkfifo` works there. HMDFS denied the make jobserver FIFO and caused libtool's `../../libtool` to be missing at `tocrlf`; moving the patched source/build/test workspace to native storage lets `tocrlf` link and the full upstream gate run. Libtool hardlink attempts may still return `EPERM`; its generated `ln ... || cp ...` fallback completes the links.

## Dependencies

The recipe declares three optional Conan requirements: GnuTLS 3.8.10, libunistring 1.0, and libtool 2.5.4. These enable the upstream TLS and Unicode cases and the Sieve extension build support. Python, PAM, GSSAPI, readline, FriBidi, database, LDAP, and Guile integrations remain disabled; SQL remains off because no SQL module is selected.

## Tests

Run `mailutils-15271-20261017-r1` completed on the HarmonyOS device with `CONAN_CREATE_EXIT=0`. The official 3.20 archive contains 22 `testsuite.at` files. The default `make -j2 -k check` gate generated 21 Autotest suite summaries: **1,389/1,389 passed, 0 failed, and 0 skipped**. The `libmu_scm` Guile suite is not part of the default `make check` target; the `mail` and `pop3d` DejaGNU harnesses did not run because `runtest` is unavailable and are outside the 1,389-case denominator.

- Upstream result JSON: `/data/storage/el2/base/cache/mailutils-8661-r6/p/b/mailu425e8b7afd356/b/build-release/upstream_test_result.json` — `total=1389, passed=1389, failed=0, skipped=0, suite_count=21`; SHA-256 `703bb6181259b53cad371597423a0af12bd6e50d1d36dcc07686702249d58264`.
- Upstream log: `/data/storage/el2/base/cache/mailutils-8661-r6/p/b/mailu425e8b7afd356/b/build-release/upstream-make-check.log`; SHA-256 `2b7ae4e77ff5a9010c2cb5620b70268429e60e1104a0d6a8a8eaa2e64ada0699`.
- Full Conan device log: `/storage/Users/currentUser/work/psj/ch-mailutils/mailutils-15271-20261017-r1.log`; SHA-256 `d63e70665a989e499744f4c8b7a50294070dfcbb891ecac5709ea6e3d1172440`.
- Consumer API test: CTest `mailutils_api` 1/1; 14/14 checks, 0 failures. `LastTest.log`: `/storage/Users/currentUser/work/psj/archives/m/mailutils/3.20/test_package/build/clang-15-armv8-17-release/Testing/Temporary/LastTest.log`; SHA-256 `cef9b5eccf6ccfbf25fece9aee0e5ad457759ab32ff3a73d5a1ce24514443b42`.
- HarmonyOS package checks: 24/24 over platform identity, executables, servers, version, and libraries.
- Mail-flow end-to-end checks: 6/6; `putmail` delivered a message, then packaged `mail` and `readmsg` read it back.
