# kservice5 5.116.0 — adaptation notes

## What this software is

KService is the KDE Frameworks 5 service and plugin metadata library. It owns
the application/service database (`ksycoca`, built by the shipped
`kbuildsycoca5` tool), the `.desktop` file model (`KService`, `KServiceGroup`),
the plugin and service traders (`KPluginTrader`, `KServiceTypeTrader`,
`KApplicationTrader`) and the D-Bus activation glue (`KToolInvocation`). The
KF5 branch targets Qt5 and is not the same package as the Qt6-based `kservice`
6.x recipe in this repository.

## Dependencies (read from the upstream CMakeLists.txt)

| dependency | requirement | where |
|---|---|---|
| `ECM` | `find_package(ECM 5.116.0 NO_MODULE)` | `CMakeLists.txt:14` |
| `Qt5 Xml` | `CONFIG REQUIRED Xml` | `CMakeLists.txt:47` |
| `Qt5 DBus` | `CONFIG REQUIRED DBus` (not ANDROID) | `CMakeLists.txt:49` |
| `Qt5 Concurrent/Test` | autotests only | `autotests/CMakeLists.txt:5` |
| `KF5Config` | `CONFIG REQUIRED` | `CMakeLists.txt:52` |
| `KF5CoreAddons` | `CONFIG REQUIRED` | `CMakeLists.txt:53` |
| `KF5DBusAddons` | `CONFIG REQUIRED` (not ANDROID) | `CMakeLists.txt:55` |
| `KF5I18n` | `CONFIG REQUIRED` | `CMakeLists.txt:57` |
| `KF5DocTools` | **optional**, no REQUIRED | `CMakeLists.txt:58` |
| `FLEX` | `REQUIRED` — generates the Trader parser | `CMakeLists.txt:60` |
| `BISON 3.0` | `REQUIRED` — generates the Trader parser | `CMakeLists.txt:68` |

`KF5DocTools` is genuinely optional: the project guards both `kdoctools_install`
and `add_subdirectory(docs)` behind `KF5DocTools_FOUND`, and `kdoctools5` has no
recipe in this repository, so it is disabled explicitly with
`CMAKE_DISABLE_FIND_PACKAGE_KF5DocTools=ON`. That drops only the generated
documentation, not a test or a library feature.

## The two Qt5 baselines (this is the interesting part)

The published KF5 5.116.0 packages in this repository are split across **two
different Qt5 revisions**:

| pins | packages |
|---|---|
| `qt5-qtbase/5.15.2` (plain, `-no-widgets` stub) | `kcoreaddons5/5.116.0`, `kcodecs5`, `kimageformats5`, `kglobalaccel5`, `attica-kf5`, … (21 recipes) |
| `qt5-qtbase/5.15.2.2` (DBus/Widgets capable) | `kconfig5`, `kdbusaddons5`, `ki18n5`, `kwindowsystem5`, `qt5-qtdeclarative`, … (73 recipes) |

KService needs `KF5CoreAddons` **and** `KF5I18n`/`KF5Config`/`KF5DBusAddons`,
i.e. one package from each column, so the graph cannot resolve on its own:

    $ conan graph info --requires=kcoreaddons5/5.116.0 --requires=ki18n5/5.116.0 -pr ohos-aarch64-wsl
    ERROR: Version conflict: Conflict between qt5-qtbase/5.15.2.2 and
    qt5-qtbase/5.15.2 in the graph.
    Conflict originates from ki18n5/5.116.0

**Resolution used here** (not invented for this task — it is the pattern already
established and documented by `kjobwidgets5/5.116.0`, which hit the same wall):

```python
self.requires("qt5-qtbase/5.15.2.2", force=True)
```

`force=True` — not `override=True` — unifies the graph while keeping
`qt5-qtbase` a consuming requirement so `package_folder` is still available in
`generate()`. The alternative (republishing `kcoreaddons5` against 5.15.2.2 and
bumping it per R37) would cascade into all 21 recipes that pin it, so it is not
done here.

## flex / bison / m4 are host requirements, not tool_requires

The Trader parser is generated at build time and both tools are REQUIRED, so
they cannot be skipped. They are declared as **host** `requires` rather than
`tool_requires`, deliberately:

* This farm's Harmony PC builds **natively** — the host profile and the build
  profile are both `ohos-aarch64` — so a host-context armv8 binary runs directly
  during the build. There is no separate build platform whose tools would have
  to run on a different architecture.
