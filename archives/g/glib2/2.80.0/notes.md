# glib2 2.80.0 HarmonyOS PC adaptation notes

Route: **路径 A（基础适配）**. GLib uses Meson and standard LLVM/Conan dependencies. This port needs platform detection, dependency discovery, and HarmonyOS runtime-test adjustments; it does not use a proprietary toolchain, platform-private API binding, assembly code, or an unusually complex architecture.

The `glib2/2.80.0` archive did not exist before this work. The repository already contains `glib2/2.88.0` and `2.88.0.1`; they were checked as references, and this package was adapted from the official 2.80.0 source rather than copied from another version.

## Build configuration

- Source: GLib 2.80.0 (`glib-2.80.0.tar.xz`), SHA-256 `8228a92f92a412160b139ae68b6345bd28f24434a7b5af150ebe21ff587a561d`
- Build system: Meson; static libraries; native HarmonyOS OHOS/aarch64 profile
- Options: `wrap_mode=nodownload`, upstream tests enabled, installed tests disabled; libmount, SELinux, NLS, introspection, man pages, GTK-doc, and OSS-Fuzz disabled
- Conan dependencies: `pcre2/10.45`, `zlib/1.3.1`
- Offline Meson subprojects: libffi 3.5.2 and proxy-libintl 0.5

## Adaptation

Patches 0001–0006 cover HarmonyOS host detection, netlink availability, Conan's PCRE2 pkg-config name, musl format-warning compatibility, offline libffi/proxy-libintl builds, and running the visibility generator with Meson's Python. Patch 0008 also detects `getpass` and updates `gio/tests/gtlsconsoleinteraction.c` to use a stdin fallback when `HAVE_GETPASS` is unavailable, so the test helper compiles on HarmonyOS; its socket-suite runtime fallback is not covered by the device run. Patches 0007, 0009–0011 adjust Meson suite metadata for verified HarmonyOS environment gaps. No upstream test assertions are weakened.

The test package has four consumer API checks for string prefixes, hash tables, GVariant round-tripping, and GObject construction/type. Its HarmonyOS-specific executable performs four checks: querying the default network monitor, observing a real file-create event, observing a real rename event in user storage, and verifying the renamed file's contents. The device's default monitor is `GNetworkMonitorBase`: patch 0002 disables Linux netlink detection, so the test validates the fallback's reported snapshot (`available=1`, `connectivity=FULL`) but does not claim to test network-change notifications or connectivity transitions. File creation and rename are exercised against real HarmonyOS user storage.

## Upstream test inventory and device result

The complete upstream inventory is **N = 6,538 individual test items**: 5,378 unit items, 990 integration items, and 170 script/other items. Counting follows registered GTest cases, Python unittest methods, individual pkg-config checks, and standalone Meson command checks; Meson targets are not counted as test items.

The native HarmonyOS 6.0 PC aarch64 W3 run executed **N′ = 5,405 upstream items**: 5,348 named GTest results (5,322 passed and 26 skipped) and 57 standalone checks (53 passed and 4 optional lint checks skipped). After W3, the `fileutils` binary was also run item-by-item on the same device: 25 of 27 cases passed; `/fileutils/mkdir-with-parents` failed because HarmonyOS does not permit creating `/usr/b/c`, and `/fileutils/set-contents-full` failed its 0644 mode check (observed 0660, including with umask 0000). These 27 cases are counted as executed, not excluded. Combined upstream totals are 5,432 executed: 5,400 passed, 30 skipped, and 2 failed. The package adds eight passing checks, so the adapted run contains **5,440 executed items**: 5,408 passed, 30 skipped, and 2 failed. Excluding skips, 5,408 of 5,410 runnable items passed (99.96%).

The 30 actual skips are 26 GTest cases whose upstream preconditions or host facilities are unavailable on this device, plus four optional lint tools that are not installed. Their individual names and reasons are in `reports/test-report.md`. A separate **1,106 upstream items were not started** because the device run excludes Meson's `failing` suite: 980 individual GTest registrations, 88 Python unittest methods, 25 script/xmllint checks, and 13 standalone GIO command checks. The device shell cannot start the required session D-Bus daemon: `/tmp` is read-only, the shell account is absent from the POSIX user database, and filesystem-backed AF_UNIX binds are restricted. Other excluded items depend on shell/user assumptions, the system MIME database, or unavailable mount/socket facilities. These items are not counted as SKIP or as executed tests. `reports/excluded-upstream-tests.md` lists them individually with reasons.

## True-device Conan finish

Ran `finish glib2 2.80.0 built` on the HarmonyOS 6.0 PC device using the native OHOS/aarch64 profile, clang 15, and Conan 2.29.1. Conan recipe checks G1–G4 passed, and the W3 `conan create` build and test run passed with exit code 0. The `test_package` ELF programs were launched through Bash; logs show both the consumer API test and the HarmonyOS network/file-monitor checks passed. The generated `.ci-result.json` records SHA-256 `913e8cf5f7fd29b69bb56021fe3f16981d6302f8a4b9e44fe4380c13a605917c` for `reports/w3-local-ci.log`.

The overall finish readiness result was partial after W3: repository-wide knowledge entries have pre-existing missing fields, and legacy packaging readiness checks request `packaging/`, `.staging-verified`, README, and release tarballs that do not apply to this Conan archive. A legacy patch counter also matched only `000*.patch`, so it counted 9 of the 11 four-digit patches. No legacy artifacts or staging markers were fabricated. The Conan verify report also records a G0 knowledge hint for E090; the actual conan create and W3 test run passed.

The item-level exclusion inventory is in `reports/excluded-upstream-tests.md`; the PR description records the final test totals and true-device W3 result. The local finish run retains its generated CI result and full log for integrity verification.
