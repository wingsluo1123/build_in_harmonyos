#!/usr/bin/env python3
"""Conan recipe for knotifications 6.28.0 on HarmonyOS PC.

knotifications is a KDE Frameworks 6 library providing desktop
notification support (libKF6Notifications.so).

OHOS-specific adaptations (refreshed from the 6.26.0 recipe of the same
chain; kitemviews 6.28.0 / kcontacts 6.28.0 siblings):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_DESIGNERPLUGIN=OFF: Qt6UiPlugin is not part of the qtbase package
  - BUILD_TESTING=ON with ctest execution; the upstream DBus autotest is
    commented out upstream (knotification_test.cpp needs a session bus, not
    available in the headless CI) and tests/ is HAVE_DBUS-guarded, so the
    upstream CTest count is 0 in this feature set
  - USE_DBUS=OFF: Qt6DBus is not published to ohpcd; the DBus+Canberra block
    is additionally disabled via patch 0001 (Canberra/libcanberra not in the
    ohpcd registry). Audio notifications (notifybyaudio.cpp) and the DBus
    popup/portal backends are therefore not compiled.
  - KF_DEP_VERSION lowered 6.28.0 -> 6.26.0 by patch 0001: the published KF6
    packages top out at the 6.26.0.x line (API/ABI compatible inside 6.x)
  - Python bindings disabled by patch 0001: Shiboken6/PySide6 are not
    published to ohpcd
  - ecm_install_po_files_as_qm and examples/ disabled by patch 0001: the
    former needs Qt6LinguistTools, the latter Qt6 Quick - neither is part of
    the qtbase package published to ohpcd
  - Dependencies: qtbase/6.11.1 (Qt6Gui), kconfig/6.26.0.1 (bare-DT_SONAME
    republish of the 6.26.0 line)
  - ECM 6.28's KDEInstallDirs6 runs qtpaths at configure time; /system/lib64
    is prepended to LD_LIBRARY_PATH so the compatible libc++_shared.so is
    found (kconfig 6.26.0 / bluez-qt 6.28.0 precedent)
  - HMDFS-symlink-safe SONAME handling, see
    _configure_ohos_shared_library_rules (kitemviews 6.28.0 precedent)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase and the KF6
    packages use cmake_find_mode=none, which prevents CMakeDeps from adding
    their lib/cmake dirs to CMAKE_PREFIX_PATH
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    save,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KnotificationsConan(ConanFile):
    name = "knotifications"
    version = "6.28.0"
    description = "KDE Frameworks 6 - KDE Notifications"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/knotifications"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.28.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt6DBus is not published to ohpcd; disable DBus.
        tc.variables["USE_DBUS"] = "OFF"
        # Qt Designer plugin requires Qt6UiPlugin, which is not published to
        # ohpcd (qtbase does not ship it). Disable it explicitly even though
        # CMAKE_CROSSCOMPILING should default it to OFF.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
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
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(KF6Config)
            # and transitive find_dependency() chains all resolve.
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

    def _configure_ohos_shared_library_rules(self, toolchain):
        """OHOS CMake ships no Platform/HarmonyOS module, so
        CMAKE_SHARED_LIBRARY_SONAME_* stays unset and lld emits no DT_SONAME.
        Consumers then record the absolute build-machine path of this library
        in DT_NEEDED and fail to load it on CI workers or any clean cache.
        Restore the soname flags through the user make-rules override
        (kirigami 6.18.0 precedent). HMDFS additionally rejects symlink(2)
        with EPERM, so the versioned-symlink chain CMake creates for a
        versioned library (libKF6Notifications.so.6 -> .so.6.28.0) can never
        be materialized; NO_VERSIONED_SONAME keeps the (unversioned)
        DT_SONAME and drops the chain (KF5/expat-validated pattern).

        The CMAKE_SHARED_LIBRARY_RUNTIME_* (rpath) flags are deliberately not
        defined here. With them defined, CMake bakes the build-tree library
        directories into a RUNPATH, and cmake install() then rewrites the ELF
        in place to strip it; this device's loader rejects the rewritten
        library on dlopen (EACCES while the untouched linker output loads).
        Without the flags CMake emits no RUNPATH at all and install() is a
        pure copy, which is what the 6.26.0 line (SONAME-only recipe) shipped
        and what packaged consumers load."""
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
            )) + "\n",
        )
        toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM 6.28 KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 (and the qtbase lib dir, already added
            # by _library_runtime_env) so the loader resolves the compatible
            # libc++ first (kconfig 6.26.0 / bluez-qt 6.28.0 precedent).
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
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so test
            # executables resolve the compatible libc++ first (kconfig 6.26.0
            # / bluez-qt 6.28.0 precedent, same fix as _cmake_build_env).
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
        test_env.define("XDG_DATA_HOME",
                        os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            # Upstream CTest add_test count is 0 in this feature set (the
            # autotest is commented out upstream, tests/ is HAVE_DBUS-guarded)
            # -- measured with `ctest -N`. --no-tests=ignore keeps the run
            # green so `conan create` verifies the build; the upstream N=0 is
            # declared in test_package/MANIFEST.yml.
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=ignore'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6NotificationsConfig.cmake with
        # proper dependency tracking (find_dependency on Qt6Gui). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Notifications"]
