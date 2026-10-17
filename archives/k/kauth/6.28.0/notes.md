# kauth 6.28.0 notes

## Scope

This recipe packages KAuth 6.28.0 for HarmonyOS PC (OHOS aarch64, CMake project,
upstream project name `kauth`; KDE Frameworks 6). It is the 6.26.0 archive
refreshed onto the 6.28.0 sources; the upstream delta is small (see "Version
refresh" below) and the adaptation surface is unchanged.

## Source verification

- Official URL: `https://download.kde.org/stable/frameworks/6.28/kauth-6.28.0.tar.xz`
- SHA256 (`fb4d90ee46a2f6202e53cdd5af8f77069c380955e3f340881f2f36ec8312079b`,
  2273684 bytes): matches the official download.kde.org `.sha256` sidecar and
  was re-verified on the tarball fetched through the aliyun mirror. The other
  four mirror URLs (bfsu/ustc/nju/aliyun list in `conandata.yml`) serve the
  same official files.

## Version refresh (6.26.0 -> 6.28.0)

The upstream source delta between the two tarballs is:

- top-level `CMakeLists.txt`: `KF_VERSION`/`KF_DEP_VERSION` bump and
  `find_package(ECM 6.28.0)`;
- `src/CMakeLists.txt`: `Qt6::Gui` added as a PRIVATE usage requirement;
- `src/backends/polkit-1/Polkit1Backend.cpp` (not compiled under the FAKE
  backend);
- translation `.po` files under `poqm/`.

Everything else - the FAKE backend, `BackendsManager`'s plugin fallback, and
the whole `autotests/` subtree - is byte-identical to 6.26.0, so the OHOS
adaptation surface and the rule12 HarmonyOS-specific tests carry over
unchanged.

## Adaptations

- `KAUTH_BACKEND_NAME=FAKE` and `KAUTH_HELPER_BACKEND_NAME=FAKE` avoid
  unavailable Polkit and system D-Bus services.
- `KF_SKIP_PO_PROCESSING=ON` omits translation catalog generation.
- Dependencies are unified with two overrides (see "Dependency fixes" below).

### patches/0001-lower-kf-dep-version.patch

Upstream raises `KF_DEP_VERSION` together with the release and uses it for
`find_package(KF6CoreAddons ${KF_DEP_VERSION} REQUIRED)` and for the exported
`KF6AuthConfig.cmake.in` (`find_dependency(KF6CoreAddons "@KF_DEP_VERSION@")`),
but the published ohpcd KF6 stack stops at `kcoreaddons/6.26.0.1`. Without the
patch both the build's configure step and every downstream consumer of
`KF6Auth` fail to resolve the dependency. The patch lowers the variable to
`6.26.0` (same family patch as `krunner`/`kcontacts` 6.28.0); the
`find_package(ECM 6.28.0)` line is deliberately untouched because ohpcd
publishes `ecm/6.28.0`, which satisfies it exactly.

The archive history of the previous revision is worth keeping visible: an
earlier 6.26.0 archive carried `patches/0001-CMakeLists.txt.patch`, which
disabled the whole `autotests/` subdirectory on OHOS, justified as
"qdbusxml2cpp-generated DBus adaptor moc code is incompatible with the OHOS Qt
toolchain". **That justification was never verified and turned out to be
incorrect.** The patch was inert (no `patches:` section in `conandata.yml`,
and `build()` never called `apply_conandata_patches()`), and after the two real
dependency bugs below were fixed every autotest target compiled with no patch
at all. Only the KF_DEP_VERSION patch above is applied in this archive.

## Dependency fixes (both carried from 6.26.0)

### 1. `KeyError: 'OHOS'` from the cmake tool_require

`expat/2.8.2` (reached via `qtbase-sql-dbus` -> `dbus/1.14.10`) declares
`tool_requires("cmake/[>=3.17]")`. The CCI cmake recipe distributes prebuilt
binaries selected by OS key and lists only `Linux`/`Macos`/`Windows`, so an
OHOS build aborts with `KeyError: 'OHOS'` (or, with conancenter disabled,
`Package 'cmake/[>=3.17]' not resolved`). Fix:

```python
self.requires("expat/2.8.2.1", override=True)
```

(same approach as `avahi-tools`, `avahi-compat-libdns_sd`, `awf-gtk`).

### 2. `variable has incomplete type 'class Q_DBUS_EXPORT'` (header mixing)

`kcoreaddons/6.26.0.1` references the plain `qtbase/6.11.1`, whose `qconfig.h`
defines `QT_NO_DBUS` (`QT_FEATURE_dbus -1`), while the QtDBus headers come from
`qtbase-sql-dbus/6.11.1`. `qdbuserror.h` therefore takes its `#else` (no-D-Bus)
branch, where `Q_DBUS_EXPORT` is never defined because `qtdbusglobal.h` only
includes `qtdbusexports.h` under `#ifndef QT_NO_DBUS`. Fix:

```python
self.requires("qtbase/6.11.1.1", override=True)
```

(same approach as `baloo/6.28.0` and `statusnotifieritem/6.26.0`; dependency
binaries remain cache hits under the override graph).

## Upstream tests

`autotests/CMakeLists.txt` declares 5 CTest entries when `BUILD_TESTING=ON`, but
`KAuthPolicyGenTest` and `KAuthPolicyGenTestCompare` are guarded by
`if(NOT "${KAUTH_BACKEND_NAME}" STREQUAL "FAKE")` and are therefore **not
registered** on OHOS (this recipe uses the FAKE backend). That leaves 3
registered entries, all of which compile and link with no patch applied:

| Test | Result | Reason |
|------|--------|--------|
| `KAuthSetupActionTest` | executed headless (`QT_QPA_PLATFORM=offscreen`) | No session bus needed |
| `KAuthHelperTest` | excluded when no session bus can be started | Drives `DBusHelperProxy` over a D-Bus session bus |
| `KAuthFdTest` | excluded when no session bus can be started | Waits on a helper service registered on the session bus |

Measured run (`conan-verify kauth 6.28.0`, ohos-aarch64): `KAuthSetupActionTest`
executed and **passed** - `1/1 Test #1: KAuthSetupActionTest .... Passed 0.11 sec`
/ `100% tests passed, 0 tests failed out of 1`. The ctest line carried
`-E "KAuthHelperTest|KAuthFdTest"` because the recipe's `dbus-daemon` probe found
no daemon to start a private session bus with, so those two ran as **excluded**
(not passed). The full verdict - G0/G1/G2/G3/G4 all PASS, L2/L4/L5 skipped (no
cache path) - is recorded in `reports/conan-verify-report.md`.

### Why the two helper tests are excluded

No `dbus-daemon` exists anywhere in this environment: not in the system paths,
not in the hnp toolchain, and not in any conan package of the dependency graph.
`dbus/1.14.10` on ohpcd deliberately builds `target="dbus-1"` only, i.e. it
ships `libdbus-1` and no daemon. The recipe probes for `dbus-daemon` at build
time and starts a private session bus when one is available; only when none can
be found does it exclude these two entries and report them as excluded. They
are **not** counted as passing. This follows the `akonadi/25.12.3` precedent
for `dbus/1.14.10` environments.

## HarmonyOS-specific test (rule12)

The external PR review (`pc-pr-review`) rule 12 requires every adapted package
to ship **at least one HarmonyOS-specific test**; a count of 0 fails with
`❌ FAIL 规则 12: 鸿蒙特有测试 N=0 < 1`. The PR description's "适配后测试用例
统计" table is what the reviewer reads, so the fix must land in the
`test_package` and be declared in its `MANIFEST.yml` at the same time.

kauth's HarmonyOS-specific test covers two layers, both driven from
`test_package/conanfile.py::test()` as separate `self.run(...)` calls:

### 1. Runtime layer - `test_package/test_kauth_ohos.cpp`

OHOS has no Polkit and no D-Bus session daemon, so the recipe builds kauth with
`KAUTH_BACKEND_NAME=FAKE` / `KAUTH_HELPER_BACKEND_NAME=FAKE`. Because no backend
plugin is installed under `KAUTH_BACKEND_PLUGIN_DIR`,
`BackendsManager::init()` falls back to a plain `FakeBackend`
(`src/BackendsManager.cpp`, `if (!auth) auth = new FakeBackend;`), which reports
`NoCapability`. The test asserts the resulting observable behavior of that
platform adaptation path:

| Assertion | Value on OHOS FAKE backend |
| --- | --- |
| `Action(name).name()` | round-trips |
| `Action(name).isValid()` | `true` (isValid() is purely "name is set") |
| `Action().isValid()` | `false` |
| `Action().status()` | `Action::InvalidStatus` (2) |
| `Action(name).status()` | `Action::DeniedStatus` (0) |
| `Action(name).execute()` -> `job->exec()` | `false` |
| `job->error()` | `ActionReply::BackendError` (9) |
| `job->errorString()` | "The backend does not specify how to authorize" |
| `helperId()` / `hasHelper()` | empty / `false` |
| `setDetailsV2()` / `detailsV2()` | round-trip |

The `BackendError` outcome is the **FAKE backend contract**, not a defect: with
`NoCapability`, `ExecuteJob` falls into its else branch
(`src/executejob.cpp`: `ActionReply r(ActionReply::BackendError); r.setErrorDescription(
tr("The backend does not specify how to authorize"));`) and reports the failure
through `KJob::setError()` / `setErrorText()`. This is exactly why kauth cannot
authorize on OHOS, and asserting it is a real gate on the adaptation.

The file starts with a `#ifndef __OHOS__ #error ... #endif` guard so a host
build cannot silently produce a meaningless "pass".

It needs only `QCoreApplication`: no session bus, no Polkit, no Qt platform
plugin. (A `QT_QPA_PLATFORM=offscreen` environment is still set by the recipe's
upstream test path but the binary does not depend on it.)

### 2. Artifact layer - `test_package/fixtures/ohos_artifact_check.py`

Verifies the FINAL conan package artifact `lib/libKF6AuthCore.a` using the
standard library only (no `readelf`/`llvm-ar` dependency):

1. the archive exists and is non-empty;
2. it is a real `ar` archive (`!<arch>\n`);
3. it has at least one member;
4. at least one member is an OHOS-shaped ELF relocatable object
   (ELF64, little-endian, `EM_AARCH64` = 183, `ET_REL` = 1);
5. no backend/helper plugin is shipped under `lib/plugins/kf6/kauth`, which is
   the precondition for the `FakeBackend` fallback the runtime test relies on.
   The compile-time plugin search path baked into `BackendsManager`
   (`KAUTH_BACKEND_PLUGIN_DIR`) is printed for auditability.

All checks fail closed (non-zero exit on the first failure).

## Build and test status

Measured on device (`conan-verify kauth 6.28.0`, profile `ohos-aarch64`,
Conan 2.29.1): **Verdict PASS** - G0/G1/G2/G3/G4 all PASS, L2/L4/L5 skipped
(no cache path). `conan create` succeeded end-to-end; recipe revision
`4cf7380eb9b6dadf1d23365824e932e5`, package ID
`a92bf6ef398ce607105bca9b8b3543f038f4c819`.

- Upstream ctest: 1/1 passed (`KAuthSetupActionTest`, 0.11 s);
  `KAuthHelperTest`/`KAuthFdTest` excluded (no session bus);
  `KAuthPolicyGenTest*` not registered under the FAKE guard.
- test_package consumers: `test_kauth` smoke PASS; `test_kauth_ohos` PASS
  (13 runtime checks); `ohos_artifact_check.py` RESULT: PASS (6 checks;
  `libKF6AuthCore.a` 236186 bytes, 13 ar members, 12 ELF64/aarch64 ET_REL
  objects, no backend/helper plugins under `lib/plugins/kf6/kauth`).
- Source fetch fell through the URL list exactly as designed: on this device
  `download.kde.org`, `mirrors.bfsu.edu.cn` and `mirrors.ustc.edu.cn` all fail
  TLS verification (self-signed interception) while `mirror.nju.edu.cn` and
  `mirrors.aliyun.com` serve the tarball with a matching sha256 - the run
  completed via the fallback list with no recipe change needed.
- Full report: `reports/conan-verify-report.md` (sanitized; the raw
  `conan-create.log` stays out of the archive per platform policy).
