#!/usr/bin/env python3
"""Conan recipe for krunner5 5.116.0 (KDE Frameworks 5 / Qt5) on HarmonyOS PC.

Builds KRunner (libKF5Runner), the KDE Frameworks 5 parallelized query
framework: the plugin side (AbstractRunner) search providers implement, and
the UI side (RunnerManager, RunnerContext, QueryMatch, RunnerSyntax) that
drives them.  The KF5 branch targets Qt5: the library needs Qt5 Core/Gui/DBus
plus KF5Config, KF5CoreAddons, KF5I18n and KF5ThreadWeaver; the upstream
autotests add Qt5 Widgets/Test.

OHOS-specific adaptations (reusing the validated threadweaver5 / kpeople5 /
kservice5 KF5 skeleton):
  - QT_MAJOR_VERSION=5 selects Qt5 (qt5-qtbase/5.15.2.2, the widgets/DBus
    capable build; 5.15.2 is the -no-widgets stub and is refused).
  - CMAKE_SYSTEM_NAME=Linux: the OHOS Conan toolchain maps os=OHOS to
    CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake defines neither UNIX nor a
    platform module, and the build is flagged as cross-compiling.  ECM only
    registers the upstream ctest cases when the build is not cross-compiling
    (if(NOT CMAKE_CROSSCOMPILING)), and its POSIX compiler/rpath settings are
    guarded by if(UNIX) as well.  Forcing the Linux platform (same libc /
    clang driver on OHOS PC) restores UNIX=1 and a native build so the 6
    autotest targets are registered and run (threadweaver5 precedent).
  - EXCLUDE_DEPRECATED_BEFORE_AND_AT=5.91.0, the load-bearing knob of this
    recipe.  KRunner's KF5-5.116 source has a large deprecated API tier that
    links KF5::Service (KPluginInfo/KService), KF5::Plasma and KF5::KIOCore —
    none of them part of this chain, so the build must exclude it.  The
    upstream ECM mechanism (exclude everything deprecated before-and-at
    5.91.0) lines up exactly with the guards in the tarball:
      * root CMakeLists.txt wraps find_package(KF5KIO/KF5Service/KF5Plasma)
        in `EXCLUDE_DEPRECATED_BEFORE_AND_AT VERSION_LESS 5.91.0`; with
        5.91.0 the three are not required at all (otherwise configure aborts
        on missing packages);
      * src/CMakeLists.txt wraps the KF5::Service/KF5::Plasma/KF5::KIOCore
        link block in the same guard;
      * src/declarative (the deprecated org.kde.runnermodel QML plugin) is
        guarded by VERSION_LESS 5.0.0 and is not built;
      * abstractrunner.h / runnermanager.h include <KPluginInfo>/<KService>
        only under KRUNNER_ENABLE_DEPRECATED_SINCE(5, 91); the export header
        generated with EXCLUDE_DEPRECATED_BEFORE_AND_AT=5.91.0 makes that
        macro FALSE, so the headers take the <KPluginFactory> branch and
        kservice stays out of the graph.  (The nested
        `#if KSERVICE_BUILD_DEPRECATED_SINCE(...)` guards inside the false
        branch are skipped by the preprocessor, so the kservice macro being
        undefined is never evaluated.)
      * the smallest tier value that drops only the out-of-chain block is
        5.91.0: the next boundary (src/CMakeLists.txt `VERSION_LESS 5.94.0`,
        Qt::Gui/KF5::ConfigCore linked PUBLIC) stays satisfiable and is
        deliberately kept enabled.  Reusable pattern + tier-selection rule:
        knowledge draft
        DRAFT-krunner5-5.116.0-exclude-deprecated-tier-absent-frameworks.
    Consequence, declared in notes.md / MANIFEST.yml / PR body: the
    KService-based deprecated API of KRunner (KPluginInfo metadata(),
    KService::Ptr loadRunner, Plasma::Package usage) is NOT part of this
    build; the KPluginMetaData-based API is complete.
  - Qt5 Quick supply: qt5-qtdeclarative ships the Qt5Qml/Qt5Quick libraries
    and headers but no lib/cmake.  CMakeDeps is told to name its generated
    qt5-qtdeclarative config Qt5Qml (cmake_file_name), and a hand-written
    aggregated Qt5Config.cmake shim in the generators folder (first on
    CMAKE_PREFIX_PATH) preloads the native qt5-qtbase per-module configs
    (Core/Network/Gui/Widgets/Test/DBus) with NO_DEFAULT_PATH, then
    find_dependency(Qt5Qml) and forwards Qt5::Quick to Qt5::Qml as an
    INTERFACE target (link-time only; krunner.cpp uses Qt5::Quick at link
    level only).  The shim sets Qt5_FOUND TRUE first, so the Qt5Qml
    config's own find_dependency(Qt5) cannot re-enter the shim
    mid-execution (kpeople5 precedent, knowledge draft
    DRAFT-E5xx-qt5-conan-split-cmake-bridge).  qt5-qtbase itself is consumed through
    its native configs (cmake_find_mode=none) because only they carry the
    mkspec include path.
  - KF5::Runner's exported interface references KF5::I18n (PUBLIC in
    src/CMakeLists.txt), but the installed KF5RunnerConfig.cmake does not
    find_dependency(KF5I18n) (upstream gap; upstream apps find I18n
    themselves).  Consumers must resolve it, so the test_package declares
    ki18n5 and calls find_package(KF5I18n) explicitly.
  - Qt5 DBus tools: the autotests build testremoterunner with
    qt_add_dbus_adaptor() from ../src/data/org.kde.krunner1.xml.  A
    CMAKE_PROJECT_TOP_LEVEL_INCLUDES file includes the package's
    lib/cmake/Qt5DBus/Qt5DBusMacros.cmake and pins
    Qt5Core_MOC/RCC/UIC_EXECUTABLE and
    Qt5DBus_QDBUSXML2CPP/QDBUSCPP2XML_EXECUTABLE to the qt5-qtbase bin/
    tools (kservice5 precedent: without it the macro is unknown at
    configure time and, once known, the empty tool path degenerates the
    custom command to "-m -p ..." with no program).
  - ECM_MODULE_PATH / ECM_DIR are set explicitly: ecm is a tool_requires
    (build context), so CMakeDeps does not wire its share/ECM tree into the
    host prefix paths.
  - CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE point at the qt5-qtbase bin
    tools, and _prepare_qt_mkspec_compat recreates the build-tree mkspecs
    path that the packaged Qt5CoreConfigExtrasMkspecDir.cmake hard-codes
    (threadweaver5 / kcoreaddons5 precedent).
  - CMAKE_BUILD_WITH_INSTALL_RPATH=ON (E537): OHOS refuses to mmap
    PROT_EXEC a library whose ELF was rewritten after linking; linking with
    the final install RPATH leaves the install step nothing to rewrite.
    Every packaged ELF is then re-signed with llvm-objcopy --remove-section
    .codesign + binary-sign-tool -selfSign 1 (kirigami/ki18n/threadweaver
    precedent).
  - CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE + SONAME flags: relocatable,
    unversioned DT_SONAME (W3 CI L5 soname gate).
  - CMAKE_BUILD_PARALLEL_LEVEL=1: the HMDFS cache refuses the make jobserver
    fifo (EPERM).
  - /system/lib64 is prepended to LD_LIBRARY_PATH while the host tools and
    the tests run so the compatible libc++ wins over the sandbox one.
  - Tests: BUILD_TESTING=ON registers 6 autotest targets (runnercontexttest
    is compiled out by the VERSION_LESS 5.76.0 guard, which also matches
    its KF5::KIOCore dependency).  build() executes ctest: the 3 bus-free
    suites (runnermatchmethodstests, runnermanagerhistorytest,
    testmetadataconversion) run headless with QT_QPA_PLATFORM=offscreen;
    the 3 suites that spawn testremoterunner and wait for its
    org.kde.krunner1 service on the session bus (dbusrunnertest,
    runnermanagersinglerunnermodetest, runnermanagertest) execute under a
    private dbus-run-session bus when the image provides both
    dbus-run-session and dbus-daemon, and are otherwise excluded from the
    ctest run with -E (recorded in notes.md / test_package/MANIFEST.yml).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KRunner5Conan(ConanFile):
    name = "krunner5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - KRunner (parallelized query framework: runner plugins, query matches, runner management)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/krunner"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # .2 is the widgets/DBus-capable Qt5 build; force=True normalises the
        # graph because kcoreaddons5/5.116.0.1 still pins qt5-qtbase/5.15.2.
        self.requires("qt5-qtbase/5.15.2.2", force=True)
        # Qt5Quick is a top-level REQUIRED component of the project.
        self.requires("qt5-qtdeclarative/5.15.2")
        self.requires("kconfig5/5.116.0")
        self.requires("kcoreaddons5/5.116.0.1")
        self.requires("ki18n5/5.116.0")
        self.requires("threadweaver5/5.116.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase is consumed through its native Qt5 configs; the
        # CMakeDeps-generated ones would shadow them and do not carry the
        # mkspec include path.
        deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
        # qt5-qtdeclarative ships libs only; CMakeDeps generates the Qt5Qml
        # per-module config for it.
        deps.set_property("qt5-qtdeclarative", "cmake_file_name", "Qt5Qml")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # The deprecated API tier (< 5.91.0) needs kio5/kservice5/
        # plasma-framework, which are not part of this chain; the upstream
        # ECM switch removes it (see module docstring for the exact guards).
        tc.variables["EXCLUDE_DEPRECATED_BEFORE_AND_AT"] = "5.91.0"
        # Treat OHOS as a Linux-like target so CMake defines UNIX and does
        # not report a cross build: ECM then registers the upstream ctest
        # cases and applies the POSIX flags/rpath settings.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # HMDFS cannot create the make jobserver fifo (EPERM).
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # E537: link with the final install RPATH so the install step does
        # not rewrite the ELF in place.
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        # Relocatable, unversioned DT_SONAME (W3 CI L5 soname gate).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]

        # Qt5CoreConfigExtrasMkspecDir.cmake hard-codes a build-tree path
        # (<prefix>/../b/mkspecs/linux-clang) the packaged cache entry never
        # has; recreate it from the package's own mkspecs/
        # (threadweaver5 / kcoreaddons5 precedent).
        self._prepare_qt_mkspec_compat(qtbase.package_folder)

        qbin = os.path.join(qtbase.package_folder, "bin")
        for tool, cmake_var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
            ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
        ):
            tool_path = os.path.join(qbin, tool)
            if not os.path.isfile(tool_path):
                raise ConanInvalidConfiguration(
                    "qt5-qtbase/5.15.2.2 does not provide the required "
                    "bin/{} tool".format(tool)
                )
            tc.variables[cmake_var] = tool_path

        # The Qt5 DBus macros and tools (qt_add_dbus_adaptor for
        # testremoterunner) come from the package through a top-level
        # include, which runs before the project's own find_package calls
        # (kservice5 precedent, see module docstring).
        qt5_dbus_macros = os.path.join(
            qtbase.package_folder, "lib", "cmake", "Qt5DBus", "Qt5DBusMacros.cmake"
        )
        top_include = os.path.join(
            self.generators_folder, "ohos-qt5-dbus-macros.cmake"
        )
        top_lines = []
        if os.path.isfile(qt5_dbus_macros):
            top_lines.append('include("%s")' % qt5_dbus_macros)
        for var, tool in (
            ("Qt5Core_MOC_EXECUTABLE", "moc"),
            ("Qt5Core_RCC_EXECUTABLE", "rcc"),
            ("Qt5Core_UIC_EXECUTABLE", "uic"),
            ("Qt5DBus_QDBUSXML2CPP_EXECUTABLE", "qdbusxml2cpp"),
            ("Qt5DBus_QDBUSCPP2XML_EXECUTABLE", "qdbuscpp2xml"),
        ):
            exe = os.path.join(qbin, tool)
            if not os.path.isfile(exe):
                # moc and qdbusxml2cpp are the two this project actually
                # needs (qt_add_dbus_adaptor); the rest are opportunistic.
                if tool in ("moc", "qdbusxml2cpp"):
                    raise ConanException(
                        "qt5-qtbase does not provide the required bin/%s" % tool
                    )
                continue
            top_lines.append('set(%s "%s")' % (var, exe))
        with open(top_include, "w", encoding="utf-8") as handle:
            handle.write("\n".join(top_lines) + "\n")
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = top_include

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        tc.generate()

        # ------------------------------------------------------------------
        # Aggregated Qt5Config.cmake shim (exact-name match beats any
        # lowercase qt5-config.cmake; the generators folder is first on
        # CMAKE_PREFIX_PATH).  Supplied by three packages:
        #   qt5-qtbase        -> native per-module configs (Core..DBus)
        #   qt5-qtdeclarative -> CMakeDeps-generated Qt5Qml config
        #   this shim         -> the aggregate + Qt5::Quick forwarding
        # ------------------------------------------------------------------
        qt_prefix = qtbase.package_folder
        shim = [
            "# Aggregated Qt5Config for krunner5 (two-package Qt5 supply).",
            "# Generated by conanfile.py generate().",
            "include(CMakeFindDependencyMacro)",
            # Guard against mutual re-entry: the CMakeDeps-generated
            # Qt5QmlConfig (qt5-qtdeclarative) find_dependency's Qt5;
            # marking the aggregate found FIRST stops that callback from
            # re-including this shim mid-execution.
            "set(Qt5_FOUND TRUE)",
            'find_dependency(Qt5Core 5.15.2 PATHS "%s/lib/cmake/Qt5Core" NO_DEFAULT_PATH)'
            % qt_prefix,
        ]
        # Network/Gui are referenced by the CMakeDeps-generated Qt5Qml
        # target interfaces (qt5-qtdeclarative cpp_info.requires), so they
        # must be preloaded before Qt5QmlConfig is included.  Widgets/Test/
        # DBus are used by the library and the autotests.
        for comp in ("Network", "Gui", "Widgets", "Test", "DBus"):
            shim.append(
                'find_dependency(Qt5%s 5.15.2 PATHS "%s/lib/cmake/Qt5%s" NO_DEFAULT_PATH)'
                % (comp, qt_prefix, comp)
            )
        shim += [
            "find_dependency(Qt5Qml)",
            # Qt5::Quick forwarding target: the project needs the Qt5::Quick
            # component at configure/link level; the declarative package
            # exposes libQt5Quick through the Qt5Qml component, so an
            # INTERFACE forwarding target is enough for link time.
            "if(NOT TARGET Qt5::Quick)",
            "  add_library(Qt5::Quick INTERFACE IMPORTED)",
            "  set_target_properties(Qt5::Quick PROPERTIES",
            "    INTERFACE_LINK_LIBRARIES Qt5::Qml",
            "  )",
            "endif()",
            "set(Qt5_Core_FOUND TRUE)",
            "set(Qt5_Network_FOUND TRUE)",
            "set(Qt5_Gui_FOUND TRUE)",
            "set(Qt5_Widgets_FOUND TRUE)",
            "set(Qt5_Test_FOUND TRUE)",
            "set(Qt5_DBus_FOUND TRUE)",
            "set(Qt5_Qml_FOUND TRUE)",
            "set(Qt5_Quick_FOUND TRUE)",
            'set(Qt5_VERSION_STRING "5.15.2.2")',
        ]
        with open(
            os.path.join(self.generators_folder, "Qt5Config.cmake"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write("\n".join(shim) + "\n")
        with open(
            os.path.join(self.generators_folder, "Qt5ConfigVersion.cmake"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                "set(PACKAGE_VERSION 5.15.2.2)\n"
                "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)\n"
                "  set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
                "else()\n"
                "  set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
                "  if(PACKAGE_FIND_VERSION STREQUAL PACKAGE_VERSION)\n"
                "    set(PACKAGE_VERSION_EXACT TRUE)\n"
                "  endif()\n"
                "endif()\n"
            )

        # Wire the search paths CMakeDeps cannot provide.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for pkg in (qtdecl, qtbase):
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % pkg.package_folder)
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % pkg.package_folder)
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % pkg.package_folder)
        # The KF5 dependency packages are consumed through their native
        # KF5*Config.cmake files (their recipes publish
        # cmake_find_mode=none), so their prefixes must be wired here.
        for dep_name in ("kconfig5", "kcoreaddons5", "ki18n5", "threadweaver5"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s")' % dep.package_folder
                )
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                    % dep.package_folder
                )
                for sub in ("KF5Config", "KF5CoreAddons", "KF5I18n", "KF5ThreadWeaver"):
                    cfg = os.path.join(dep.package_folder, "lib", "cmake", sub)
                    if os.path.isdir(cfg):
                        lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % cfg)
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # The whole mkspecs tree is needed: <qplatformdefs.h> is included
        # from the mkspec include dir, and Qt5CoreConfigExtras.cmake resolves
        # it as <package_folder>/../b/mkspecs (the build tree of the
        # original build), which the packaged cache entry never has.
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if not os.path.isdir(source):
            return
        os.makedirs(expected, exist_ok=True)
        for name in os.listdir(source):
            src_entry = os.path.join(source, name)
            dst_entry = os.path.join(expected, name)
            if os.path.exists(dst_entry):
                continue
            if os.path.isdir(src_entry):
                shutil.copytree(src_entry, dst_entry)
            else:
                shutil.copy2(src_entry, dst_entry)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _runtime_env(self):
        runtime_env = Environment()
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            runtime_env.prepend_path(
                "PATH", os.path.join(qt5.package_folder, "bin")
            )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        if str(self.settings.os) == "OHOS":
            # The sandbox LD_LIBRARY_PATH carries an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64;
            # prepend /system/lib64 so the Qt host tools and the test
            # executables resolve the compatible libc++ first.
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _run_upstream_tests(self):
        # 6 upstream QTEST targets are registered by ECM (see module
        # docstring; runnercontexttest falls to the 5.76 deprecation guard,
        # which also matches its KF5::KIOCore dependency).  Three of them
        # spawn testremoterunner and wait for its org.kde.krunner1 service
        # registration on the session bus (abstractrunnertest.h
        # startDBusRunnerProcess / QDBusServiceWatcher): they run under a
        # private dbus-run-session bus when the image provides
        # dbus-run-session AND dbus-daemon, otherwise they are excluded from
        # the ctest run with -E (recorded in notes.md / MANIFEST.yml).
        if not can_run(self):
            return
        test_env = self._runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        try:
            os.chmod(xdg_runtime, 0o700)
        except OSError:
            pass
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        self._prepare_ctest_runtime_links()
        ctest_cmd = 'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
            self.build_folder
        )
        session_bus_tests = (
            "dbusrunnertest|runnermanagersinglerunnermodetest|runnermanagertest"
        )
        dbus_runner = shutil.which("dbus-run-session")
        dbus_daemon = shutil.which("dbus-daemon")
        if dbus_runner and dbus_daemon:
            ctest_cmd = "{} -- {}".format(self._quote(dbus_runner), ctest_cmd)
        else:
            self.output.warning(
                "dbus-run-session/dbus-daemon not available on this image: "
                "running the bus-free suites and excluding {} from ctest "
                "with -E".format(session_bus_tests)
            )
            ctest_cmd += ' -E "{}"'.format(session_bus_tests)
        with test_env.vars(self).apply():
            self.run(ctest_cmd)

    def _prepare_ctest_runtime_links(self):
        # ECMAddTests/KDECMakeSettings place the test executables under
        # <build>/bin; their libKF5Runner and Qt5 runtime deps live in the
        # build tree / conan package folders.  Symlink them next to the
        # test binaries so the loader can resolve (threadweaver5 precedent).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        """CMake rewrites the RUNPATH of installed shared libraries, which
        invalidates the OHOS build-time .codesign section. The OHOS loader
        then refuses to load the library ("Permission denied"). Re-sign every
        packaged ELF (kitemmodels 6.18.0.1 / kirigami 6.26.0 / ki18n 6.26.0.1
        precedent)."""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        # install() runs cmake again (env-clean CI shell: no /system/lib64 on
        # LD_LIBRARY_PATH -> the cmake binary itself fails to relocate,
        # exit 127); wrap it with the runtime env like build().
        with self._runtime_env().vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # The project installs its own KF5RunnerConfig.cmake with proper
        # dependency tracking; use cmake_find_mode=none so CMakeDeps does
        # not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Runner"]
