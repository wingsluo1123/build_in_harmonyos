#!/usr/bin/env python3
"""Conan recipe for kbookmarks 6.28.0 on HarmonyOS PC.

kbookmarks is a KDE Frameworks 6 library for managing bookmarks and bookmark
widgets (libKF6Bookmarks.so and libKF6BookmarksWidgets.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: ECMPoQmTools' ecm_process_po_files_as_qm()
    returns early when this option is set (verified in the ECM 6.26/6.28
    sources on the device), so translation catalog generation is skipped
    without a source patch and without requiring Qt6LinguistTools (not
    published to ohpcd)
  - KF_DEP_VERSION lowered 6.28.0 -> 6.26.0 (patches/0001): ohpcd publishes
    KF6Config/KF6CoreAddons only up to 6.26.0.1 while KF6WidgetsAddons is at
    6.28.0; 6.26.0 is the common floor that satisfies all three
    find_package() calls (kcontacts 6.28.0 precedent)
  - BUILD_TESTING=ON and ctest execution for the upstream autotest
  - Dependencies: qtbase/6.11.1, kconfig/6.26.0.1, kcoreaddons/6.26.0.1,
    kwidgetsaddons/6.28.0, ecm/6.28.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase and the three
    KF6 packages use cmake_find_mode=none, which prevents CMakeDeps from
    adding their lib/cmake builddirs to CMAKE_PREFIX_PATH
  - Shared libraries are emitted unversioned (CMAKE_PLATFORM_NO_VERSIONED_SONAME
    plus explicit -soname flags, both in plain and cache variables): HMDFS
    rejects symlink() with EPERM, so CMake's versioned .so chain cannot be
    created on device (kwidgetsaddons 6.28.0 / kitemviews 6.28.0 precedent)
  - ECM 6.28 KDEInstallDirs6 runs the qtbase qtpaths host tool during
    configure (ecm_query_qt -> QT_INSTALL_PREFIX); /system/lib64 and the SDK
    llvm lib dir are prepended to LD_LIBRARY_PATH so the compatible
    libc++_shared.so wins over the sandbox one (kwidgetsaddons 6.28.0
    precedent)
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KbookmarksConan(ConanFile):
    name = "kbookmarks"
    version = "6.28.0"
    description = "KDE Frameworks 6 - Bookmark management"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kbookmarks"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # Highest versions published to ohpcd (device registry probe,
        # 2026-10-17): kconfig/kcoreaddons top out at 6.26.0.1 (packaged as
        # 6.26.0), kwidgetsaddons is at 6.28.0. patches/0001 lowers the
        # upstream KF_DEP_VERSION to the 6.26.0 common floor.
        self.requires("kconfig/6.26.0.1")
        self.requires("kcoreaddons/6.26.0.1")
        self.requires("kwidgetsaddons/6.28.0")

    def build_requirements(self):
        # kbookmarks 6.28.0 requires ECM >= 6.28.0 (find_package(ECM 6.28.0
        # NO_MODULE) in the top-level CMakeLists.txt); ohpcd publishes
        # ecm/6.28.0 since 2026-10-14.
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
        # ECMPoQmTools' ecm_process_po_files_as_qm() returns early when this
        # option is set, so po/qm catalog generation is skipped without
        # needing Qt6LinguistTools (not published to ohpcd).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # HMDFS (the device user volume) rejects symlink() with EPERM, so the
        # versioned lib<name>.so.<major> symlink chain CMake creates after
        # linking fails the build on device. Emit every shared library under
        # its plain name instead (DRAFT-cmake-harmonyos-system-name-soname;
        # kcolorpicker/expat precedent).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        # CMake ships no Platform/HarmonyOS module, so CMAKE_SHARED_LIBRARY_SONAME_*
        # stays empty and lld emits no DT_SONAME. Consumers then record the absolute
        # build-machine path of this library in DT_NEEDED and fail to load it on CI
        # workers or any clean cache. Provide the flags so each library gets a
        # DT_SONAME and consumers record the bare soname instead. Set both variable
        # flavors: cache_variables reaches the configure only through CMakePresets
        # while plain variables reach -DCMAKE_TOOLCHAIN_FILE configures.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

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
            # qtbase and the KF6 packages use cmake_find_mode=none -> CMakeDeps
            # does not generate conan_cmakedeps_paths.cmake. Create it manually
            # so the toolchain adds their cmake dirs to CMAKE_PREFIX_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            for dep_name in ("kconfig", "kcoreaddons", "kwidgetsaddons"):
                dep = self.dependencies.get(dep_name)
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
            # ECM 6.28 KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 (and the qtbase lib dir, already added
            # by _library_runtime_env) so the loader resolves the compatible
            # libc++ first (kconfig 6.26.0 / kwidgetsaddons 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
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
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 60'.format(self.build_folder)
            )

    def _prepare_ctest_runtime_links(self):
        # The autotest executable records bare sonames (libKF6Bookmarks.so,
        # ...); mirror the build-tree and dependency libraries into build/../bin
        # as a loader fallback when the sandbox build folder sits on a volume
        # that cannot follow the build-tree layout (6.18.0 precedent).
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
        # The project installs its own KF6BookmarksConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Widgets/Qt6Xml and
        # KF6WidgetsAddons). Use cmake_find_mode=none so CMakeDeps doesn't
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Bookmarks", "KF6BookmarksWidgets"]
