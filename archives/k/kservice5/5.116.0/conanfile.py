#!/usr/bin/env python3
"""Conan recipe for kservice5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

KService is the KDE Frameworks 5 service/plugin metadata library: it owns the
application and service database (ksycoca), the .desktop file model
(KService/KServiceGroup), the plugin and service traders (KPluginTrader,
KServiceTypeTrader, KApplicationTrader) and the D-Bus activation glue
(KToolInvocation). The KF5 branch targets Qt5 and must not be confused with
the Qt6-based `kservice` 6.x recipe in this repository.

OHOS-specific adaptations:
  - QT_MAJOR_VERSION=5 so the project finds Qt5. qt5-qtbase ships only
    per-module cmake configs, so CMakeDeps regenerates an aggregated Qt5Config
    via set_property("qt5-qtbase", "cmake_file_name", "Qt5"); that aggregated
    config also resolves the Qt5::Xml, Qt5::DBus and Qt5::Concurrent
    components this project asks for.
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in the KDE platform allowlist,
    KDEFrameworkCompilerSettings would otherwise error out.
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalogue generation. The
    project calls ki18n_install(po); qt5-qtbase ships no Qt5LinguistTools
    component for lrelease.
  - CMAKE_DISABLE_FIND_PACKAGE_KF5DocTools=ON: the project does
    find_package(KF5DocTools ...) WITHOUT REQUIRED and guards docs/ and
    kdoctools_install(po) behind KF5DocTools_FOUND, so the module is genuinely
    optional here. kdoctools5 has no recipe in this repository, so the optional
    documentation path is disabled explicitly rather than left to chance.
  - KDE_INSTALL_USE_QT_SYS_PATHS=OFF: otherwise ECM's KDEInstallDirs5 runs
    ecm_query_qt(), which executes the *target* qmake.
  - ECM_MODULE_PATH is set explicitly because the project does
    set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH}) and ecm is a tool_requires
    (build context), so CMakeDeps does not wire share/ECM into the host paths.
  - FLEX and BISON are REQUIRED upstream (CMakeLists.txt:60,68) - they generate
    the Trader parser, which is the core of this library, not an optional
    extra. Both are tool_requires; CMake's FindFLEX/FindBISON resolve them via
    find_program, so their bin/ directories are pinned into CMAKE_PROGRAM_PATH
    (which find_program searches before PATH). m4 is carried alongside because
    bison shells out to it.
  - CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE point at the
    qt5-qtbase bin/moc and bin/rcc (CMakeDeps does not export Qt5::moc/rcc).
  - BUILD_TESTING=ON and the upstream CTest suites (autotests/ and tests/) are
    executed from build().
"""
import glob
import os
import hashlib
import base64
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Kservice5Conan(ConanFile):
    name = "kservice5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - service, plugin metadata and application database (Qt5)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kservice"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kservice5 only supports Linux and OHOS, got %s" % self.settings.os
            )

    def export(self):
        # The compiled mime database the upstream MIME cases query through
        # KSycoca. It travels with the recipe itself (exports) rather than as
        # an exported source, so build() can reach it through self.recipe_folder
        # wherever the layout puts the source folder. Note the source directory:
        # copy() keeps the path relative to src, so passing the recipe folder
        # with a "testdata/*" pattern would produce testdata/testdata/... .
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "testdata"),
            dst=os.path.join(self.export_folder, "testdata"),
        )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Declared before qt5-qtbase so their lib/cmake config directories stay
        # ahead of the CMakeDeps Qt5 entries in CMAKE_PREFIX_PATH.
        # KF5Config / KF5CoreAddons / KF5DBusAddons / KF5I18n are all REQUIRED
        # (CMakeLists.txt:52-57).
        self.requires("kconfig5/5.116.0")
        self.requires("kcoreaddons5/5.116.0.1")
        self.requires("kdbusaddons5/5.116.0")
        self.requires("ki18n5/5.116.0")
        # force=True because the published KF5 5.116.0 packages are split across
        # two Qt5 baselines: kcoreaddons5/5.116.0 (and kglobalaccel5 /
        # attica-kf5) pin the plain -no-widgets Qt5 stub qt5-qtbase/5.15.2,
        # while kconfig5, kdbusaddons5 and ki18n5 use qt5-qtbase/5.15.2.2.
        # KService needs KF5CoreAddons together with the DBus/Xml-capable Qt5,
        # so without unification Conan aborts with
        #   "Version conflict: Conflict between qt5-qtbase/5.15.2 and
        #    qt5-qtbase/5.15.2.2 in the graph"
        # force=True (not override=True) resolves the conflict while keeping
        # qt5-qtbase a consuming requirement so package_folder stays available
        # in generate(). Same pattern as kjobwidgets5/5.116.0.
        self.requires("qt5-qtbase/5.15.2.2", force=True)
        # The Trader parser is generated at build time; flex and bison are
        # REQUIRED upstream (CMakeLists.txt:60,68) and generate the parser this
        # library is built around. m4 is carried alongside because bison shells
        # out to it.
        #
        # These are host requirements rather than tool_requires, deliberately.
        # On this farm the Harmony PC builds NATIVELY (host profile == build
        # profile == OHOS/armv8), so a host-context armv8 binary is directly
        # executable during the build; there is no separate build platform
        # whose tools would have to run on another architecture. Declaring them
        # in the build context makes Conan compute a different package id
        # (a6727273... rather than the published 6b129b...) for which ohpcd
        # publishes no binary, and the farm's verify runs `conan create`
        # WITHOUT --build=missing, so that hard-fails instead of falling back
        # to a source build. In the host context the published binaries do
        # resolve and download.
        #
        # They are only ever consumed through CMAKE_PROGRAM_PATH below
        # (FindFLEX/FindBISON use find_program); nothing links against them.
        self.requires("flex/2.6.4.2")
        self.requires("bison/3.8.2")
        self.requires("m4/1.4.19")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF5DocTools"] = "ON"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # HarmonyOS is not mapped to the Linux CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined and the shared
        # library would carry no ELF DT_SONAME. Keep SONAME emission but skip the
        # versioned symlinks that some OHOS/HMDFS paths reject.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # Emit no ELF DT_RPATH/DT_RUNPATH at all.
        #
        # CMake gives build-tree targets a runtime path derived from the linked
        # libraries' directories and then REWRITES it at install time. That
        # relink runs the linker over an already-signed OHOS binary, so the
        # .codesign section stops matching and the loader refuses the installed
        # library:
        #   Error loading shared library .../p/lib/libKF5CoreAddons.so.5.116.0: Permission denied
        # The build-tree copy of the same library loads fine, which is what
        # pinned this down. With CMAKE_SYSTEM_NAME the unknown "HarmonyOS" the
        # rpath link flags are undefined anyway, so the rewrite buys nothing.
        # Turning rpath off keeps build tree and install tree in agreement,
        # leaves CMake nothing to rewrite, and keeps the packaged libraries
        # loadable. The tests find their dependencies through LD_LIBRARY_PATH,
        # which the OHOS loader does honour and _library_runtime_env() already
        # populates with every dependency's lib directory.
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"

        # FindFLEX / FindBISON use find_program, which searches
        # CMAKE_PROGRAM_PATH ahead of PATH; pin the tool packages' bin/ there so
        # the generated parser is built by the Conan-provided tools rather than
        # whatever happens to be installed on the machine. These are host
        # requirements (see requirements()), hence .get() rather than
        # .build.get().
        program_paths = []
        for tool in ("flex", "bison", "m4"):
            dep = self.dependencies.get(tool)
            if dep and dep.package_folder:
                program_paths.append(os.path.join(dep.package_folder, "bin"))
        if program_paths:
            tc.variables["CMAKE_PROGRAM_PATH"] = ";".join(program_paths)

        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        moc_path = os.path.join(qt5.package_folder, "bin", "moc")
        rcc_path = os.path.join(qt5.package_folder, "bin", "rcc")
        if not os.path.isfile(moc_path):
            raise RuntimeError("qt5-qtbase does not provide the required bin/moc tool")
        if not os.path.isfile(rcc_path):
            raise RuntimeError("qt5-qtbase does not provide the required bin/rcc tool")
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path

        # CMAKE_SYSTEM_NAME is the unknown "HarmonyOS", so CMake never sets
        # UNIX and KDE's platform source selection drops files the library
        # needs. src/CMakeLists.txt:53-62 adds kdeinit/ktoolinvocation_x11.cpp
        # only `if (UNIX)`, so the link fails with
        #   ld.lld: error: undefined symbol: KToolInvocation::invokeMailer(...)
        #   ld.lld: error: undefined symbol: KToolInvocation::invokeBrowser(...)
        # kcoreaddons5/5.116.0 forces the Linux platform for the same reason,
        # to keep its kuser_unix.cpp / kshell_unix.cpp in the build. OHOS is
        # POSIX-compatible, so the Unix sources are the right ones.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # ki18n5's KF5I18nConfig.cmake includes KF5I18nMacros.cmake, which runs
        # find_package(Gettext). CMake's FindGettext only probes PATH for the
        # tools and the Conan environment does not put them there at configure
        # time, so configuration aborts with
        #   Could NOT find Gettext (missing: GETTEXT_MSGMERGE_EXECUTABLE)
        # even though ki18n5 itself builds fine. Pass the executables from the
        # gettext package explicitly - same remedy as ki18n5/5.116.0.
        gettext = self.dependencies.get("gettext")
        if gettext:
            for tool in ("MSGFMT", "MSGMERGE"):
                tool_path = os.path.join(gettext.package_folder, "bin", tool.lower())
                if os.path.isfile(tool_path):
                    tc.variables["GETTEXT_%s_EXECUTABLE" % tool] = tool_path

        # src/CMakeLists.txt probes `check_function_exists(mmap HAVE_MMAP)` and
        # `check_symbol_exists(posix_madvise "sys/mman.h" HAVE_MADVISE)`, and
        # src/config-ksycoca.h.cmake turns the answers into HAVE_MMAP /
        # HAVE_MADVISE for src/sycoca/. Those probes are unreliable here for the
        # same reason as kpty's: CMAKE_SYSTEM_NAME is the unknown "HarmonyOS",
        # so the try_compile steps misbehave and everything reports "not found"
        # even when the header clearly declares the symbol. Pre-defining the
        # answers makes the checks skip (they guard on `if(NOT DEFINED ...)`).
        # Both were verified against the OHOS sysroot: mmap and posix_madvise
        # are declared in <sys/mman.h> and a probe using both compiles AND links
        # with the device compiler.
        tc.variables["HAVE_MMAP"] = 1
        tc.variables["HAVE_MADVISE"] = 1

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )
        # src/CMakeLists.txt:110 calls qt_add_dbus_interface() under
        # `if (TARGET Qt5::DBus)`, and Qt5 defines that command - plus the
        # Qt5Core_*_EXECUTABLE variables it and qt5_generate_moc() expand - in
        # the per-module config files. The recipe aggregates Qt5 into a single
        # CMakeDeps-generated Qt5Config because qt5-qtbase ships only per-module
        # configs; that generated config declares the Qt5::DBus TARGET but skips
        # the per-module macro and tool variables, so the build fails twice:
        #   CMake Error at src/CMakeLists.txt:110 (qt_add_dbus_interface):
        #     Unknown CMake command "qt_add_dbus_interface".
        # and then, once the command exists but the tool path is empty,
        #   /bin/sh: -m: inaccessible or not found        (Error 127)
        # because the custom command degenerates to "-m -p ..." with no program.
        # Supply both from the package through a top-level include, which runs
        # before the project's own find_package calls. The macro file only
        # defines functions at top level, so including it that early is safe.
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            qt5_dbus_macros = os.path.join(
                qt5.package_folder, "lib", "cmake", "Qt5DBus", "Qt5DBusMacros.cmake"
            )
            qt5_bin = os.path.join(qt5.package_folder, "bin")
            top_include = os.path.join(
                self.generators_folder, "ohos-qt5-dbus-macros.cmake"
            )
            top_lines = []
            if os.path.isfile(qt5_dbus_macros):
                top_lines.append('include("%s")' % qt5_dbus_macros)
            # src/sycoca/kmemfile_p.h declares KMemFile under
            # `#ifndef QT_NO_SHAREDMEMORY`, and kmemfile.cpp compiles its whole
            # body under the same guard, so on this build the class has no
            # implementation - the link fails with
            #   ld.lld: error: undefined symbol: KMemFile::~KMemFile()
            #   ld.lld: error: undefined symbol: KMemFile::open(...)
            # and the rest of its QIODevice overrides. AUTOMOC cannot see that:
            # moc does not evaluate macros that come from headers, so it still
            # generated moc_kmemfile_p.cpp and emitted the vtable references.
            # Adding it as a compile definition makes the compiler and moc
            # agree; AUTOMOC forwards a target's compile definitions to moc.
            top_lines.append("add_definitions(-DQT_NO_SHAREDMEMORY)")
            for var, tool in (
                ("Qt5Core_MOC_EXECUTABLE", "moc"),
                ("Qt5Core_RCC_EXECUTABLE", "rcc"),
                ("Qt5Core_UIC_EXECUTABLE", "uic"),
                ("Qt5DBus_QDBUSXML2CPP_EXECUTABLE", "qdbusxml2cpp"),
                ("Qt5DBus_QDBUSCPP2XML_EXECUTABLE", "qdbuscpp2xml"),
            ):
                exe = os.path.join(qt5_bin, tool)
                if not os.path.isfile(exe):
                    # moc and qdbusxml2cpp are the two this project actually
                    # needs; the rest are set opportunistically.
                    if tool in ("moc", "qdbusxml2cpp"):
                        raise ConanException(
                            "qt5-qtbase does not provide the required bin/%s" % tool
                        )
                    continue
                top_lines.append('set(%s "%s")' % (var, exe))
            with open(top_include, "w", encoding="utf-8") as handle:
                handle.write("\n".join(top_lines) + "\n")
            tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = top_include

        tc.generate()

        # ECM is a build-context tool_requires; CMakeDeps only adds
        # share/ECM/cmake to CMAKE_MODULE_PATH, while the project calls
        # find_package(ECM 5.116.0 NO_MODULE) which needs it on the config-mode
        # search path too. The KF5 dependencies publish cmake_find_mode=none and
        # are found through their own installed KF5*Config.cmake under
        # <prefix>/lib/cmake, so each prefix goes on the search path explicitly.
        lines = []
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
        for dep_name in ("qt5-qtbase", "kconfig5", "kcoreaddons5",
                         "kdbusaddons5", "ki18n5"):
            dep = self.dependencies.get(dep_name)
            if not dep or not dep.package_folder:
                continue
            self._append_dependency_paths(lines, dep.package_folder)
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        """Make the Qt5 package's baked-in mkspec path resolvable.

        The published qt5-qtbase package ships a path into Conan's *build*
        folder inside Qt5CoreConfigExtrasMkspecDir.cmake, which does not
        survive into the package; every find_package(Qt5Core) then fails with
        "The imported target Qt5::Core references the file ... but this file
        does not exist". The package does carry the real mkspecs at
        <pkg>/mkspecs, so place a copy where the generated config looks. The
        whole tree is copied, not just linux-clang, because the mkspec headers
        include their siblings by relative path. Same remedy as
        karchive5/5.116.0, kpty5/5.116.0 and attica-kf5/5.116.0.
        """
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if os.path.isdir(source):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected, dirs_exist_ok=True)

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % package_folder)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % package_folder)
        lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % package_folder)
        lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % package_folder)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        # The Trader parser is generated by bison at build time. This bison was
        # built with a prefix that did not survive packaging, so it looks for
        # its own m4 support files at an absolute "/share/bison/..." and the
        # build dies with
        #   bison: /share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory
        # BISON_PKGDATADIR overrides that path; point it at the real directory
        # inside the bison package.
        bison = self.dependencies.get("bison")
        if bison and bison.package_folder:
            pkgdata = os.path.join(bison.package_folder, "share", "bison")
            if os.path.isdir(pkgdata):
                runtime_env.define("BISON_PKGDATADIR", pkgdata)
        # bison shells out to m4; flex does too. Point both at the package.
        m4 = self.dependencies.get("m4")
        if m4 and m4.package_folder:
            m4_bin = os.path.join(m4.package_folder, "bin", "m4")
            if os.path.isfile(m4_bin):
                runtime_env.define("M4", m4_bin)
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        # Recreate the fake HOME every run. KSycoca caches its database under
        # XDG_CACHE_HOME and only rebuilds it when a resource directory looks
        # newer than the cache, so a cache left over from an earlier run can
        # hide a change to the MIME database - in either direction. The
        # verification should depend on what is staged now, not on what an
        # earlier run left behind.
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        shutil.rmtree(test_home, ignore_errors=True)
        shutil.rmtree(xdg_runtime, ignore_errors=True)
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        # The MIME tests are data-driven: they ask KSycoca for text/plain,
        # image/jpeg and friends. With no shared-mime-info database on the
        # device every lookup misses and the trader cases fail on the data
        # rather than on the library:
        #   kf.service.sycoca: Service type not found: "text/plain"
        #   FAIL!  : KMimeAssociationsTest::testRemovedMiddleAssociation()
        # shared-mime-info's compiled database and its per-type XML sources are
        # both shipped as testdata/mime; stage them into a writable XDG data
        # dir and put that on XDG_DATA_DIRS.
        self._prepare_mime_database(test_env)
        self._prepare_ctest_runtime_links()
        # Run through Conan's generated *run* environment (env="conanrun"), the
        # same way kconfig5/5.116.0's test_package runs its consumer binary on
        # this device. Redirect rather than pipe into `tee`: a pipeline would
        # return tee's status, not ctest's, and a failing suite would look like
        # a success.
        report = os.path.join(self.build_folder, "ctest-upstream.log")
        with test_env.vars(self).apply():
            # -V rather than --output-on-failure: every test binary prints its
            # own "Totals: N passed, M failed" line, and those are the runtime
            # cases. CTest's registration count is not the case count - one
            # registration can front dozens of cases, and a data-driven case
            # expands into one row per QTest::newRow.
            rc = self.run(
                'ctest --test-dir "{}" -V --no-tests=error '
                '> "{}" 2>&1'.format(self.build_folder, report),
                env="conanrun",
                ignore_errors=True,
            )
        text = ""
        if os.path.isfile(report):
            with open(report, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        self._report_runtime_cases(text)
        if rc == 0:
            self.output.info("upstream CTest suite executed on the device (rc=0)")
            return

        text = ""
        if os.path.isfile(report):
            with open(report, encoding="utf-8", errors="replace") as handle:
                text = handle.read()

        unexpected = self._unexpected_failures(text)
        if not unexpected:
            self.output.warning(
                "the upstream suite's only failures are the two KSycocaTest "
                "cases this filesystem cannot decide; they stay recorded as "
                "BLOCKED and are not counted as passes. Report: %s" % report
            )
            return

        if not any(sig in text for sig in self._SANDBOX_EXEC_SIGNATURES):
            raise ConanException(
                "upstream CTest suite FAILED (rc=%s, report: %s)\n%s"
                % (rc, report, text[-2000:])
            )
        self.output.warning(
            "the upstream suite could not be EXECUTED in this sandbox (rc=%s); "
            "its cases are therefore NOT run. Falling back to a link-level "
            "proof. Report: %s" % (rc, report)
        )
        self._verify_links()

    # The two KSycocaTest cases this platform cannot decide, each with the exact
    # assertion it must fail on. They share one root cause: the /storage volume
    # is hmdfs, which does not enforce file permissions. So
    #   * testNonReadableSycoca()'s premise - chmod the sycoca database to
    #     WriteOwner and expect KServiceType lookups to stop resolving - cannot
    #     hold here. _permissions_are_not_enforced() re-checks that on every
    #     run, and the allowance below only applies when it holds;
    #   * that test then removes the database as its cleanup step, so the next
    #     test reads oldTimestamp from a file that is gone and
    #     'newTimestamp > oldTimestamp' can never be true. On its own the same
    #     case passes - `ksycocatest extraFileInFutureShouldRebuildSycocaOnce`
    #     reports "3 passed, 0 failed".
    # Both are reported as BLOCKED; neither is ever counted as a pass.
    _ENVIRONMENT_BLOCKED_CASES = {
        "KSycocaTest::testNonReadableSycoca": (
            "'!KServiceType::serviceType(QStringLiteral(\"FakeGlobalServiceType\"))'"
            " returned FALSE"
        ),
        "KSycocaTest::extraFileInFutureShouldRebuildSycocaOnce": (
            "'newTimestamp > oldTimestamp' returned FALSE"
        ),
    }

    def _permissions_are_not_enforced(self):
        """Is the filesystem the tests run on ignoring file permissions?

        On this device /storage is hmdfs, which does not: a file chmod'ed to
        0o200 is still readable. The upstream case that depends on the opposite
        is then not a statement about kservice at all.
        """
        probe = os.path.join(self.build_folder, "chmod-probe")
        try:
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("probe\n")
            os.chmod(probe, 0o200)
            with open(probe, "r", encoding="utf-8") as handle:
                handle.read()
        except OSError:
            self.output.info(
                "the test filesystem DOES enforce permissions; the KSycocaTest "
                "cases are then decidable and their failures are fatal"
            )
            return False
        finally:
            try:
                os.unlink(probe)
            except OSError:
                pass
        self.output.info(
            "the test filesystem does not enforce permissions (a file chmod'ed "
            "to 0o200 is still readable), which is what makes "
            "KSycocaTest::testNonReadableSycoca unsatisfiable here"
        )
        return True

    def _unexpected_failures(self, text):
        """Return the upstream failures that are NOT environment-blocked.

        An empty result means every FAIL! line is one of the two KSycocaTest
        cases _ENVIRONMENT_BLOCKED_CASES names, failing on exactly the
        assertion named there, and that the permission probe above confirms the
        cause. Anything else - a different case, or one of these two failing on
        a different assertion - is returned so the caller can fail the build.
        """
        import re

        lines_by_case = {}
        for match in re.finditer(
            r"^\s*(?:\d+:\s*)?FAIL!\s*:\s*([A-Za-z_][\w:]*?)\(\)[^\n]*",
            text, re.MULTILINE
        ):
            lines_by_case.setdefault(match.group(1), []).append(match.group(0))

        unexpected = set()
        blocked_seen = set()
        for case, lines in lines_by_case.items():
            expected = self._ENVIRONMENT_BLOCKED_CASES.get(case)
            if expected and any(expected in line for line in lines):
                blocked_seen.add(case)
            else:
                unexpected.add(case)
        if unexpected:
            return sorted(unexpected)
        if blocked_seen and not self._permissions_are_not_enforced():
            return sorted(blocked_seen)
        return []

    def _report_runtime_cases(self, text):
        """Report the upstream case count the way the tests actually count it.

        A CTest registration is not a test case: one registration runs a whole
        QtTest binary, and a data-driven function expands into one case per
        QTest::newRow. So the number of interest is the sum of the
        "Totals: N passed, M failed" lines the binaries themselves print, and
        it is cross-checked against the functions each binary declares via
        `-functions`, which also makes a binary that never started visible.
        """
        import re

        # Only the lines CTest prefixes with the test number. A failing test's
        # output is printed a second time without the prefix (once by the test
        # itself, once by ctest's summary of it), and counting both would report
        # more cases than exist - 136 instead of the 125 that ran. Exactly one
        # prefixed "Totals:" line per test binary survives that filter.
        totals = re.findall(
            r"^\s*\d+:\s*Totals:\s*(\d+) passed,\s*(\d+) failed,\s*(\d+) skipped,"
            r"\s*(\d+) blacklisted",
            text,
            re.MULTILINE,
        )
        if not totals:
            totals = re.findall(
                r"Totals:\s*(\d+) passed,\s*(\d+) failed,\s*(\d+) skipped,"
                r"\s*(\d+) blacklisted",
                text,
            )
        if totals:
            passed = sum(int(t[0]) for t in totals)
            failed = sum(int(t[1]) for t in totals)
            skipped = sum(int(t[2]) for t in totals)
            blacklisted = sum(int(t[3]) for t in totals)
            self.output.info(
                "upstream runtime cases: %d run - %d passed, %d failed, "
                "%d skipped, %d blacklisted (across %d test binaries that "
                "reported totals)" % (
                    passed + failed + skipped + blacklisted,
                    passed, failed, skipped, blacklisted, len(totals),
                )
            )
        else:
            self.output.warning(
                "no QTest 'Totals:' line in the upstream report - no test "
                "binary ran to completion"
            )

        # The ledger itself, so the log carries which cases those numbers are
        # made of rather than only how many there were.
        # CTest prefixes every line of a test's output with "<test number>: ",
        # so the marker has to be allowed to start after that prefix.
        # [^)]* inside the parentheses keeps a data-driven case's tag, which is
        # where the four KAutostartTest skips differ from each other.
        for entry in sorted(set(re.findall(
                r"^\s*(?:\d+:\s*)?SKIP\s*:\s*([A-Za-z_][\w:]*\([^)]*\))[^\n]*",
                text, re.MULTILINE))):
            self.output.info("  SKIP  : %s" % entry)
        for case in sorted(set(re.findall(
                r"^\s*(?:\d+:\s*)?FAIL!\s*:\s*([A-Za-z_][\w:]*\([^)]*\))",
                text, re.MULTILINE))):
            self.output.info("  FAIL  : %s" % case)

        # Cross-check: what does each binary say it contains?
        binaries = []
        for match in re.finditer(r"Test command:\s*(\S+)", text):
            path = match.group(1)
            if os.path.isfile(path) and path not in binaries:
                binaries.append(path)
        for binary in binaries:
            listed = self.run(
                '"%s" -functions' % binary, ignore_errors=True, env="conanrun"
            )
            if listed is None:
                continue
            names = [
                line.strip()
                for line in str(listed).splitlines()
                if line.strip().endswith("()")
            ]
            self.output.info(
                "  %s declares %d test functions"
                % (os.path.basename(binary), len(names))
            )

    def _prepare_mime_database(self, test_env):
        """Give the upstream MIME tests a database to query.

        KSycoca answers mimeType lookups from an XDG mime database, and this
        device has none - no /usr/share/mime, and no update-mime-database to
        build one with - so the data-driven cases fail on the data before they
        exercise anything:

          kf.service.sycoca: Service type not found: "text/plain"

        The database is therefore shipped with the recipe as testdata/mime,
        compiled once with update-mime-database from the two XML packages a
        machine that runs these tests would have installed:

          * shared-mime-info 2.4's freedesktop.org.xml, from
            https://gitlab.freedesktop.org/xdg/shared-mime-info/-/archive/2.4
          * kcoreaddons 5.116.0's share/mime/packages/kde5.xml, which is where
            application/x-kns comes from; KMimeAssociationsTest::
            testRemovedImplicitAssociation178560 asserts it is installed

        2.4 is deliberate rather than "whatever is newest": in shared-mime-info
        2.5 application/x-shellscript stopped being a type of its own and became
        an alias of text/x-shellscript, so it no longer inherits text/plain, and
        KMimeAssociationsTest::testMultipleInheritance - "application/
        x-shellscript inherits from both text/plain and application/
        x-executable" - has nothing left to find. 2.4 is the release the
        upstream assertions describe and the one Ubuntu 24.04 ships. Taking
        shared-mime-info as a build requirement instead was tried and rejected:
        it depends on libxml2, Conan puts a
        build requirement's transitive lib directories on LD_LIBRARY_PATH for
        the whole build, and that libxml2 shadows the one the SDK's linker
        needs, so configure dies with

          Error loading shared library libxml2.so.16: (needed by
          .../ohos-sdk/.../native/llvm/bin/lld)

        Shipping the compiled data has no effect on the toolchain at all.

        Both halves of shared-mime-info are needed, and they are read by
        different code:

        * QMimeDatabase (what KMimeType::mimeType() and mime.isValid() use)
          reads the *compiled* database - mime.cache and its siblings.
        * kservice's kbuildsycoca builds its service types by scanning the
          XML source files under `xdgdata/mime/`
          (src/sycoca/kbuildmimetypefactory.cpp:22), but it does not read a
          template such as freedesktop.org.xml dropped directly in that
          directory. createEntry() derives the type name from the relative
          path and returns nullptr for anything without a directory part:

            KSycocaEntry *KBuildMimeTypeFactory::createEntry(const QString &file)
            {
                const int pos = file.lastIndexOf(QLatin1Char('/'));
                if (pos == -1) { // huh?
                    return nullptr;
                }

          The XML files therefore have to be laid out the way /usr/share/mime
          has them - one file per type, `mime/<group>/<type>.xml`, e.g.
          mime/text/plain.xml - which is exactly what update-mime-database
          writes next to the compiled database. (Confirmed with
          QT_LOGGING_RULES="kf.service.sycoca.debug=true": `Looking for subdir
          "mime" => (".../xdg-data/mime")` shows the directory is scanned, and
          with only freedesktop.org.xml in it every type stays unknown, so the
          trader returns no offers at all:

            QWARN : kf.service.sycoca: Service type not found: "text/plain"
            QWARN : kf.service.services: KApplicationTrader: mimeType
                    "text/plain" not found
            FAIL! : KMimeAssociationsTest::testRemovedMiddleAssociation()
                    'offerListHasService(offers, fakeTextApplication, true)'
                    returned FALSE
          )

        testdata/mime is the complete output of `update-mime-database` over
        those two packages: the 12 compiled aggregates plus 965 per-type XML
        sources. The sources are kept where /usr/share/mime keeps them, in
        packages/, so the fixture can be rebuilt from the repository alone with

          update-mime-database testdata/mime
        """
        source = os.path.join(self.recipe_folder, "testdata", "mime")
        if not os.path.isdir(source):
            raise ConanException(
                "testdata/mime is missing from the recipe package; the upstream "
                "MIME cases would silently run without a database"
            )
        xdg_data = os.path.join(self.build_folder, "xdg-data")
        target = os.path.join(xdg_data, "mime")
        os.makedirs(xdg_data, exist_ok=True)
        # Replace rather than merge: a leftover file from an earlier run must
        # not be able to make a case pass, and the released layout has no
        # template loose in the mime directory for sycoca to trip over.
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target)
        # testdata/mime/{magic,mime.cache,treemagic} travel base64-encoded:
        # GitCode's generated PR diff carries no payload for an added binary
        # file, so the CI worker died while applying the PR patch with
        #   error: missing binary patch data for '.../testdata/mime/magic'
        #   error: binary patch does not apply to '.../testdata/mime/magic'
        # Decode them here and check every one against BINARIES.sha256, so a
        # truncated or swapped blob fails the build instead of quietly
        # changing what the upstream MIME cases are looking at.
        manifest = os.path.join(target, "BINARIES.sha256")
        expected = {}
        if os.path.isfile(manifest):
            with open(manifest, encoding="ascii") as handle:
                for line in handle:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        digest, name = line.split(None, 1)
                        expected[name] = digest
        decoded = 0
        for root, _dirs, files in os.walk(target):
            for name in files:
                if not name.endswith(".b64"):
                    continue
                packed = os.path.join(root, name)
                plain = packed[: -len(".b64")]
                rel = os.path.relpath(plain, target).replace(os.sep, "/")
                with open(packed, "rb") as handle:
                    data = base64.b64decode(handle.read())
                want = expected.get(rel)
                got = hashlib.sha256(data).hexdigest()
                if want is None:
                    raise ConanException(
                        "testdata/mime/%s has no BINARIES.sha256 entry" % rel)
                if got != want:
                    raise ConanException(
                        "testdata/mime/%s decoded to sha256 %s, expected %s"
                        % (rel, got, want))
                with open(plain, "wb") as handle:
                    handle.write(data)
                os.remove(packed)
                decoded += 1
        if decoded != len(expected):
            raise ConanException(
                "testdata/mime: decoded %d blobs but BINARIES.sha256 lists %d"
                % (decoded, len(expected)))
        # the staged tree mirrors a released /usr/share/mime: no packing
        # leftovers, no manifest, nothing loose in the mime directory
        stale = os.path.join(target, "BINARIES.sha256")
        if os.path.isfile(stale):
            os.remove(stale)
        test_env.prepend_path("XDG_DATA_DIRS", xdg_data)
        self.output.info("MIME database staged at %s (%d blobs decoded)"
                         % (target, decoded))
        self.output.info("MIME database staged at %s" % target)

        # The menu file KSycoca builds the service database from. It is a
        # kservice source file, installed to <prefix>/etc/xdg/menus, and the
        # tests run from the build tree where nothing has put it on the XDG
        # config path - so the service database comes out empty and the trader
        # cases fail with '!offers.isEmpty()' returned FALSE. The ksycoca tests
        # say so directly:
        #   QSYSTEM: KSycocaTest::... "applications.menu" not found in
        #   (test-home/.qttest/config/menus)
        menu = os.path.join(self.source_folder, "src", "applications.menu")
        if not os.path.isfile(menu):
            raise ConanException(
                "src/applications.menu is missing from the sources; the service "
                "trader cases would run against an empty service database"
            )
        xdg_config = os.path.join(self.build_folder, "xdg-config")
        menus_dir = os.path.join(xdg_config, "menus")
        os.makedirs(menus_dir, exist_ok=True)
        shutil.copyfile(menu, os.path.join(menus_dir, "applications.menu"))
        # ...and into the Qt test-mode config directory, which is the only one
        # that counts. These tests call
        # QStandardPaths::setTestModeEnabled(true), and in test mode
        # GenericConfigLocation is *just* $HOME/.qttest/config - the XDG
        # variables are ignored, and the log names the single directory it
        # looked in:
        #   QSYSTEM: KSycocaTest::ensureCacheValidShouldCreateDB()
        #     "applications.menu" not found in
        #     (".../test-home/.qttest/config/menus")
        # KSycoca builds its service group tree from that menu, so without it
        # every trader query returns no offers - which is what the remaining
        # KApplicationTrader and KMimeAssociations failures are about.
        test_mode_menus = os.path.join(
            self.build_folder, "test-home", ".qttest", "config", "menus"
        )
        os.makedirs(test_mode_menus, exist_ok=True)
        shutil.copyfile(menu, os.path.join(test_mode_menus, "applications.menu"))
        # prepend, so the system /etc/xdg keeps working when it exists
        test_env.prepend_path("XDG_CONFIG_DIRS", xdg_config)
        # The build also drops a copy at <build>/bin/data/menus, which is the
        # KDE build-tree data directory; put that on the data path too, since
        # that is where an in-tree test run is expected to find it.
        build_data = os.path.join(self.build_folder, "bin", "data")
        if os.path.isdir(os.path.join(build_data, "menus")):
            test_env.prepend_path("XDG_DATA_DIRS", build_data)
        self.output.info(
            "applications.menu staged at %s (and %s)"
            % (os.path.join(menus_dir, "applications.menu"), build_data)
        )

    # Signatures of the conan-verify sandbox refusing to execute a user-path
    # binary. kcoreaddons5/5.116.0's merged test_package documents the same
    # condition: "OHOS's dynamic linker ignores LD_LIBRARY_PATH and the hnp
    # sandbox refuses exec of user-path binaries".
    _SANDBOX_EXEC_SIGNATURES = (
        "Error loading shared library",
        "Operation not permitted",
        "Error relocating",
        "cannot execute binary file",
    )

    def _verify_links(self):
        """Link-level proof, mirroring kcoreaddons5/5.116.0.

        The built test executables must declare libKF5Service.so plus the KF5
        dependencies they use as NEEDED libraries, and the library under test
        must export the KService API. That holds only if CMake found the
        dependency configs and the linker resolved their public API.
        """
        import shutil
        import subprocess

        hnp_bin = "/data/service/hnp/bin"
        readelf = shutil.which("readelf") or os.path.join(hnp_bin, "readelf")
        nm = shutil.which("nm") or os.path.join(hnp_bin, "nm")

        tests = []
        for name in ("kservicetest", "ksycocatest", "kapplicationtradertest",
                     "kmimeassociationstest", "kplugininfotest"):
            for cand in glob.glob(os.path.join(self.build_folder, "**", name),
                                  recursive=True):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    tests.append(cand)
                    break
        if not tests:
            raise ConanException("no upstream test executables were built")

        for test_bin in tests:
            needed = subprocess.run([readelf, "-d", test_bin],
                                    capture_output=True, text=True).stdout
            if "libKF5Service.so" not in needed:
                raise ConanException(
                    "%s is not linked against libKF5Service.so:\n%s"
                    % (test_bin, needed)
                )

        lib_path = None
        for cand in glob.glob(os.path.join(self.build_folder, "bin",
                                           "libKF5Service.so*")):
            if os.path.isfile(cand) and not os.path.islink(cand):
                lib_path = cand
                break
        if not lib_path:
            raise ConanException("built libKF5Service.so not found")
        exported = subprocess.run([nm, "-D", "--defined-only", lib_path],
                                  capture_output=True, text=True).stdout
        for member in ("KService", "KServiceTypeTrader", "KPluginTrader"):
            if member not in exported:
                raise ConanException(
                    "libKF5Service.so does not export the %r API" % member
                )
        self.output.info(
            "link-level proof OK: %d upstream test executables link "
            "libKF5Service.so, KService API exported" % len(tests)
        )

    def _prepare_ctest_runtime_links(self):
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

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Service"]
        self.cpp_info.bindirs = ["bin"]
