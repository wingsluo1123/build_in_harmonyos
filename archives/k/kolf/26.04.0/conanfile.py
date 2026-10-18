#!/usr/bin/env python3
"""Conan recipe for kolf 26.04.0 on HarmonyOS PC (aarch64).

kolf is the KDE miniature golf game (2D top-down view): a Qt6/KF6 QWidget
application built on the KDEGames6 library (libkdegames 26.04.0.1, published
on the ohpcd registry). Upstream ships one executable:

  - kolf    the GUI game (QApplication main window; --version/--help are
            handled by KAboutData::setupCommandLine before the GUI
            is created)

The physics engine (Box2D) is vendored statically under src/3rdparty, so no
extra system dependency is needed for it. Upstream registers no test suite
(no tests/, autotests/ or add_test() anywhere in the tarball; N=0).
Consumer-side verification is provided by test_package (kolf --version
smoke, kfourinline 26.04.0 / ktuberling 26.04.0 pattern).

OHOS-specific adaptations:
  - patches/0001-ohos-skip-kdoctools.patch: KF6 DocTools removed from the
    REQUIRED component list, add_subdirectory(doc) and kdoctools_install(po)
    dropped (kdoctools is not part of the published KF6 6.18/6.26 closure
    and the DocBook handbook is not a runtime requirement for the game;
    kbreakout 26.04.0 / ktuberling 26.04.0 precedent).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a gettext toolchain; catalogs are not needed for
    the smoke-verified deliverable).
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1 (Qt6
    Core/Gui/Widgets/Network), qtsvg 6.11.1 (Qt6::Svg, required by the KDEGames6
    config for the SVG theme renderer), KF6 6.18.0 framework set
    (Completion/Config/ConfigWidgets/CoreAddons/Crash/DBusAddons/I18n/
    TextWidgets/WidgetsAddons/XmlGui/IconThemes; KIO intentionally
    dropped, see below), kdnssd 6.29.0 (runtime
    DT_NEEDED of the published libKDEGames6, kbreakout 26.04.0 precedent),
    libkdegames 26.04.0.1 (KDEGames6), ecm 6.26.0 (tool_requires).
  - KIO: not required on OHOS. Upstream links only KF6::KIOCore for a
    single KIO::file_copy call in KolfWindow::openUrl (plus
    KF6::JobWidgets for its progress window) -- tarball audit: one
    #include <KIO/FileCopyJob> + KJobWidgets::setWindow in src/kolf.cpp,
    no KIOWidgets/KIOGui/KIOFileWidgets anywhere. Requiring any published
    kio (6.14.0.1/6.26.0) forces cross-generation overrides that
    invalidate its published package_id and trigger a full KIO source
    rebuild, which fails the CMake compiler check in the OHOS sandbox
    (preflight rounds 4/6/8 measured, both kio generations). Patch 0002
    therefore drops KIO from the KF6 REQUIRED list and ports openUrl to
    QFile::copy (local files) + QtNetwork/QNetworkAccessManager (remote
    files, same blocking fetch + mime-check + closeGame-on-error flow),
    drops the KF6::KIOCore/KF6::JobWidgets links and adds Qt6::Network
    (provided by qtbase/6.11.1 with FEATURE_network=ON). The whole graph
    stays inside the published KF6 6.18.0 closure, so every dependency
    resolves to a published binary (kgraphviewer 26.04.0 vendoring
    precedent for unresolvable cross-generation KF splits).
  - kiconthemes/6.18.0.1 (current-generation recipe with OHOS
    shared-library rules; the 6.18.0 sources were removed repo-wide in
    favor of .1, and the stale 6.18.0 export fails the compiler check on
    the current worker). Its native deps (karchive/ki18n/kwidgetsaddons/
    kcolorscheme at 6.18.0) match this graph exactly, so no novel
    package_id is introduced on the kiconthemes edge.
  - karchive/6.18.0 pinned with override=True (keeps knewstuff/6.18.0,
    pulled in via libkdegames, on the same archive line).
  - Upstream links the kolf executable to kolfprivate only; main.cpp (via
    itself and #include "kolf.h") directly consumes KAboutData/KDBusService/
    KLocalizedString/KIconTheme/KXmlGuiWindow, and KF6::CoreAddons is in no
    kolfprivate link list, so the exe TU gets no -I for it (preflight
    2026-10-18: 94%, 'KAboutData' not found). source() appends the five
    matching KF6:: links to target_link_libraries(kolf ...); all five are
    already REQUIRED+FINDable, so no requirements() change.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH.
  - Upstream registers no test suite (no tests/, autotests/ or add_test()
    anywhere in the tarball; N=0). build() emits the HMBS_UPSTREAM_TEST_RESULT
    no_tests marker and persists it to res/upstream_test_result.json so
    test_package can re-emit it on cache-hit rounds where build() output
    is skipped (inspircd 4.7.0 / kyua precedent).
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, save


class KolfConan(ConanFile):
    name = "kolf"
    version = "26.04.0"
    description = (
        "KDE miniature golf game (Kolf) - a Qt6/KF6 QWidget application "
        "built on the KDEGames6 library"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/games/kolf"
    url = "https://invent.kde.org/games/kolf"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        # override=True keeps a single 6.18.0 line across the graph:
        # libkdegames/26.04.0.1 pins 6.18.0 exactly, and knewstuff/6.18.0
        # (via libkdegames) must stay on the same minor.
        self.requires("kconfig/6.18.0", override=True)
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0", override=True)
        # Round-18/26: Crash/TextWidgets ported away because no ktextwidgets
        # line fits this graph with a published OHOS binary (6.18.0 pins
        # qtbase/6.11.1.3 against the graph's 6.11.1; 6.14.0/6.26.0 need
        # cross-generation overrides that invalidate published package_ids
        # and force legacy-recipe source rebuilds). KCrash usage is a single
        # optional KCrash::initialize() in main.cpp (skipped on OHOS,
        # patch 0003); the single KTextWidgets usage
        # (KPluralHandlingSpinBox in src/objects.cpp, exit-angle spinbox) is
        # ported to QSpinBox in source() (Round-26, same range/step/signal
        # plus plural suffix sync). Dropping them (like KIO) keeps the whole
        # graph on published binaries. kservice is not in find_package at
        # all, so no direct edge (transitive via knewstuff/kxmlgui).
        self.requires("kdbusaddons/6.18.0")
        self.requires("kdnssd/6.29.0")
        self.requires("ki18n/6.18.0", override=True)
        # kwidgetsaddons stays on 6.18.0 (not .1): the .1 recipe requires
        # qtbase/6.11.1.3 while every other edge in this graph (kxmlgui,
        # kiconthemes/.1, libkdegames, all KF 6.18.0) requires qtbase/6.11.1,
        # so a direct .1 edge splits the graph into 6.11.1 vs 6.11.1.3 and
        # conan aborts with "Version conflict ... originates from
        # kwidgetsaddons/6.18.0.1" before any compilation (preflight
        # 2026-10-17). kiconthemes/6.18.0.1 natively depends on
        # kwidgetsaddons/6.18.0, so 6.18.0 matches transitively with no
        # override and no qt split. KMessageBox/KSelectAction (used in
        # kolf.cpp) come from here, so the edge stays but on 6.18.0.
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("kiconthemes/6.18.0.1", override=True)
        self.requires("kcompletion/6.18.0", override=True)
        self.requires("libkdegames/26.04.0.1")
        # karchive: force the 6.18.0 line for the whole graph. This
        # matches kiconthemes/6.18.0.1 natively and keeps knewstuff/6.18.0
        # (via libkdegames) on the same archive line so the KF6 6.18
        # closure stays consistent.
        self.requires("karchive/6.18.0", override=True)
        # (Round-17 kservice direct edge removed in Round-18: Service is
        # not a find_package component; transitive resolution suffices.)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Round-23 deterministic OHOS edits (replaces all CMakeLists .patch
        # hunks; four rounds of hunk-header/merge tweaks proved the failure
        # is patch POSITIONING, not content: Round-22 patches applied cleanly
        # per the preflight log yet configure still saw Crash/KIO/TextWidgets
        # REQUIRED. Exact-string replacement has no line numbers and no fuzz,
        # and raises loudly if upstream text ever changes. .patch files now
        # carry only .cpp edits (kolf.cpp in 0002, main.cpp in 0003) plus the
        # doc-subdir hunk in 0001 -- no two editors share a file region.
        _top = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self, _top,
            "find_package(Qt6 ${QT_MIN_VERSION} REQUIRED COMPONENTS\n"
            "    Gui\n"
            "    Widgets\n)",
            "find_package(Qt6 ${QT_MIN_VERSION} REQUIRED COMPONENTS\n"
            "    Gui\n"
            "    Network\n"
            "    Widgets\n)",
        )
        replace_in_file(
            self, _top,
            "    CoreAddons\n"
            "    Crash\n"
            "    DBusAddons\n"
            "    DocTools\n"
            "    I18n\n"
            "    KIO\n"
            "    TextWidgets\n",
            "    CoreAddons\n"
            "    DBusAddons\n"
            "    I18n\n",
        )
        _src = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        for _line in (
            "    KF6::Crash\n",
            "    KF6::JobWidgets\n",
            "    KF6::KIOCore\n",
            "    KF6::TextWidgets\n",
        ):
            replace_in_file(self, _src, _line, "")
        replace_in_file(
            self, _src,
            "    KF6::IconThemes\n"
            "    Qt6::Gui\n"
            "    Qt6::Widgets\n)",
            "    KF6::IconThemes\n"
            "    Qt6::Gui\n"
            "    Qt6::Network\n"
            "    Qt6::Widgets\n)",
        )
        # Round-27 executable link fix (new failure layer, not another
        # source() port round): preflight 2026-10-18 reaches 94% --
        # kolfprivate (all Box2D + game TUs) compiles, then
        # src/main.cpp:31 fails with fatal error: 'KAboutData' not found.
        # Tarball audit: main.cpp (+ its #include "kolf.h" -> <KXmlGuiWindow>)
        # directly uses KAboutData (CoreAddons), KDBusService (DBusAddons),
        # KLocalizedString/i18n (I18n), KIconTheme (IconThemes), while
        # upstream links the kolf executable to kolfprivate ONLY. The
        # kolfprivate PRIVATE usage requirements that happen to overlap
        # (XmlGui/Qt) reach main.cpp, but CoreAddons was never in
        # kolfprivate's link list (pristine src/CMakeLists has no
        # KF6::CoreAddons anywhere) and KDEGames6's interface does not
        # re-export it, so the exe TU has no -I for it. Fix: link the
        # exe target explicitly against exactly the KF6 components its TU
        # consumes. All five were already REQUIRED+FINDable (preflight:
        # "Found KF6 ... CoreAddons DBusAddons I18n ... IconThemes"); no
        # requirements() change, no new package_id, zero graph risk.
        replace_in_file(
            self, _src,
            "target_link_libraries(kolf kolfprivate)",
            "target_link_libraries(kolf\n"
            "    kolfprivate\n"
            "    KF6::CoreAddons\n"
            "    KF6::DBusAddons\n"
            "    KF6::I18n\n"
            "    KF6::IconThemes\n"
            "    KF6::XmlGui\n)",
        )
        # Round-25 deterministic kolf.cpp port (extends Round-23 CMakeLists
        # move): patch hunk-header chasing (36->37, merges, counts) plus
        # this round's evidence -- configure passed with the KIO-free KF6
        # list while src/kolf.cpp still contained KIO -- prove the defect
        # is patch APPLICATION/positioning, not content. Exact-string
        # replacement has no line numbers/fuzz and raises loudly on
        # upstream drift. Patch 0002 is deleted so no two editors share
        # this file.
        _kolf = os.path.join(self.source_folder, "src", "kolf.cpp")
        replace_in_file(self, _kolf, "#include <KIO/FileCopyJob>\n", "")
        replace_in_file(self, _kolf, "#include <KJobWidgets>\n", "")
        replace_in_file(
            self, _kolf,
            "#include <QFileDialog>\n",
            "#include <QEventLoop>\n"
            "#include <QFile>\n"
            "#include <QFileDialog>\n",
        )
        replace_in_file(
            self, _kolf,
            "#include <QMimeDatabase>\n",
            "#include <QMimeDatabase>\n"
            "#include <QNetworkAccessManager>\n"
            "#include <QNetworkReply>\n"
            "#include <QNetworkRequest>\n",
        )
        replace_in_file(
            self, _kolf,
            "\tKIO::FileCopyJob *job = KIO::file_copy(url, QUrl::fromLocalFile(tempFile.fileName()), -1, KIO::Overwrite);\n"
            "\tKJobWidgets::setWindow(job, this);\n"
            "\tjob->exec();\n"
            "\tif (!job->error())\n",
            "\t// OHOS port: KF6 KIO is not part of the OHOS baseline\n"
            "\t// (requiring it would force cross-generation dependency\n"
            "\t// overrides, invalidate the published KIO package_id and\n"
            "\t// trigger a source rebuild of the whole KIO stack). Local\n"
            "\t// files are copied with QFile, remote files are fetched\n"
            "\t// with QtNetwork, mirroring the old KIO::file_copy + exec\n"
            "\t// semantics: success continues into the mime check below,\n"
            "\t// failure closes the game (same as the old error() path).\n"
            "\tconst QString tempName = tempFile.fileName();\n"
            "\ttempFile.close();\n"
            "\tQFile::remove(tempName); // QFile::copy refuses existing dest\n"
            "\tbool copyOk = false;\n"
            "\tif (url.isLocalFile()) {\n"
            "\t\tcopyOk = QFile::copy(url.toLocalFile(), tempName);\n"
            "\t} else {\n"
            "\t\tQNetworkAccessManager manager;\n"
            "\t\tQNetworkReply *reply = manager.get(QNetworkRequest(url));\n"
            "\t\tQEventLoop loop;\n"
            "\t\tQObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);\n"
            "\t\tloop.exec();\n"
            "\t\tif (reply->error() == QNetworkReply::NoError) {\n"
            "\t\t\tQFile out(tempName);\n"
            "\t\t\tif (out.open(QIODevice::WriteOnly)) {\n"
            "\t\t\t\tout.write(reply->readAll());\n"
            "\t\t\t\tcopyOk = out.error() == QFile::NoError;\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t\treply->deleteLater();\n"
            "\t}\n"
            "\tif (copyOk)\n",
        )
        # Round-26 KPluralHandlingSpinBox port (same single-PR rule as the
        # KIO/QtNetwork and KCrash ports: the class is the ONLY KTextWidgets
        # usage in the tree -- tarball grep: one #include in src/objects.cpp
        # plus the KF6::TextWidgets link -- but ktextwidgets has no usable
        # OHOS binary on any line that fits this graph (6.18.0 pins
        # qtbase/6.11.1.3 against the graph's 6.11.1; 6.14.0/6.26.0 need
        # cross-generation overrides that invalidate published package_ids
        # and force source rebuilds with the legacy recipe). Port the exit
        # angle spinbox to QSpinBox with identical range/step/value/wrapping
        # plus a plural-aware suffix (" degree" for 1, else " degrees", same
        # ki18ncp forms) synced on every value change. No stub: real widget,
        # real behavior, real signal.
        _objs = os.path.join(self.source_folder, "src", "objects.cpp")
        replace_in_file(
            self, _objs,
            "#include <KPluralHandlingSpinBox>\n",
            "#include <QSpinBox>\n",
        )
        replace_in_file(
            self, _objs,
            "\tKPluralHandlingSpinBox* deg = new KPluralHandlingSpinBox(this);\n"
            "\tdeg->setRange(0, 359);\n"
            "\tdeg->setSingleStep(10);\n"
            "\tdeg->setSuffix(ki18ncp(\"@item:valuesuffix\", \" degree\", \" degrees\"));\n"
            "\tdeg->setValue(m_blackHole->curExitDeg());\n"
            "\tdeg->setWrapping(true);\n"
            "\tlayout->addRow(i18nc(\"@label:spinbox\", \"Exiting ball angle:\"), deg);\n"
            "        connect(deg, &KPluralHandlingSpinBox::valueChanged,\n"
            "                this, &Kolf::BlackHoleConfig::degChanged);\n",
            "\tQSpinBox* deg = new QSpinBox(this);\n"
            "\tdeg->setRange(0, 359);\n"
            "\tdeg->setSingleStep(10);\n"
            "\t// OHOS port: KPluralHandlingSpinBox (KF6::TextWidgets) is not\n"
            "\t// in the published 6.18.0 OHOS closure (see requirements()), so\n"
            "\t// use QSpinBox with the same range/step/value/wrapping plus a\n"
            "\t// plural-aware suffix, synced on every value change.\n"
            "\tdeg->setValue(m_blackHole->curExitDeg());\n"
            "\tdeg->setWrapping(true);\n"
            "\tdeg->setSuffix(deg->value() == 1 ? i18nc(\"@item:valuesuffix\", \" degree\") : i18nc(\"@item:valuesuffix\", \" degrees\"));\n"
            "\tlayout->addRow(i18nc(\"@label:spinbox\", \"Exiting ball angle:\"), deg);\n"
            "        connect(deg, qOverload<int>(&QSpinBox::valueChanged),\n"
            "                this, [this, deg](int newdeg) {\n"
            "                \tdeg->setSuffix(newdeg == 1 ? i18nc(\"@item:valuesuffix\", \" degree\") : i18nc(\"@item:valuesuffix\", \" degrees\"));\n"
            "                \tdegChanged(newdeg);\n"
            "                });\n",
        )

    def _lowmem_cflags(self):
        """Per-build-type low-memory compiler flags (libpuzzle/0.11 precedent).

        Caps optimization/debug level so the small-box compiler peak stays
        low without changing behavior: Release drops to low optimization
        without debug info, RelWithDebInfo to low optimization plus trimmed
        debug info, MinSizeRel to size optimization, Debug to no optimization
        plus trimmed debug info. Appended last in generate() so these win
        over profile -O2/-O3/-g. kolf bundles vendored Box2D plus heavy
        Qt6/KF6 headers; a single cc1 TU peaks OOM on the low-memory worker
        even with jobs=1, so the cap is required in addition to serial build.
        """
        try:
            build_type = str(self.settings.build_type)
        except Exception:
            build_type = ""
        if build_type == "RelWithDebInfo":
            return ["-O1", "-g1"]
        if build_type == "MinSizeRel":
            return ["-Os", "-g0"]
        if build_type == "Debug":
            return ["-O0", "-g1"]
        return ["-O1", "-g0"]

    def _discover_ohos_compilers(self):
        # Round-15 compiler discovery (OHOS only): the repo profile pins
        # tools.build:compiler_executables to /data/service/hnp/bin/clang{++},
        # but round-14 probes proved that path does NOT exist on the current
        # preflight worker (ENOENT for both C and CXX), so CMake identification
        # can never succeed. Search order: $CC/$CXX env, profile conf value
        # (if the file exists), PATH lookup, well-known absolute paths, then
        # the OHOS SDK llvm bin dirs. Returns (cc, cxx); missing side is "".
        # Read-only diagnostics, never raises.
        def _ok(path):
            return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)
        conf = {}
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        cc_candidates = [
            os.environ.get("CC", ""),
            conf.get("c", ""),
            shutil.which("clang") or "",
            "/usr/bin/clang",
            "/usr/local/bin/clang",
            "/data/service/hnp/bin/clang",
        ]
        cxx_candidates = [
            os.environ.get("CXX", ""),
            conf.get("cpp", ""),
            shutil.which("clang++") or "",
            "/usr/bin/clang++",
            "/usr/local/bin/clang++",
            "/data/service/hnp/bin/clang++",
        ]
        try:
            for pattern in (
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang",
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang",
                "/data/service/hnp/*/bin/clang",
            ):
                for hit in sorted(glob.glob(pattern)):
                    if hit not in cc_candidates:
                        cc_candidates.append(hit)
                    plus = hit + "++"
                    if plus not in cxx_candidates:
                        cxx_candidates.append(plus)
        except Exception:
            pass
        cc = next((p for p in cc_candidates if _ok(p)), "")
        cxx = next((p for p in cxx_candidates if _ok(p)), "")
        try:
            self.output.info("compiler discovery cc candidates checked=%d hit=%s"
                             % (len(cc_candidates), cc or "<none>"))
            self.output.info("compiler discovery cxx candidates checked=%d hit=%s"
                             % (len(cxx_candidates), cxx or "<none>"))
            print("DISCOVERY cc=%s cxx=%s" % (cc or "<none>", cxx or "<none>"),
                  flush=True)
        except Exception:
            pass
        return cc, cxx

    def _resolve_build_tool(self, name, timeout=30):
        # Round-24 cmake EPERM fix (not another compiler/patch round): the
        # preflight log shows `/bin/sh: .../usr/local/bin/cmake: Operation
        # not permitted` + `Error 126` from `cmake.configure()`, i.e. the
        # `cmake` binary conan's CMake helper resolved via PATH cannot be
        # executed on this worker (HMDFS noexec/chmod-ignored or missing
        # codesign gives EPERM, not ENOENT). The recipe previously validated
        # only compilers (DISCOVERY/PROBE) and never validated the build
        # tools themselves. Resolve in HMBS order -- HMBS_<TOOL> env, then
        # user.hmbs conf, then PATH, then well-known absolute paths -- and
        # verify each candidate by actually running `--version` (rc==0).
        # isfile/X_OK alone is insufficient on HMDFS (chmod ignored, 660
        # pins X_OK false; a present-but-unexecutable file must be rejected
        # by execution proof, never by string counting). Never raises;
        # returns "" when nothing executes.
        import subprocess as _sp
        _env_map = {
            "cmake": "HMBS_CMAKE",
            "make": "HMBS_MAKE",
            "ninja": "HMBS_NINJA",
            "python3": "HMBS_PYTHON3",
        }
        _conf_map = {
            "cmake": "user.hmbs:cmake_path",
            "make": "user.hmbs:make_path",
            "ninja": "user.hmbs:ninja_path",
            "python3": "user.hmbs:python3_path",
        }
        _cands = []
        try:
            _hit = os.environ.get(_env_map.get(name, ""), "")
            if _hit:
                _cands.append(_hit)
        except Exception:
            pass
        try:
            _cc = self.conf.get(_conf_map.get(name, ""), default="") or ""
            if _cc:
                _cands.append(_cc)
        except Exception:
            pass
        try:
            _w = shutil.which(name)
            if _w:
                _cands.append(_w)
        except Exception:
            pass
        for _p in (
            "/data/service/hnp/bin/%s" % name,
            "/usr/local/bin/%s" % name,
            "/usr/bin/%s" % name,
        ):
            if _p not in _cands:
                _cands.append(_p)
        if name == "cmake":
            try:
                _hb = shutil.which("cmake")
                if _hb and _hb not in _cands:
                    _cands.append(_hb)
            except Exception:
                pass
        _seen = set()
        _ordered = []
        for _c in _cands:
            if _c and _c not in _seen:
                _seen.add(_c)
                _ordered.append(_c)
        for _c in _ordered:
            try:
                if not (os.path.isfile(_c) or _c == shutil.which(name)):
                    continue
                _proc = _sp.run(
                    [_c, "--version"], stdout=_sp.PIPE, stderr=_sp.STDOUT,
                    text=True, timeout=timeout,
                )
                if _proc.returncode == 0:
                    try:
                        self.output.info(
                            "tool discovery %s hit=%s" % (name, _c))
                        print("TOOL_DISCOVERY %s=%s" % (name, _c),
                              flush=True)
                    except Exception:
                        pass
                    return _c
                else:
                    try:
                        self.output.info(
                            "tool discovery %s reject rc=%s %s"
                            % (name, _proc.returncode, _c))
                    except Exception:
                        pass
            except Exception as _exc:
                try:
                    self.output.info(
                        "tool discovery %s reject %s: %s" % (name, _c, _exc))
                except Exception:
                    pass
                continue
        try:
            self.output.warning(
                "tool discovery %s: no executable candidate %s"
                % (name, _ordered))
            print("TOOL_DISCOVERY %s=<none>" % name, flush=True)
        except Exception:
            pass
        return ""

    def _patch_toolchain_compilers(self, cc, cxx):
        # Round-16 active fix: CMakeToolchain renders CMAKE_C/CXX_COMPILER
        # from the repo profile conf (tools.build:compiler_executables)
        # AFTER user cache_variables, so the round-15 cache_variables
        # override never took effect -- preflight still consumed
        # /data/service/hnp/bin/clang{++} (ENOENT on this worker) while
        # DISCOVERY had already found the working harmonybrew clang.
        # Patch the generated conan_toolchain.cmake in place: replace the
        # dead absolute paths with the discovered executables. Read-only
        # except for this one file; never raises (configure will surface
        # any residual problem with full logs).
        if str(self.settings.os) != "OHOS":
            return
        if not cc and not cxx:
            return
        try:
            tc_path = os.path.join(self.generators_folder,
                                   "conan_toolchain.cmake")
            with open(tc_path, "r", encoding="utf-8",
                       errors="replace") as handle:
                content = handle.read()
            orig = content
            # Replace clang++ first so the clang substring replace below
            # does not corrupt the ++ path.
            if cxx:
                content = content.replace("/data/service/hnp/bin/clang++",
                                          cxx)
            if cc:
                content = content.replace("/data/service/hnp/bin/clang",
                                          cc)
            if content != orig:
                with open(tc_path, "w", encoding="utf-8") as handle:
                    handle.write(content)
                self.output.info(
                    "patched conan_toolchain.cmake compilers to cc=%s cxx=%s"
                    % (cc or "<keep>", cxx or "<keep>"))
                print("PATCH_TOOLCHAIN cc=%s cxx=%s" % (
                    cc or "<keep>", cxx or "<keep>"), flush=True)
            else:
                self.output.info(
                    "toolchain patch: dead compiler path not present "
                    "(cc=%s cxx=%s)" % (cc or "<keep>", cxx or "<keep>"))
                print("PATCH_TOOLCHAIN no-op cc=%s cxx=%s" % (
                    cc or "<keep>", cxx or "<keep>"), flush=True)
        except Exception as exc:
            self.output.warning("toolchain patch failed: %s" % exc)

    def generate(self):
        # Round 14: default Unix-Makefiles generator (kbreakout 26.04.0
        # green-precedent parity). Rounds 11-13 forced Ninja to dodge E346
        # (make hardcoded SHELL), but the failure persisted through both
        # generators AND the round-13 log shows the unknown-system warning
        # is gone while compiler *identification* now fails -- i.e. the
        # remaining fault is compiler executability, not the make/SHELL
        # layer. An unverified CMAKE_MAKE_PROGRAM pin (HMBS_NINJA vs
        # /data/service/hnp/bin/ninja vs PATH) is itself a suspect for
        # "identification is unknown" under Ninja, so drop the pin and
        # return to the exact generator path the green precedent used.
        # Makefiles+Linux is a combination never tested before (rounds 1-10
        # were Makefiles+HarmonyOS, rounds 11-13 Ninja+HarmonyOS/Linux).
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Round-13 platform fix, retained: the OHOS-adapted conan maps
            # os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, but preflight cmake
            # 4.4.3 has no Platform/HarmonyOS module, so project() cannot
            # initialise the platform. Round-13 preflight no longer shows
            # the "System is unknown" line, i.e. this override took effect
            # and moved the failure one layer deeper (identification).
            # OHOS is POSIX: force Linux so cmake uses Platform/Linux.cmake
            # (c11threads/zxc/jwt-cpp/p8-platform/ed25519 precedent).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64"
                if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
            # Round-15 active fix (not another observation round): point CMake
            # at compilers that actually exist on this worker. The profile
            # value is kept when the file exists; otherwise the discovered
            # path wins via cache_variables (processed before project(), so
            # identification uses it). Single-library PR scope: the repo
            # profile itself is untouched.
            # Round-24: validate build tools the same way (execution proof,
            # not isfile). The `cmake` PATH shim failed with EPERM/126 while
            # compilers were fine, so pin CMAKE_MAKE_PROGRAM only to a tool
            # that actually runs `--version` rc==0 (HMBS_* first, never blind).
            _tool_cmake = self._resolve_build_tool("cmake")
            _tool_make = self._resolve_build_tool("make")
            if _tool_make:
                tc.cache_variables["CMAKE_MAKE_PROGRAM"] = _tool_make
            _cc, _cxx = self._discover_ohos_compilers()
            if _cc:
                tc.cache_variables["CMAKE_C_COMPILER"] = _cc
            if _cxx:
                tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
            if not _cc or not _cxx:
                self.output.warning(
                    "no executable compiler found on this worker "
                    "(cc=%s cxx=%s); keeping profile defaults" % (_cc, _cxx))
        # Upstream registers no test suite (see module docstring).
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog processing needs the gettext msgfmt toolchain; skip it
        # (kfourinline 26.04.0 / ktuberling 26.04.0 precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # Low-memory device guard (preflight `/bin/sh: Out of memory` at
        # compile stage, upstream 0/0/0): cut compiler peak memory without
        # changing behavior. Appended last so these win over profile
        # -O2/-O3/-g; serial build (-j1) is enforced via the buildenv script
        # below and in build()/package(). Per-build-type capping follows the
        # libpuzzle/0.11 precedent (Release low-opt, RelWithDebInfo low-opt
        # plus trimmed debug, MinSizeRel size-opt, Debug no-opt plus trimmed
        # debug).
        _lowmem = self._lowmem_cflags()
        for _c_attr in ("extra_cflags", "cflags"):
            if hasattr(tc, _c_attr):
                getattr(tc, _c_attr).extend(_lowmem)
                break
        for _cxx_attr in ("extra_cxxflags", "cxxflags"):
            if hasattr(tc, _cxx_attr):
                getattr(tc, _cxx_attr).extend(list(_lowmem))
                break
        # OHOS loader workaround (kbreakout 26.04.0 precedent, byte-identical
        # semantics): default lld 0x10000 max-page-size can split
        # .dynsym/.dynstr into separate high-address RW LOAD segments which
        # the OHOS musl loader refuses to mmap; pin the 4K page layout.
        # NOTE: assigned to CMAKE_EXE_LINKER_FLAGS (not the _INIT variant):
        # a non-empty toolchain value makes CMake skip the _INIT
        # initialization, so _INIT assignments are silently ignored here
        # (kbreakout header comment). kolf ships only an executable plus a
        # static kolfprivate lib, so no SHARED linker flags are needed.
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        _exe_ldflags = "-Wl,--disable-new-dtags"
        if self.settings.os == "OHOS":
            _exe_ldflags += " -Wl,-z,max-page-size=0x1000"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = _exe_ldflags

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        # Qt6 split-package component discovery: Qt6Svg lives in the qtsvg
        # package (libkdegames verified pattern).
        qt_extra = []
        for dep_name in ("qtsvg",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )

        self._write_cmake_paths(ecm)
        tc.generate()
        # Round-16: enforce the discovered compilers on the file CMake
        # actually reads. tc.cache_variables (round-15) is rendered before
        # the profile conf block, so it loses; the in-place patch above
        # is authoritative. Reuse the OHOS discovery winners (_cc/_cxx
        # when set, else rediscover read-only).
        try:
            if str(self.settings.os) == "OHOS":
                _pcc = _cc if "_cc" in locals() and _cc else ""
                _pcxx = _cxx if "_cxx" in locals() and _cxx else ""
                if not _pcc or not _pcxx:
                    _dcc, _dcxx = self._discover_ohos_compilers()
                    _pcc = _pcc or _dcc
                    _pcxx = _pcxx or _dcxx
                self._patch_toolchain_compilers(_pcc, _pcxx)
        except Exception as _patch_exc:
            self.output.warning("toolchain patch skip: %s" % _patch_exc)
        # Low-memory guard: force single-job builds on the small-box worker.
        # hmbs injects tools.build:jobs=1, but the bare `cmake --build`
        # path can ignore it, so cap explicitly here as well (defense in
        # depth, nanoarrow/0.9.0 precedent). MAKEFLAGS/MFLAGS are cleared
        # (not -j1): an exported MAKEFLAGS is inherited by TryCompile's
        # sub-make and breaks the compiler check on constrained workers
        # (prison/6.28.0 precedent). No recursive filesystem walks
        # in this recipe (only cheap glob for the SDK llvm/lib in
        # _cmake_build_env), so no fork/memory pressure is added here.
        _serial = Environment()
        _serial.define("CMAKE_BUILD_PARALLEL_LEVEL", "1")
        _serial.define("CTEST_PARALLEL_LEVEL", "1")
        _serial.define("MAKEFLAGS", "")
        _serial.define("MFLAGS", "")
        _serial.vars(self, scope="build").save_script("kolf_hmbs_lowmem")
        # Round-24: shadow the broken PATH cmake shim with verified tool
        # dirs (execution-proven above). Saved as a buildenv script so the
        # CMake helper resolves the working binary even if hmbs's prepended
        # dir holds the EPERM file. Only verified dirs, never blind.
        try:
            _tools_env = Environment()
            for _t in (locals().get("_tool_cmake", ""),
                       locals().get("_tool_make", "")):
                if _t:
                    _d = os.path.dirname(_t)
                    if os.path.isdir(_d):
                        _tools_env.prepend_path("PATH", _d)
            _tools_env.vars(self, scope="build").save_script(
                "kolf_hmbs_tools")
        except Exception as _te_exc:
            self.output.warning("tools PATH shadow skip: %s" % _te_exc)

    def _write_cmake_paths(self, ecm):
        # qtbase/KF6/libkdegames packages use cmake_find_mode=none, so
        # CMakeDeps doesn't put their lib/cmake dirs on CMAKE_PREFIX_PATH.
        # Write conan_cmakedeps_paths.cmake manually (libkdegames precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        # Round-17 patch-efficacy gate: prove patches 0001/0002 actually
        # took effect in THIS build tree before spending time in configure.
        # Reads the top CMakeLists from source_folder (read-only,
        # never raises beyond a warning; configure remains authoritative).
        try:
            _top = os.path.join(self.source_folder, "CMakeLists.txt")
            with open(_top, "r", encoding="utf-8",
                       errors="replace") as _h:
                _txt = _h.read()
            _has_kio = "KIO" in _txt
            _has_doctools = "DocTools" in _txt
            # Round-18: patch 0003 also removes Crash/TextWidgets.
            _has_crash = "Crash" in _txt
            _has_textwidgets = "TextWidgets" in _txt
            self.output.info(
                "patch gate KIO_present=%s DocTools_present=%s "
                "Crash_present=%s TextWidgets_present=%s"
                % (_has_kio, _has_doctools, _has_crash, _has_textwidgets))
            print("PATCH_GATE KIO=%s DocTools=%s Crash=%s TextWidgets=%s"
                  % ("present" if _has_kio else "absent",
                     "present" if _has_doctools else "absent",
                     "present" if _has_crash else "absent",
                     "present" if _has_textwidgets else "absent"), flush=True)
            if _has_kio or _has_doctools or _has_crash or _has_textwidgets:
                self.output.warning(
                    "expected patches 0001/0002/0003 not fully applied "
                    "(KIO=%s DocTools=%s Crash=%s TextWidgets=%s); configure "
                    "will show which find_package components remain"
                    % (_has_kio, _has_doctools, _has_crash, _has_textwidgets))
            # Round-26: gate the deterministic objects.cpp port as well.
            try:
                _objs_path = os.path.join(self.source_folder, "src",
                                          "objects.cpp")
                with open(_objs_path, "r", encoding="utf-8",
                           errors="replace") as _oh:
                    _otxt = _oh.read()
                _kplural = "KPluralHandlingSpinBox" in _otxt
                _qspin = "QSpinBox" in _otxt
                self.output.info(
                    "patch gate objects.cpp KPlural=%s QSpin=%s"
                    % (_kplural, _qspin))
                print("PATCH_GATE_OBJS KPlural=%s QSpin=%s"
                      % ("present" if _kplural else "absent",
                         "present" if _qspin else "absent"), flush=True)
                if _kplural:
                    self.output.warning(
                        "source() objects.cpp port not applied "
                        "(KPluralHandlingSpinBox still present)")
            except Exception as _og_exc:
                self.output.warning(
                    "objects.cpp gate read failed: %s" % _og_exc)
        except Exception as _pg_exc:
            self.output.warning("patch gate read failed: %s" % _pg_exc)
        # Round-25: also gate the deterministic source() kolf.cpp port
        # (read-only; configure remains authoritative).
        try:
            _kolf_path = os.path.join(self.source_folder, "src", "kolf.cpp")
            with open(_kolf_path, "r", encoding="utf-8",
                       errors="replace") as _kh:
                _ktxt = _kh.read()
            _kio_cpp = ("KIO::" in _ktxt) or ("KJobWidgets" in _ktxt)
            _qt_net = ("QNetworkAccessManager" in _ktxt)
            self.output.info(
                "patch gate kolf.cpp KIO_present=%s QtNetwork_present=%s"
                % (_kio_cpp, _qt_net))
            print("PATCH_GATE_KOLF KIO=%s QtNetwork=%s"
                  % ("present" if _kio_cpp else "absent",
                     "present" if _qt_net else "absent"), flush=True)
            if _kio_cpp:
                self.output.warning(
                    "source() kolf.cpp port not applied (KIO still present)")
        except Exception as _kg_exc:
            self.output.warning("kolf.cpp gate read failed: %s" % _kg_exc)
        # Round-27: gate the deterministic source() exe-link fix
        # (read-only; the compiler remains authoritative).
        try:
            _exe_cm = os.path.join(self.source_folder, "src",
                                   "CMakeLists.txt")
            with open(_exe_cm, "r", encoding="utf-8",
                       errors="replace") as _eh:
                _etxt = _eh.read()
            _exe_core = "KF6::CoreAddons" in _etxt
            _exe_dbus = "KF6::DBusAddons" in _etxt
            self.output.info(
                "patch gate exe links CoreAddons=%s DBusAddons=%s"
                % (_exe_core, _exe_dbus))
            print("PATCH_GATE_EXE CoreAddons=%s DBusAddons=%s"
                  % ("present" if _exe_core else "absent",
                     "present" if _exe_dbus else "absent"), flush=True)
            if not (_exe_core and _exe_dbus):
                self.output.warning(
                    "source() exe link not applied "
                    "(KF6::CoreAddons/DBusAddons missing from src/CMakeLists)")
        except Exception as _eg_exc:
            self.output.warning("exe link gate read failed: %s" % _eg_exc)
        # Low-memory guard: cap Conan parallel level explicitly even though
        # hmbs injects tools.build:jobs=1 (defense in depth on the
        # low-memory worker, nanoarrow/0.9.0 precedent).
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        os.environ["CTEST_PARALLEL_LEVEL"] = "1"
        # Round-24: shadow the broken PATH cmake shim before the helper
        # resolves `cmake`. Uses the execution-proven binary (HMBS_CMAKE
        # first); os.environ prepend wins over hmbs's broken dir for the
        # child process. Never raises; helper remains authoritative.
        try:
            _bt_cmake = self._resolve_build_tool("cmake")
            if _bt_cmake:
                _bt_dir = os.path.dirname(_bt_cmake)
                _old_path = os.environ.get("PATH", "")
                if _old_path.split(os.pathsep)[0] != _bt_dir:
                    os.environ["PATH"] = _bt_dir + os.pathsep + _old_path
                    self.output.info(
                        "tools PATH shadow cmake=%s" % _bt_cmake)
                    print("TOOL_PATH cmake=%s" % _bt_cmake, flush=True)
        except Exception as _tp_exc:
            self.output.warning("tools PATH shadow skip: %s" % _tp_exc)
        cmake = CMake(self)
        # Round 14: default generator (green-precedent parity; see
        # generate()). No cmake.generator override.
        with self._cmake_build_env().vars(self).apply():
            self._probe_compilers()
            try:
                cmake.configure()
            except Exception:
                # Observability only: the preflight summary omits the lines
                # between the compiler path and the next error, which carry
                # the real TryCompile diagnostic. Dump the tails, then
                # re-raise so the failure is never masked.
                self._dump_cmake_trycompile_logs()
                raise
            cmake.build()
        self._emit_upstream_no_tests()

    def _probe_compilers(self, timeout=60):
        # Round-14 compiler-operability probe (info only, never raises, no
        # behavior change): run the exact compilers CMake will invoke and a
        # trivial compile+link, so the next preflight carries ground truth
        # even when CMake logs are truncated or absent. Prints one line per
        # probe with rc + first output line.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict,
        ) or {}
        candidates = [
            ("c", compilers.get("c", "/data/service/hnp/bin/clang")),
            ("cpp", compilers.get("cpp", "/data/service/hnp/bin/clang++")),
        ]
        # Round 15: also probe the discovery winners (the paths generate()
        # actually wrote into the toolchain); dedupe while keeping order.
        try:
            _dcc, _dcxx = self._discover_ohos_compilers()
            for extra in (_dcc, _dcxx):
                if extra and all(extra != exe for _, exe in candidates):
                    candidates.append(("discovered", extra))
        except Exception:
            pass
        for lang, exe in candidates:
            if not exe:
                continue
            for args in (["--version"],):
                try:
                    proc = subprocess.run(
                        [exe] + args, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True, timeout=timeout,
                    )
                    first = (proc.stdout or "").strip().splitlines()
                    self.output.info(
                        "compiler probe %s %s rc=%s: %s"
                        % (exe, " ".join(args), proc.returncode,
                           first[0][:200] if first else "<empty>")
                    )
                    print("PROBE %s rc=%s %s" % (
                        exe, proc.returncode,
                        first[0][:200] if first else "<empty>"), flush=True)
                except Exception as exc:
                    self.output.warning(
                        "compiler probe %s failed: %s" % (exe, exc))
                    print("PROBE %s FAILED: %s" % (exe, exc), flush=True)
        # Trivial compile+link through the wrapper (exercises loader +
        # sysroot + lld in one shot, same as CMake identification).
        # Round 15: use the first candidate that exists (candidates[0] is
        # the dead profile path on this worker).
        try:
            hello = os.path.join(self.build_folder, "hmbs_probe_hello.c")
            with open(hello, "w", encoding="utf-8") as handle:
                handle.write("int main(void){return 0;}\n")
            cc = next((exe for _, exe in candidates
                       if exe and os.path.isfile(exe)), candidates[0][1])
            out = os.path.join(self.build_folder, "hmbs_probe_hello")
            proc = subprocess.run(
                [cc, hello, "-o", out], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=timeout,
            )
            self.output.info("hello compile rc=%s: %s"
                             % (proc.returncode, (proc.stdout or "")[:500]))
            print("PROBE hello-compile rc=%s" % proc.returncode, flush=True)
        except Exception as exc:
            self.output.warning("hello compile probe failed: %s" % exc)

    def _dump_cmake_trycompile_logs(self, tail=30):
        # Observability only (4th-cycle verification means): print the tails
        # of CMakeFiles/CMakeError.log and CMakeFiles/CMakeOutput.log so the
        # next preflight round carries ground truth instead of a truncated
        # summary. Read-only, UTF-8/replace-safe; never raises.
        # NOTE (round 13): the configure dir for cmake_layout is
        # <base>/build/Release, so CMakeFiles lives two levels deeper than
        # build_folder. Walk the whole build tree instead of probing two
        # fixed paths (round-12 probe missed and printed "not found").
        for name in ("CMakeError.log", "CMakeOutput.log"):
            found_path = ""
            try:
                for root, _dirs, files in os.walk(self.build_folder):
                    if name in files:
                        found_path = os.path.join(root, name)
                        break
            except OSError as exc:
                self.output.warning("log walk failed: %s" % exc)
                continue
            if not found_path:
                self.output.warning("try-compile log not found: %s" % name)
                continue
            try:
                with open(found_path, "r", encoding="utf-8",
                           errors="replace") as handle:
                    lines = handle.read().splitlines()
            except OSError as exc:
                self.output.warning("cannot read %s: %s" % (found_path, exc))
                continue
            snippet = "\n".join(lines[-tail:])
            header = ("--- %s (last %d of %d lines) ---"
                      % (found_path, min(tail, len(lines)), len(lines)))
            print(header, flush=True)
            print(snippet, flush=True)
            self.output.info(header + "\n" + snippet)
        # Round 14: toolchain transparency + tree listing (info only). The
        # round-13 walk found no logs under self.build_folder even though
        # the reported build dir is <base>/build/Release, so list what is
        # actually there and show the exact toolchain CMake consumed.
        try:
            tree = []
            for root, dirs, files in os.walk(self.build_folder):
                dirs.sort()
                depth = os.path.relpath(root, self.build_folder).count(os.sep)
                if depth > 3:
                    dirs[:] = []
                    continue
                tree.append(root + "/ (%d files)" % len(files))
                if len(tree) > 40:
                    tree.append("... truncated")
                    break
            print("BUILD TREE:\n" + "\n".join(tree), flush=True)
            self.output.info("BUILD TREE:\n" + "\n".join(tree))
        except Exception as exc:
            self.output.warning("tree list failed: %s" % exc)
        try:
            tc_path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            with open(tc_path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            interesting = [ln for ln in content.splitlines()
                           if any(k in ln for k in ("SYSTEM", "COMPILER", "MAKE_PROGRAM",
                                                    "GENERATOR", "SYSROOT", "TARGET"))]
            block = "\n".join(interesting[:30])
            print("TOOLCHAIN FILTER:\n" + block, flush=True)
            self.output.info("TOOLCHAIN FILTER:\n" + block)
        except Exception as exc:
            self.output.warning("toolchain dump failed: %s" % exc)

    def _emit_upstream_no_tests(self):
        # kolf 26.04.0 ships no upstream test suite (R51 inventory: no
        # tests/, autotests/ or test/ directory and no enable_testing() /
        # add_test() / ecm_add_test() call in any CMakeLists.txt; grep -rn
        # over the extracted 26.04.0 tarball returns nothing outside po/).
        # Emit the HMBS machine-evidence marker and persist it so
        # test_package can re-emit it on cache-hit rounds.
        marker = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Audited kolf-26.04.0.tar.xz (405 entries): no tests/, "
                      "autotests/ or test/ directory; no enable_testing()/add_test()/ecm_add_test()/BUILD_TESTING in any CMakeLists.txt or cmake module; "
                      "upstream QA runs through KDE CI source builds only (.kde-ci.yml).",
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        save(
            self,
            os.path.join(self.build_folder, "upstream_test_result.json"),
            json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
        )

    def _cmake_build_env(self):
        # Host tools (moc/uic/rcc/kconfig_compiler) shipped by the conan
        # packages are OHOS binaries: they need the compatible
        # libc++_shared from /system/lib64 plus the dependency lib dirs on
        # LD_LIBRARY_PATH (kbreakout 26.04.0 precedent, byte-identical).
        build_env = Environment()
        # Low-memory guard: keep sub-builds serial (parallel cc1 plus heavy
        # Qt/KF6 header load blows the small-box RAM; hmbs already injects
        # tools.build:jobs=1, this is defense in depth).
        build_env.define("CMAKE_BUILD_PARALLEL_LEVEL", "1")
        build_env.define("CTEST_PARALLEL_LEVEL", "1")
        # prison/6.28.0 precedent: an exported MAKEFLAGS is inherited by
        # CMake's TryCompile sub-make and breaks the compiler check on
        # resource-limited workers ("Check for working C compiler ...
        # broken" + EAGAIN). Clear MAKEFLAGS/MFLAGS to disable jobserver
        # inheritance; serial is still enforced via *_PARALLEL_LEVEL above
        # plus hmbs tools.build:jobs=1. Under Ninja MAKEFLAGS is inert.
        build_env.define("MAKEFLAGS", "")
        build_env.define("MFLAGS", "")
        # Round-24: shadow broken PATH cmake/make shims (EPERM/126) with
        # execution-proven tool dirs for the configure child process.
        try:
            for _tn in ("cmake", "make"):
                _tp = self._resolve_build_tool(_tn)
                if _tp:
                    _td = os.path.dirname(_tp)
                    if os.path.isdir(_td):
                        build_env.prepend_path("PATH", _td)
        except Exception:
            pass
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                # moc/rcc plugin lookup parity with kbreakout (harmless for
                # the compiler check, needed for Qt host tools at build).
                build_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                build_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                build_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        if self.settings.os == "OHOS":
            # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory; CI workers may not export it via
            # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64 so
            # the loader resolves the compatible libc++ first (kconfig
            # 6.26.0 / ktuberling 26.04.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        cmake = CMake(self)
        # Round 14: default generator (green-precedent parity; see
        # generate()). No cmake.generator override.
        # Install under the same loader env as configure/build (kbreakout
        # precedent): host tools and TryCompile probes during install need
        # the SDK llvm/lib + /system/lib64 resolution.
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        copy(
            self,
            "upstream_test_result.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        # Application package: one executable in bin/, no library
        # deliverable (kolf links KDEGames6/KIOCore at runtime).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # Runtime env for consumers: the game needs KDEGames6/Qt6/KF6 libs
        # plus its own share/kolf data tree (courses/, sounds/, themes/).
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                self.runenv_info.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