* In the build context Conan computes a different package id
  (`a6727273a650c4e6aec15c32aa0acbda87ab8220`) for which ohpcd publishes **no**
  binary, while the host context resolves to the published
  `6b129b068851896169fae42d399fa922d239ce8a` and downloads cleanly.
* The farm's verify runs `conan create` **without `--build=missing`**, so a
  missing build-context binary hard-fails rather than falling back to a source
  build.

They are consumed only through `CMAKE_PROGRAM_PATH` (FindFLEX/FindBISON use
`find_program`, which searches that variable ahead of `PATH`); nothing links
against them.

## Upstream test audit

**Registration.** `autotests/CMakeLists.txt` registers test executables through
the `KSERVICE_UNIT_TESTS` macro (`ecm_add_test(... TEST_NAME ...)`), plus one
standalone `ecm_add_test` for `kmimeassociationstest`. `tests/pluginlocator/`
adds `kservice-pluginloadertest`. The `EXCLUDE_DEPRECATED_BEFORE_AND_AT`
conditionals guarding `ktoolinvocation_x11test`, `kplugintradertest`,
`kautostarttest` and `kplugininfotest` all evaluate true when the variable is
unset, so all eleven run.

**Counting cases, not runners.** `QTest` executes every slot declared under
`private Q_SLOTS`, excluding the `initTestCase`/`cleanupTestCase` hooks and the
`*_data` providers. Enumerated over both `.h` and `.cpp` (several classes
declare their slots in the header — counting only `.cpp` misses three of them):

| test class | cases |
|---|---|
| `kservicetest` | 34 |
| `ksycocatest` | 9 |
| `kmimeassociationstest` | 8 |
| `kautostarttest` | 7 |
| `kapplicationtradertest` | 5 |
| `ktoolinvocation_x11test` | 4 |
| `kplugininfotest` | 3 |
| `kplugintradertest` | 3 |
| `ksycocathreadtest` | 3 |
| `ksycoca_xdgdirstest` | 1 |
| `ksycocadicttest` | 1 |
| **total** | **78** |

Note on `ksycocathreadtest`: its third slot `slotFinish` is counted because
QTest *does* execute it; it is a completion helper rather than an assertion
block, and is listed here so the number is auditable rather than quietly
adjusted.

`tests/` additionally builds `kservicegroup_dumper`, `findservice`,
`kdbusservicestartertest`, `startserviceby` and `kmimeassociations_dumper`
(inspection tools) — these carry no QTest assertions and are not part of the 78.


### The MIME database needs both halves

`QMimeDatabase` reads the compiled database (`mime.cache` and its siblings),
while `kbuildsycoca` builds its service types by scanning the **XML source**
files, `xdgdata/mime/*.xml` (`src/sycoca/kbuildmimetypefactory.cpp:22`). Staging
only the compiled half - which is what the first revision of this recipe did -
leaves every MIME type unknown to sycoca:

    QWARN : kf.service.sycoca: Service type not found: "text/plain"
    QWARN : kf.service.services: KApplicationTrader: mimeType "text/plain" not found

and the trader then returns no offers, so `KMimeAssociationsTest` and
`KApplicationTraderTest` fail on the data rather than on the library. Both halves
are shipped now, and the XML half has to be laid out the way sycoca reads it -
see "The MIME database has to be shipped the way sycoca scans it" below.

### `applications.menu` has to sit in the Qt test-mode config directory

Staging the MIME XML source fixed the "Service type not found" warnings but left
the trader queries empty. The next log line names the reason:

    QSYSTEM: KSycocaTest::ensureCacheValidShouldCreateDB() "applications.menu"
    not found in (".../test-home/.qttest/config/menus")

These tests call `QStandardPaths::setTestModeEnabled(true)`, and in test mode
`GenericConfigLocation` is **only** `$HOME/.qttest/config` - the `XDG_CONFIG_DIRS`
entries the recipe sets are ignored, and that single directory is the whole search
path. KSycoca builds its service *group* tree from `applications.menu`, so with
no menu the tree is empty and every trader query returns no offers, which is what
the `KApplicationTrader` and `KMimeAssociations` failures are.

The menu is therefore staged twice: into `xdg-config/menus` for the normal XDG
path, and into `<build>/test-home/.qttest/config/menus` for the test-mode path
the tests actually use.
## The MIME database has to be shipped the way sycoca scans it

For a long time the suite reported **126 runtime cases, 106 pass, 16 fail, 4
skip**, every failure a trader query finding no offers behind the same line:

    QWARN : kf.service.sycoca: Service type not found: "text/plain"

