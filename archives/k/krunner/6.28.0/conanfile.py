#!/usr/bin/env python3
"""Conan recipe for krunner 6.28.0 on HarmonyOS PC.

krunner is the KDE Frameworks 6 launcher framework: the KF6Runner
library (AbstractRunner, QueryMatch, RunnerSyntax, RunnerContext and the
RunnerManager plugin orchestrator with its D-Bus remote-runner protocol,
libKF6Runner.so) plus the runner plugin template tree (src/templates).

Upstream hard requirements: Qt6 >= 6.10.0 (Core/Gui/DBus, Test for the
autotests), ECM >= 6.28.0, KF6 >= 6.28.0 (Config/CoreAddons/I18n
REQUIRED, ItemModels optional, WindowSystem REQUIRED).

OHOS-specific adaptations:
  - patches/0001: KF_DEP_VERSION 6.28.0 -> 6.26.0. The ohpcd-published
    KF6 stack stops at 6.26.0 (kconfig/kcoreaddons/kwindowsystem
    have .1 fix releases there; ki18n and kitemmodels stop at 6.26.0). Only the
    KF_DEP_VERSION line is lowered: the find_package(ECM 6.28.0) line
    stays untouched because the extra-cmake-modules/6.29.0 tool package
    satisfies it.
  - patches/0002: relocatable basename SONAME linkage (kscreenlocker
    6.7.2 0008 / kpackage/6.26.0.1 0005 precedent, device-proven). The
    published KF6 libraries carry no versioned SONAME chain usable on
    HMDFS (symlinks are denied on /storage), so linking them by their
    absolute Conan cache paths would bake machine-private paths into
    libKF6Runner.so's DT_NEEDED (non-relocatable, E537). lld records the
    name as given on the command line, so the KF6 dependencies are
    linked by exact-file-name -l: flags (bare basenames) with the
    dependency directories attached PRIVATE to KF6Runner; KF6Runner
    itself gets an explicit -Wl,-soname,libKF6Runner.so where the
    platform module defines no soname flag. KF6::CoreAddons stays on the
    link INTERFACE only (the public headers include
    <KPluginFactory>/<KPluginMetaData>; the installed
    KF6RunnerConfig.cmake already find_dependency(KF6CoreAddons)
    upstream, so it is exported by name, never by absolute path).
    Usage requirements of the deps that leave the link line are copied
    by walking the INTERFACE_LINK_LIBRARIES transitive closure of the
    direct KF6 deps with -NOTFOUND sentinel guards on every
    get_target_property lookup (the KDE-installed targets files set the
    per-config IMPORTED_LOCATION_RELEASE only).
  - patches/0003: optional KWaylandExtras. dbusrunner.cpp includes
    <KWaylandExtras> unconditionally, but kwindowsystem publishes that
    header only when it is built with Wayland support -- it is absent
    from the ohpcd 6.26.0.1 package. The consuming block is already
    gated on KWindowSystem::isPlatformWayland() at run time, so a
    __has_include capability probe (a plain C++17 feature test, no
    platform macros) compiles it out where the header is missing and
    keeps upstream behaviour everywhere else.
  - patches/0004: libc++ 15 ranges compatibility. autotests/
    threadingtest.cpp calls std::ranges::all_of, but the OHOS SDK's
    libc++ ships the ranges algorithms disabled by default
    (_LIBCPP_HAS_NO_INCOMPLETE_RANGES): the call does not resolve even
    under -std=c++20. This is the tree's only ranges use, so the call
    is rewritten onto the semantically identical short-circuiting
    std::all_of iterator-pair overload, plus the <algorithm> include
    it needs (enabling the ranges algorithms instead would take
    -D_LIBCPP_ENABLE_EXPERIMENTAL, flipping experimental standard
    library behaviour tree-wide).
  - patches/0005: test-only fixture-installation hardening.
    autotests/runnermanagersinglerunnermodetest.cpp
    testLoadingDisabledRunner() installs the two DBus-runner .desktop
    fixtures with bare QFile::copy() calls whose result is discarded.
    QFile::copy() refuses to overwrite an existing destination, so a
    reused XDG_DATA_HOME turns the install into a silent no-op and the
    following runner-count assertion fails as an opaque 0-vs-1
    mismatch. Stale destinations are removed first, both copies are
    asserted, and the fixture directory, copy sources, QStandardPaths
    data locations and metadata-offer list are dumped through qWarning
    so a remaining environment difference is visible in the ctest log.
  - patches/0006: test-only plain-copy fixture installation.
    The 0005 instrumentation showed on CI that both QFile::copy() calls
    return false even though the destination directory was just created
    and is writable, and the fixture sources exist (the dump lists both
    source paths and an empty destination directory). That points at
    QFile::copy()'s QSaveFile temporary-file + rename path failing
    silently here, not at stale destinations. The fixtures are now
    installed with a plain QFile read/write copy (ReadOnly source,
    WriteOnly|Truncate destination, short-write check) and each failure
    path prints the file error string, keeping any remaining
    environment difference visible in the ctest log.
  - BUILD_TESTING=ON: the 7 upstream autotests build and run. 4 of them
    (dbusrunnertest, runnermanagersinglerunnermodetest, runnermanagertest,
    threadingtest) start the testremoterunner helper and need a live
    session D-Bus; the recipe brings one up itself (dbus/1.14.10.3
    ships dbus-daemon; unix socket under /data/storage/el2/base with the
    getpwuid shim, TCP/ANONYMOUS fallback -- both device-proven in the
    dbus package's own test_package). If no bus can be started the 4
    D-Bus-dependent tests are waived with a warning; any other failure
    fails the build.
  - Dependencies: qtbase/6.11.1 (Core/Gui/Widgets/Test) +
    qtbase-sql-dbus/6.11.1 (Qt6::DBus; the two packages coexist by
    design, knighttime/kscreenlocker precedent), the KF6 stack at
    6.26.0 (ki18n and kitemmodels at 6.26.0 -- no .1 release exists; the
    others at their .1 fix releases, which inject the bare DT_SONAME so
    consumers record the bare soname instead of an absolute cache path)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none; Qt6_DIR is re-asserted to qtbase-sql-dbus LAST
    so find_package(Qt6 COMPONENTS DBus) resolves there
  - package() re-signs every installed ELF (CMake install rewrites the
    RUNPATH, which invalidates the build-time .codesign section and
    makes the OHOS loader refuse the library with "Permission denied";
    kscreenlocker/knotifyconfig precedent)
"""
import glob
import os
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class KrunnerConan(ConanFile):
    name = "krunner"
    version = "6.28.0"
    description = "KDE Frameworks 6 - Framework for providing different actions given a string query"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/krunner"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # copytree (not conan.tools.files.copy) so the shim lands at the
        # single-layer es/test_shim/ohos_nopw.c: copy() keeps the matched
        # item's path relative to src, which nested it one level deeper
        # (es/test_shim/test_shim/ohos_nopw.c) and made the shim
        # unresolvable in cache builds (kcoreaddons5 5.116.0.1 precedent
        # uses copytree for the same identity_shim.c export).
        shim_src = os.path.join(self.recipe_folder, "test_shim")
        shim_dst = os.path.join(self.export_sources_folder, "test_shim")
        if os.path.isdir(shim_src):
            if os.path.isdir(shim_dst):
                shutil.rmtree(shim_dst)
            shutil.copytree(shim_src, shim_dst)

    def validate(self):
        # Shared-only by construction: patch 0002 gates -Wl,-soname on the
        # shared link, package() runs the OHOS ELF refresh on
        # lib/libKF6Runner.so and the consumer test loads the shared object
        # at run time. The shared option stays declared (package_id shape),
        # but a static request would silently produce a package that claims
        # shared=False while containing a shared library -- reject it like
        # the other OHOS adaptations that only package .so (kscreenlocker
        # 6.7.2 precedent).
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "krunner 6.28.0 OHOS adaptation only packages shared "
                "libraries (libKF6Runner.so); use -o '&:shared=True' "
                "(the default)."
            )

    def requirements(self):
        # Qt6::Core/Gui/Widgets/Test come from the plain qtbase build
        # (Qt6::Test is used by the upstream autotests).
        self.requires("qtbase/6.11.1")
        # Qt6::DBus lives only in the qtbase-sql-dbus variant (the plain
        # qtbase/6.11.1 is built with FEATURE_dbus=OFF; the two packages
        # coexist by design, knighttime/kscreenlocker precedent).
        self.requires("qtbase-sql-dbus/6.11.1")
        # KF6 stack at 6.26.0. Direct component use in the sources:
        # runnermanager.cpp opens KSharedConfig (KF6::ConfigCore),
        # abstractrunner.cpp/runnersyntax.cpp use KLocalizedString
        # (KF6::I18n), src/model/resultsmodel.cpp includes
        # <KDescendantsProxyModel> (KF6::ItemModels), src/dbusrunner.cpp
        # uses KWindowSystem (KF6::WindowSystem) and the public headers
        # include <KPluginFactory>/<KPluginMetaData> (KF6::CoreAddons).
        # The autotests additionally link KF6::ConfigCore directly.
        # The .1 fix releases inject the bare DT_SONAME (consumers record
        # the bare soname instead of an absolute cache path; kscreen
        # CI-proven); ki18n and kitemmodels have no .1 release.
        self.requires("kconfig/6.26.0.1")       # KF6::ConfigCore
        self.requires("kcoreaddons/6.26.0.1")   # KF6::CoreAddons
        self.requires("ki18n/6.26.0")           # KF6::I18n
        self.requires("kitemmodels/6.26.0")     # KF6::ItemModels
        self.requires("kwindowsystem/6.26.0.1")  # KF6::WindowSystem

    def build_requirements(self):
        # ECM >= 6.28.0 REQUIRED upstream (the find_package(ECM 6.28.0)
        # line stays untouched); extra-cmake-modules/6.29.0 is the
        # published ECM base for this KF6 generation (kdbusaddons 6.29.0
        # precedent).
        self.tool_requires("extra-cmake-modules/6.29.0")
        # dbus-daemon for the session bus the 4 D-Bus-dependent upstream
        # autotests need; the package runs natively on this host (it is
        # device-proven by its own test_package). Build-context only:
        # the shipped krunner package does not depend on it.
        self.tool_requires("dbus/1.14.10.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The profile pins cppstd=17; the KF6 6.28 headers need C++20
        # (KDEFrameworkCompilerSettings raises it upstream; make it
        # explicit here).
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but
        # the CMakeDeps-generated ECMConfig.cmake does not. Set it
        # manually so the KDE cmake modules are found (kdbusaddons
        # 6.29.0 precedent).
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # conan_cmakedeps_paths.cmake created manually because qtbase
        # uses cmake_find_mode=none (kscreenlocker precedent).
        qtbase = self.dependencies.get("qtbase")
        lines = []
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        # Every host dependency's lib/cmake so find_package(KF6...) and
        # the per-package KF6 config files resolve inside the conan
        # cache. The plain qtbase/6.11.1 lacks Qt6DBus and must not win
        # the Qt6_DIR lookup -- the re-assert below puts
        # qtbase-sql-dbus back first.
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        if qtbase and qtbase.package_folder:
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
        sqlqt = self.dependencies.get("qtbase-sql-dbus")
        if sqlqt and sqlqt.package_folder:
            # Re-assert the DBus-enabled qtbase LAST so it wins the
            # Qt6_DIR lookup (list(PREPEND) puts the last entry first).
            lines.append(f'set(Qt6_DIR "{sqlqt.package_folder}/lib/cmake/Qt6")')
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{sqlqt.package_folder}/lib/cmake")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _sdk_llvm_lib_dirs(self):
        # The OHOS SDK root is environment specific, so prefer the
        # llvm/lib directory implied by the profile's compiler and fall
        # back to globbing the installed SDK. The SDK version stays
        # unpinned on purpose: a pinned version breaks as soon as a CI
        # image ships a different SDK release (kconfig 6.26.0.1
        # precedent).
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx:
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            )
        )
        return [c for c in dict.fromkeys(candidates) if os.path.isdir(c)]

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in self._sdk_llvm_lib_dirs():
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM's KDEInstallDirs6 runs the qtbase qtpaths host tool
            # during configure (ecm_query_qt -> QT_INSTALL_PREFIX). The
            # sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64
            # (and the qtbase lib dir, already added by
            # _library_runtime_env) so the loader resolves the compatible
            # libc++ first (kconfig 6.26.0.1 / bluez-qt 6.28.0
            # precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in self._sdk_llvm_lib_dirs():
                test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # Same /system/lib64 reasoning as _cmake_build_env.
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        xdg_data_dirs = os.path.join(self.build_folder, "xdg-data-dirs")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.makedirs(xdg_data_dirs, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        # The runner plugin scan must find nothing outside the test's own
        # static plugins: point XDG_DATA_DIRS at an empty directory.
        test_env.define("XDG_DATA_DIRS", xdg_data_dirs)
        self._prepare_ctest_runtime_links()
        bus_proc = self._start_session_bus(test_env)
        result = None
        try:
            with test_env.vars(self).apply():
                result = subprocess.run(
                    [
                        "ctest",
                        "--test-dir", self.build_folder,
                        "--output-on-failure",
                        "--no-tests=error",
                        "--timeout", "300",
                    ],
                    cwd=self.build_folder,
                    env=dict(os.environ),
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )
        finally:
            self._stop_bus(bus_proc)
        if result.stdout:
            self.output.info(result.stdout)
        if result.stderr:
            self.output.info(result.stderr)
        if result.returncode == 0:
            self.output.info("upstream ctest: all tests passed")
            return
        failed = re.findall(r"(?m)^\s*\d+ - (\S+) \(", result.stdout or "")
        bus_tests = {
            "dbusrunnertest",
            "runnermanagersinglerunnermodetest",
            "runnermanagertest",
            "threadingtest",
        }
        if bus_proc is None and failed and set(failed) <= bus_tests:
            # The 4 D-Bus-dependent tests cannot run without a session
            # bus; without one they fail with a runtime environment
            # limitation, not a package defect (kdbusaddons 6.29.0 /
            # karchive precedent: record the outcome, warn, do not block
            # package creation on environment-caused failures).
            self.output.warning(
                "No session bus could be started; waived D-Bus-dependent "
                "test failure(s): " + ", ".join(sorted(set(failed)))
            )
            return
        raise ConanException(
            "upstream ctest failed (exit %s); failed tests: %s"
            % (result.returncode, ", ".join(sorted(set(failed))) or "unknown")
        )

    def _prepare_ctest_runtime_links(self):
        # ctest runs the tests with WORKING_DIRECTORY set to the test
        # binary's directory (<build>/autotests), and a library recorded
        # in DT_NEEDED as the build-tree-relative "../../bin/..." would
        # then resolve to <build>/../bin -- next to, not inside, the
        # build folder. Stage libKF6Runner.so there (kconfig 6.26.0.1
        # _prepare_ctest_runtime_links precedent; symlink when the
        # filesystem allows it, copy otherwise -- HMDFS denies symlinks).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        for lib_name in ("libKF6Runner.so",):
            src = os.path.join(self.build_folder, "bin", lib_name)
            dst = os.path.join(compatibility_bin, lib_name)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    # ------------------------------------------------------------------
    # Session bus for the D-Bus-dependent autotests.
    # ------------------------------------------------------------------

    def _start_session_bus(self, test_env):
        """Start a session bus for the 4 D-Bus-dependent autotests.

        Returns the daemon Popen handle (or None when no bus could be
        started). On success DBUS_SESSION_BUS_ADDRESS is defined in
        test_env. Transport selection follows the dbus/1.14.10.3
        test_package (device-proven): a unix socket needs an
        AF_UNIX-capable directory (/tmp is a read-only erofs; HMDFS under
        $HOME denies bind, /data/storage/el2/base works) and the
        getpwuid shim on the daemon (the sandbox uid 20020101 has no
        /etc/passwd entry, which makes dbus-daemon drop EXTERNAL
        handshakes); TCP on 127.0.0.1 with ANONYMOUS auth is the
        fallback.
        """
        dbus = self.dependencies.build.get("dbus")
        if not dbus or not dbus.package_folder:
            self.output.warning(
                "dbus tool package unavailable; running without a session bus")
            return None
        daemon = os.path.join(dbus.package_folder, "bin", "dbus-daemon")
        if not os.path.isfile(daemon):
            self.output.warning(
                "dbus-daemon not found in %s; running without a session bus"
                % dbus.package_folder)
            return None
        shim = self._build_bus_shim()
        bus_dir = os.path.join(self.build_folder, "test-bus")
        os.makedirs(bus_dir, exist_ok=True)
        attempts = []
        socket_dir = self._probe_socket_dir()
        if socket_dir:
            attempts.append(("unix", socket_dir))
        attempts.append(("tcp", ""))
        for transport, sdir in attempts:
            proc, address = self._try_bus(daemon, shim, bus_dir, transport, sdir)
            if address:
                test_env.define("DBUS_SESSION_BUS_ADDRESS", address)
                self.output.info(
                    "Session bus for upstream autotests: %s (%s transport)"
                    % (address, transport))
                return proc
        self.output.warning(
            "Could not start a session bus; the D-Bus-dependent autotests "
            "will be waived if they fail")
        return None

    def _try_bus(self, daemon, shim, bus_dir, transport, socket_dir):
        env_over = {}
        if transport == "unix":
            sock = os.path.join(socket_dir, "kr-session-bus.sock")
            try:
                os.unlink(sock)
            except OSError:
                pass
            config = (
                '<busconfig>\n'
                '  <type>session</type>\n'
                '  <listen>unix:path=%s</listen>\n'
                '  <auth>EXTERNAL</auth>\n'
                '  <keep_umask/>\n'
                '  <policy context="default">\n'
                '    <allow send_destination="*" eavesdrop="true"/>\n'
                '    <allow eavesdrop="true"/>\n'
                '    <allow own="*"/>\n'
                '  </policy>\n'
                '</busconfig>\n' % sock
            )
            if shim:
                env_over["LD_PRELOAD"] = shim
        else:
            config = (
                '<busconfig>\n'
                '  <type>session</type>\n'
                '  <listen>tcp:host=127.0.0.1,port=0</listen>\n'
                '  <auth>ANONYMOUS</auth>\n'
                '  <allow_anonymous/>\n'
                '  <keep_umask/>\n'
                '  <policy context="default">\n'
                '    <allow send_destination="*" eavesdrop="true"/>\n'
                '    <allow eavesdrop="true"/>\n'
                '    <allow own="*"/>\n'
                '  </policy>\n'
                '</busconfig>\n'
            )
        conf_path = os.path.join(bus_dir, "session-%s.conf" % transport)
        with open(conf_path, "w") as f:
            f.write(config)
        log_path = os.path.join(bus_dir, "daemon-%s.log" % transport)
        env = dict(os.environ)
        env.update(env_over)
        # Pin the daemon's own package lib dir first in LD_LIBRARY_PATH:
        # dbus-daemon carries a build-time RUNPATH into the package's
        # build tree, and an ambient LD_LIBRARY_PATH entry otherwise
        # shadows the package's libdbus-1.so.3 with an unusable one
        # (observed: "Error relocating .../dbus-daemon: dbus_free: symbol
        # not found"), so the daemon died before printing its address.
        # LD_LIBRARY_PATH is searched before DT_RUNPATH, so the pinned
        # dir wins even when that stale path exists.
        dbus_lib = os.path.join(
            os.path.dirname(os.path.dirname(daemon)), "lib")
        ld_path = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = dbus_lib + (":" + ld_path if ld_path else "")
        with open(log_path, "w") as log:
            try:
                proc = subprocess.Popen(
                    [daemon, "--config-file=" + conf_path,
                     "--print-address", "--nofork"],
                    stdout=log, stderr=subprocess.STDOUT, env=env,
                )
            except OSError as exc:
                self.output.warning("dbus-daemon launch failed: %s" % exc)
                return None, ""
            address = ""
            deadline = time.time() + 10
            pattern = re.compile(r"^(unix:path=\S+|tcp:host=\S+,\S+)$", re.M)
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                try:
                    with open(log_path) as fh:
                        match = pattern.search(fh.read())
                except OSError:
                    match = None
                if match:
                    address = match.group(1)
                    break
                time.sleep(0.1)
        if address:
            return proc, address
        self.output.warning(
            "Session bus (%s) did not come up; see %s" % (transport, log_path))
        self._stop_bus(proc)
        return None, ""

    @staticmethod
    def _stop_bus(proc):
        if not proc:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        except OSError:
            pass

    def _probe_socket_dir(self):
        """Return the first directory where an AF_UNIX socket can be
        bound, listened on and connected to, or "" (dbus/1.14.10.3
        test_package precedent: /tmp is read-only and HMDFS denies
        bind)."""
        candidates = [
            "/data/storage/el2/base/tmp",
            "/data/storage/el2/base",
            os.environ.get("TMPDIR", ""),
            tempfile.gettempdir(),
            self.build_folder,
        ]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
            except OSError:
                continue
            path = os.path.join(candidate, "kr-bus-probe-%d.sock" % os.getpid())
            try:
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    server.bind(path)
                    server.listen(1)
                    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    try:
                        client.connect(path)
                        conn, _ = server.accept()
                        conn.close()
                    finally:
                        client.close()
                finally:
                    server.close()
                os.unlink(path)
                return candidate
            except OSError:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        return ""

    def _build_bus_shim(self):
        """Compile test_shim/ohos_nopw.c (getpwuid shim, dbus/1.14.10.3
        test_package precedent). Returns the .so path or "" when the
        shim cannot be built (the unix attempt will then fail its
        EXTERNAL handshake and the TCP fallback takes over)."""
        # Resolve where the shim actually is: in an export/cache build the
        # recipe folder (e/) holds only the conanfile, while the exported
        # shim lands in the export_sources/source folders; a plain local
        # `conan build` sees it under recipe_folder. A miss is warned, not
        # silently swallowed (the unix bus would then fail its EXTERNAL
        # handshake and the TCP fallback would cover it up).
        src = ""
        for base in (self.source_folder, self.export_sources_folder,
                     self.recipe_folder):
            if not base:
                continue
            candidate = os.path.join(base, "test_shim", "ohos_nopw.c")
            if os.path.isfile(candidate):
                src = candidate
                break
        if not src:
            self.output.warning(
                "test_shim/ohos_nopw.c not found under source/export_sources/"
                "recipe folders; the unix bus attempt will fail its EXTERNAL "
                "handshake")
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp")
        if not cc:
            cc = shutil.which("cc") or shutil.which("clang") or ""
        if not cc:
            return ""
        out = os.path.join(self.build_folder, "test-bus", "libhos_nopw.so")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            subprocess.run(
                [cc, "-shared", "-fPIC", "-O2", "-o", out, src],
                check=True, capture_output=True, text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            self.output.warning("Could not build the getpwuid shim: %s" % exc)
            return ""
        return out

    # ------------------------------------------------------------------
    # Packaging.
    # ------------------------------------------------------------------

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

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
        # The value lands in a shell command line: quote for the shell
        # (shlex) so $, backticks and backslashes stay inert.
        return shlex.quote(str(value))

    def _sign_ohos_elf_tree(self, root_folder):
        # CMake install rewrites the RUNPATH of every installed ELF,
        # which invalidates the build-time .codesign section; re-sign
        # everything with the device binary-sign-tool (kscreenlocker
        # 6.7.2 precedent).
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

    def package_info(self):
        # The project installs its own KF6RunnerConfig.cmake with proper
        # dependency tracking (find_dependency on KF6CoreAddons). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it (KF6
        # precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Runner"]
