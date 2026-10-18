#!/usr/bin/env python3
"""Conan recipe for kdbusaddons 6.29.0 on HarmonyOS PC.

kdbusaddons is a KDE Frameworks 6 (Tier 1) library that provides add-ons to
Qt's D-Bus classes: KDBusService (unique/multiple D-Bus service registration),
KDEDModule, KUpdateLaunchEnvironmentJob, plus the kquitapp6 CLI tool
(libKF6DBusAddons.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - WITH_X11=OFF: Qt6Gui/Qt6GuiPrivate are X11-only and are not linked on
    OHOS (no X11); this avoids the X11-only private Gui dependency while the
    public library surface (Qt6DBus) is fully built
  - BUILD_TESTING=ON: the upstream autotests/tests are really executed, against
    a private D-Bus session bus started from the dbus package (OHOS ships no
    session bus of its own); every buildable upstream test program must pass
  - Dependencies: qtbase/6.11.1.1 (Qt6::DBus, verified consumable via the
    r04 Qt6DBus consumption gate), extra-cmake-modules/6.29.0 (ECM) as build
    tool, qt6linguisttools/6.11.1 for the upstream poqm translation step, and
    dbus/1.14.10.3 as build tool for the test suite (shared libdbus-1.so.3 that
    Qt6DBus dlopen()s, plus dbus-daemon/dbus-run-session)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    copy,
    get,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KdbusaddonsConan(ConanFile):
    name = "kdbusaddons"
    version = "6.29.0.1"
    description = "KDE Frameworks 6 - Addons to QtDBus"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kdbusaddons"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def export(self):
        # passwd_shim.c is compiled by build() for the upstream test run only;
        # a recipe export carries conanfile.py/conandata.yml alone, so the
        # helper has to be exported explicitly to be available in the cache.
        copy(self, "passwd_shim.c", self.recipe_folder, self.export_folder)

    def requirements(self):
        # Qt6DBus >= 6.9.0 is the direct upstream requirement (REQUIRED in
        # CMakeLists.txt). qtbase/6.11.1.1 is the published binary verified
        # consumable by the r04 Qt6DBus consumption gate (libQt6DBus.so +
        # Qt6DBusConfig.cmake + real CMake consumer find_package(Qt6DBus)
        # with Qt6::DBus link).
        self.requires("qtbase/6.11.1.1")

    def build_requirements(self):
        # ECM >= 6.29.0 is REQUIRED upstream. extra-cmake-modules/6.29.0 is
        # the published ECM base for the KF6 path (proved consumable in r03).
        self.tool_requires("extra-cmake-modules/6.29.0")
        # Qt6LinguistTools is a build-time tool set (lrelease/lupdate/lconvert +
        # Qt6::LinguistTools CMake module) required by ECMPoQmTools for the
        # upstream poqm translation step. Published on ohpcd as
        # qt6linguisttools/6.11.1. Consumed as a build requirement, never
        # rebuilt from source (R36).
        self.tool_requires("qt6linguisttools/6.11.1")
        # Qt6DBus does not link libdbus-1: libQt6DBus.so.6 has no DT_NEEDED for
        # it and dlopen()s "libdbus-1.so.3" at run time. The dbus/1.14.10 binary
        # qtbase depends on ships only the static client library, so that
        # run-time lookup fails and every D-Bus user reports "DBus session bus
        # not found" (measured with the upstream test suite below).
        # dbus/1.14.10.3 publishes the shared client library plus the session
        # bus daemon and the dbus-run-session/dbus-send tools. It is consumed as
        # a build requirement - the shared library the upstream test programs
        # load through Qt6DBus, and the daemon they run against - so the
        # run-time dependency graph of qtbase/6.11.1.1, and therefore its
        # published binary, stays untouched.
        self.tool_requires("dbus/1.14.10.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # CMake ships no Platform/HarmonyOS module, so CMAKE_SHARED_LIBRARY_SONAME_*
        # stays empty and lld emits no DT_SONAME. Consumers then record the absolute
        # build-machine path of libKF6DBusAddons.so in DT_NEEDED and fail to load it
        # on CI workers or any clean cache. Provide the flags so the library gets a
        # DT_SONAME and consumers record the bare soname instead.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Qt6Gui/Qt6GuiPrivate are X11-only (qtx11extras_p.h); OHOS has no
        # X11, so build the library without the X11-only GuiPrivate link.
        tc.variables["WITH_X11"] = "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"

        # Qt6Config.cmake resolves COMPONENTS relative to Qt6_DIR (qtbase),
        # so find_package(Qt6 COMPONENTS LinguistTools) would look inside
        # qtbase's lib/cmake and fail. Pin Qt6LinguistTools_DIR explicitly to
        # the qt6linguisttools package so ECMPoQmTools resolves the component.
        ltt = self.dependencies.build.get("qt6linguisttools")
        if ltt:
            tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
                ltt.package_folder, "lib", "cmake", "Qt6LinguistTools"
            )

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ECMPoQmTools,
        # ECMGenerateQDoc, etc.) are found.
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            ltt = self.dependencies.build.get("qt6linguisttools")
            if ltt:
                ltt_pkg = ltt.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ltt_pkg}/lib/cmake")')
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{ltt_pkg}/lib/cmake/Qt6LinguistTools")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ltt_pkg}/lib/cmake/Qt6LinguistTools")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{ltt_pkg}/lib")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    # ── upstream test suite ───────────────────────────────────────────────
    # kdbusaddons ships four upstream test programs; every one of them drives a
    # real D-Bus session bus:
    #   autotests/kdbusservicetest.cpp  registered with CTest by upstream
    #   tests/dbuscalltest.cpp          upstream only calls ecm_mark_as_test()
    #   tests/syncdbusenvtest.cpp       on these two, which never emits
    #                                   add_test(); CTest does not know about
    #                                   them, so they are run directly
    #   autotests/deadservicetest.cpp   wrapped in if(UNIX) upstream, hence not
    #                                   built for OHOS at all
    # OHOS has no session bus, so start a private one with dbus-run-session from
    # the dbus package (its dbus-daemon listens on an abstract socket, since the
    # build sandbox denies binding a filesystem unix socket) and run the suite
    # against it. These are real upstream assertions: a failure fails the build.
    SESSION_BUS_CONFIG = """<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>{listen}</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""

    # Upstream calls ecm_mark_as_test() on these instead of ecm_add_tests(),
    # which never produces an add_test() entry, so CTest cannot run them.
    EXTRA_UPSTREAM_TESTS = ("dbuscalltest", "syncdbusenvtest")

    def _dbus_package_folder(self):
        # The build-context dbus (tool_requires, 1.14.10.3) is the one that
        # carries the shared client library and the session bus daemon; the
        # host-context dbus/1.14.10 that qtbase pulls in only ships the static
        # library, so it must not be picked up here.
        dbus = self.dependencies.build.get("dbus")
        if dbus is None or not dbus.package_folder:
            raise ConanException(
                "the dbus package (shared libdbus-1.so.3 + dbus-daemon + "
                "dbus-run-session) is required to run the upstream test suite"
            )
        return dbus.package_folder

    def _find_test_binary(self, name):
        preferred = os.path.join(self.build_folder, "bin", name)
        if os.path.isfile(preferred):
            return preferred
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        raise ConanException("upstream test program '{}' was not built".format(name))

    def _run_upstream_tests(self):
        dbus_pkg = self._dbus_package_folder()
        dbus_daemon = os.path.join(dbus_pkg, "bin", "dbus-daemon")
        bus_runner = os.path.join(dbus_pkg, "bin", "dbus-run-session")
        for tool in (dbus_daemon, bus_runner):
            if not os.path.isfile(tool):
                raise ConanException("dbus test tool missing: {}".format(tool))

        bus_config = os.path.join(self.build_folder, "ctest-session-bus.conf")
        with open(bus_config, "w") as handle:
            handle.write(
                self.SESSION_BUS_CONFIG.format(
                    listen="unix:abstract=ohos-kdbusaddons-ctest"
                )
            )

        # The sandbox UID has no passwd entry and Qt6DBus' dlopen()ed libdbus
        # aborts the bus attachment without one (see passwd_shim.c).
        shim_so = os.path.join(self.build_folder, "test-passwd-shim.so")
        c_compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        self.run(
            '"{}" -shared -fPIC -o "{}" "{}"'.format(
                c_compiler, shim_so, os.path.join(self.recipe_folder, "passwd_shim.c")
            )
        )

        test_env = Environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("TZ", "Asia/Shanghai")
        test_env.define("LD_PRELOAD", shim_so)
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dbus_pkg, "lib"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                test_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                test_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            test_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )

        commands = [
            'echo "=== upstream ctest suite ==="',
            'ctest --test-dir "{}" --output-on-failure --no-tests=error '
            "--timeout 120".format(self.build_folder),
        ]
        for name in self.EXTRA_UPSTREAM_TESTS:
            commands.append('echo "=== upstream test: {} ==="'.format(name))
            commands.append('"{}"'.format(self._find_test_binary(name)))
            commands.append('echo "=== upstream test {} PASSED ==="'.format(name))
        with test_env.vars(self).apply():
            self.run(
                '"{}" --dbus-daemon="{}" --config-file="{}" -- /bin/sh -c {}'.format(
                    bus_runner,
                    dbus_daemon,
                    bus_config,
                    shlex.quote("set -e; " + "; ".join(commands)),
                ),
                env="conanrun",
            )
        self.output.info(
            "upstream D-Bus test suite passed on a private session bus"
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6DBusAddonsConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6DBus). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6DBusAddons"]
        # The package ships the kquitapp6 CLI tool in bin/ (R38: declared in
        # the software-level commands.json); expose it so consumers and the
        # PF8 static gate see this is not a pure-library package.
        self.cpp_info.bindirs = ["bin"]