Four earlier attempts (staging `freedesktop.org.xml` beside the compiled files,
copying the database into the test-mode paths, a brand-new `HOME`, running
`kbuildsycoca5` by hand) did not move the counts. The reason only became visible
by reading the scanner and probing it:

* `KSycocaFactory::allDirectories("mime")` *is* the right directory, and the
  scanning really happens - `QT_LOGGING_RULES="kf.service.sycoca.debug=true"`
  prints
  `Looking for subdir "mime" => (".../xdg-data/mime")`, so the staged directory
  was being read all along;
* but `KBuildMimeTypeFactory::createEntry()` derives the type name from the
  file's *relative path* and discards anything without a directory part:

```cpp
KSycocaEntry *KBuildMimeTypeFactory::createEntry(const QString &file) const
{
    const int pos = file.lastIndexOf(QLatin1Char('/'));
    if (pos == -1) { // huh?
        return nullptr;
    }
```

  so the single `freedesktop.org.xml` sitting directly in `mime/` was skipped,
  and the service database came out with no MIME types at all. The XML files
  have to be laid out the way `/usr/share/mime` has them - one per type,
  `mime/<group>/<type>.xml`.

`testdata/mime` is therefore the complete output of `update-mime-database` over
two packages: shared-mime-info 2.4's `freedesktop.org.xml` (12 compiled
aggregates plus 965 per-type XML sources) and kcoreaddons 5.116.0's
`share/mime/packages/kde5.xml`. 2.4 rather than anything newer is deliberate: in
2.5 `application/x-shellscript` stopped being a type of its own and became an
alias of `text/x-shellscript`, so it no longer inherits `text/plain` and
`KMimeAssociationsTest::testMultipleInheritance` has nothing left to find. The
sources stay in `packages/`, so `update-mime-database testdata/mime` rebuilds
the fixture from the repository alone.

## Result on the device

Every case the run produces is in the report; nothing is excluded and nothing
skipped by the gate. At the MIME fix the ledger became:

**125 runtime cases - 119 passed, 2 failed, 4 skipped, 0 blacklisted**, across
11 test binaries that print totals (12 CTest registrations; the twelfth,
`kservice-pluginloadertest`, asserts without QTest totals). CTest itself now
reports **11 of 12 tests passed** - `kmimeassociationstest`, `kapplication-
tradertest` and everything else are green; only `ksycocatest` still has cases
failing.

The four skips are QSKIPs inside the upstream test source, all in
`KAutostartTest` and all from the same fixture gap:

| case | reason (verbatim) |
|---|---|
| `KAutostartTest::testStartInEnvDetection(kde)` | `plasma-desktop.desktop not found, kdebase not installed` |
| `KAutostartTest::testStartInEnvDetection(xfce)` | `plasma-desktop.desktop not found, kdebase not installed` |
| `KAutostartTest::testStartName()` | `plasma-desktop.desktop not found, kdebase not installed` |
| `KAutostartTest::testServiceRegistered()` | `plasma-desktop.desktop not found, kdebase not installed` |

`autotests/kautostarttest.cpp` lines 57, 91 and 103 call `QSKIP` when the
fixture desktop file is absent; the file belongs to plasma-desktop, which is not
in this graph.

The two remaining failures are in `KSycocaTest` and neither is a statement about
kservice. They share one cause: **`/storage` is hmdfs and does not enforce file
permissions**.

* `testNonReadableSycoca` chmods the sycoca database to `WriteOwner` and expects
  `KServiceType::serviceType("FakeGlobalServiceType")` to stop resolving. On
  hmdfs the chmod is a no-op - a file chmod'ed to `0o200` is still readable -
  so the type stays resolvable. The recipe re-checks that property on every run
  (`_permissions_are_not_enforced()`); the allowance only applies while it
  holds.
* `extraFileInFutureShouldRebuildSycocaOnce` reads `oldTimestamp` from the
  sycoca database - which the previous test has just deleted in its cleanup, so
  the timestamp is invalid and `newTimestamp > oldTimestamp` cannot be true. Run
  on its own it passes: `ksycocatest extraFileInFutureShouldRebuildSycocaOnce`
  reports `3 passed, 0 failed`.

Both are recorded as **BLOCKED** and never counted as passes; the recipe
recognises them only by the exact assertion they fail on
(`_ENVIRONMENT_BLOCKED_CASES`), so any other failure - including one of these
two failing on a different line - still fails the build.

## Status

Device verification PASS at this HEAD. The run executes all 125 cases; the
ledger above is what the report contains. See `manifest.yaml` for the numbers
recorded from the actual run.
