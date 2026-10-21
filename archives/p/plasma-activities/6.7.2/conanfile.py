#!/usr/bin/env python3
"""Conan recipe for plasma-activities 6.7.2 on HarmonyOS PC.

plasma-activities is the KDE Plasma activities library. It ships
libPlasmaActivities.so (the Consumer/Controller/Info C++ API and its D-Bus
client), the org.kde.activities QML module (plasmaactivitiesextensionplugin)
and the plasma-activities-cli6 diagnostic binary. It is the base of the
Plasma 6 stack used by this repository (libplasma -> kscreenlocker -> kwin).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list).
  - Qt dependency: qtbase-sql-dbus/6.11.1. The top-level CMakeLists asks for
    Qt6 Core+DBus and src/imports asks for Gui/Qml/Quick/Sql; the plain
    qtbase package is built with FEATURE_dbus=OFF and without the Sql module,
    while qtbase-sql-dbus is the superset build that provides Qt6
    Core/DBus/Gui/Widgets/Sql/Test from one coherent build
    (kactivitymanagerd 6.7.2 precedent). qtdeclarative/6.11.1 provides Qt6
    Qml/Quick for the QML module.
  - KF6 6.26 baseline: kconfig + kcoreaddons, the two frameworks linked by
    src/imports/CMakeLists.txt (KF6::ConfigCore, KF6::CoreAddons).
  - Shared libraries are emitted unversioned with an explicit bare SONAME
    (CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON plus -Wl,-soname, in both the
    variable and the cache_variable channel): HMDFS on the device user volume
    rejects symlink() with EPERM, so the upstream VERSION/SOVERSION symlink
    chain cannot be created (E330; kcolorpicker/expat/kwidgetsaddons
    precedent).
  - BUILD_TESTING=ON. Upstream registers only QFlatSetTest with CTest. The
    PlasmaActivitiesTest integration runner (six further QTest slots) is
    built but has no add_test and requires a running kactivitymanagerd over a
    session D-Bus, which OHOS does not provide; only QFlatSetTest runs here
    (see notes.md for the per-function inventory).
  - ECM_MODULE_PATH is set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project relies on.
  - conan_cmakedeps_paths.cmake is written manually because every Qt/KF
    package here uses cmake_find_mode=none (CMakeDeps does not add their
    lib/cmake dirs); qtbase-sql-dbus is prepended last so find_package(Qt6)
    resolves to the superset build that carries Qt6::DBus/Sql.
  - /system/lib64 and the OHOS SDK llvm/lib are prepended to LD_LIBRARY_PATH
    while configuring/building/testing: the sandbox LD_LIBRARY_PATH contains
    an incompatible libc++_shared.so (under
    /data/storage/el1/bundle/libs/arm64) and ECM's KDEInstallDirs runs the
    qtbase qtpaths host tool during configure (kconfig 6.26.0 / bluez-qt
    6.28.0 precedent).
  - 0001-manager-guard-null-session-bus.patch: QDBusConnection::sessionBus()
    .interface() returns nullptr when no session bus is reachable (always the
    case on OHOS, which has no session D-Bus). Manager::self() and
    serviceOwnerChanged() dereference it unconditionally and crash on the
    first Consumer construction. The patch adds the missing null checks; it
    is a plain null guard with no platform macros, so it is applied on every
    platform (kscreenlocker 6.7.2 precedent): the offline consumer contract
    that test_package enforces holds on any headless system.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class PlasmaActivitiesConan(ConanFile):
    name = "plasma-activities"
    version = "6.7.2"
    description = (
        "KDE Plasma activities library: Consumer/Controller/Info C++ API, "
        "the org.kde.activities QML module and the plasma-activities-cli6 tool"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/plasma/plasma-activities"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Superset Qt6 build: Core/DBus/Gui/Widgets/Sql/Test in one package.
        # The plain qtbase/6.11.1 kept below is built without DBus and Sql and
        # cannot satisfy the top-level find_package(Qt6 COMPONENTS Core DBus)
        # nor the QML module's Sql link (kactivitymanagerd 6.7.2 precedent).
        self.requires("qtbase-sql-dbus/6.11.1")
        # qtdeclarative/kconfig/kcoreaddons are built against qtbase/6.11.1;
        # keep the plain package in the graph at the matching version.
        self.requires("qtbase/6.11.1")
        # Qt6 Qml/Quick for the org.kde.activities QML module.
        self.requires("qtdeclarative/6.11.1")
        # src/imports/CMakeLists.txt: find_package(KF6Config 6.26.0 REQUIRED)
        # and find_package(KF6CoreAddons 6.26.0 REQUIRED).
        self.requires("kconfig/6.26.0.1")
        self.requires("kcoreaddons/6.26.0.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # HMDFS rejects symlink() with EPERM, so the versioned
        # libPlasmaActivities.so.7 -> .so.7.0.0 chain cannot be created on
        # device. Emit the unversioned library only (E330 precedent).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        # CMake ships no Platform/HarmonyOS module, so
        # CMAKE_SHARED_LIBRARY_SONAME_* stays empty and lld emits no
        # DT_SONAME; consumers then record the absolute build-machine path of
        # libPlasmaActivities.so in DT_NEEDED. Provide the flags in both
        # channels (kwidgetsaddons 6.28.0 precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are
        # found (kcrash 6.26.0 precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # Qt6Config.cmake resolves COMPONENTS relative to Qt6_DIR (the
        # qtbase-sql-dbus prefix); without this cache variable
        # find_package(Qt6 COMPONENTS Qml Quick) would not look inside the
        # qtdeclarative package (analitza 26.04.0 precedent).
        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtdeclarative:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = (
                qtdeclarative.package_folder
            )

        # Every Qt/KF package here uses cmake_find_mode=none -> CMakeDeps
        # does not generate conan_cmakedeps_paths.cmake. Create it manually
        # so the toolchain adds their cmake dirs to CMAKE_PREFIX_PATH/
        # CMAKE_MODULE_PATH, then prepend qtbase-sql-dbus last so it wins the
        # find_package(Qt6) lookup (kactivitymanagerd 6.7.2 precedent).
        qtbase_sql_dbus = self.dependencies.get("qtbase-sql-dbus")
        if qtbase_sql_dbus:
            qt_pkg = qtbase_sql_dbus.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
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
        # The null-session-bus guard is a platform-agnostic portability fix
        # (no platform macros; kscreenlocker 6.7.2 precedent): apply it on
        # every platform so the installed library and the offline consumer
        # contract enforced by test_package agree everywhere.
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
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
                    "PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "PATH", os.path.join(dep.package_folder, "libexec")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        # The superset Qt build must precede the plain qtbase pulled by
        # qtdeclarative/kconfig/kcoreaddons at runtime as well (last prepend
        # lands at the front of LD_LIBRARY_PATH).
        qtbase_sql_dbus = self.dependencies.get("qtbase-sql-dbus")
        if qtbase_sql_dbus:
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(qtbase_sql_dbus.package_folder, "lib")
            )
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64 which
            # shadows the compatible one; prepend /system/lib64 so qtpaths
            # (invoked by KDEInstallDirs during configure) and the build tools
            # resolve the compatible libc++ first (kconfig 6.26.0 / bluez-qt
            # 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.info("Cross build: skipping the upstream test suite")
            return
        if self.conf.get("tools.build:skip_test", default=False):
            self.output.info("tools.build:skip_test set: skipping ctest")
            return
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
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
        with test_env.vars(self).apply():
            # QFlatSetTest is the only upstream test registered with CTest
            # (autotests/core/CMakeLists.txt). PlasmaActivitiesTest is built
            # but not registered: its custom runner needs kactivitymanagerd
            # and a session D-Bus (see notes.md).
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 120'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own PlasmaActivitiesConfig.cmake with the
        # proper find_dependency(Qt6Core) chain. Use cmake_find_mode=none so
        # CMakeDeps does not shadow it (kwidgetsaddons 6.28.0 precedent).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["PlasmaActivities"]
