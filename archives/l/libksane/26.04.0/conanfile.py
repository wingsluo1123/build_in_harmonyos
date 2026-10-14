#!/usr/bin/env python3
"""Conan recipe for libksane 26.04.0 on HarmonyOS PC.

libksane is the KDE scanner widget library (libKSaneWidgets6.so), the GUI layer
on top of ksanecore (KSaneCore6).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation
  - KF6 6.18.0 line for the widget frameworks, matching the published
    ktextwidgets/6.18.0 and kwallet/6.18.0 artifacts. ksanecore's ki18n/6.26.0
    requirement is overridden down to ki18n/6.18.0 to keep the graph
    single-version; ksanecore is therefore rebuilt from source by
    --build=missing (the container line has to stay consistent one way or the
    other, since ktextwidgets is only published on the 6.18 track).
  - E537 relocatable linkage: the published KF6 dependencies carry no
    DT_SONAME, so the two patches stamp IMPORTED_SONAME on the imported targets
    and link them by basename through KSANE_DEP_LIB_DIRS; otherwise ld would
    record the machine-private package path in DT_NEEDED.
  - BUILD_TESTING=ON and ctest execution; the upstream autotests only define a
    ksane_tests() macro without registering any test (and the optional
    COMPILE_VIEWER_TESTAPP target links a non-existent `KSaneWidget` target), so
    the upstream CTest suite has zero registered entries and the conan
    test_package carries the functional assertions (construct KSaneWidget
    offscreen and exercise its no-device public API).
  - Dependencies: qtbase/6.11.1 (Qt6 Core/Gui/Widgets), ki18n/6.18.0,
    kwidgetsaddons/6.18.0, ktextwidgets/6.18.0, kwallet/6.18.0 (optional
    KF6Wallet), ksanecore/26.04.0, ecm/6.26.0 (build-time ECM)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because the dependencies use
    cmake_find_mode=none, which prevents CMakeDeps from adding their lib/cmake
    builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibksaneConan(ConanFile):
    name = "libksane"
    version = "26.04.0"
    description = "KDE scanner widget library (KSaneWidgets6)"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/graphics/libksane"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # KF6 6.18.0 line: ktextwidgets/kwallet are only published on the 6.18
        # track, so the whole widget framework stack is pinned there. The
        # overrides force the lower line on ksanecore (ki18n) and on
        # ktextwidgets' transitive kwidgetsaddons requirement.
        self.requires("ki18n/6.18.0", override=True)
        self.requires("kwidgetsaddons/6.18.0", override=True)
        self.requires("ktextwidgets/6.18.0")
        self.requires("kwallet/6.18.0")
        self.requires("ksanecore/26.04.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # CMake has no Platform/HarmonyOS module; provide the SONAME flag so
        # libKSaneWidgets6.so gets a DT_SONAME + versioned symlink chain
        # (ksanecore 26.04.0 precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # E537 relocatable linkage: expose the KF6 dependency lib dirs to the
        # patched src/CMakeLists.txt (target_link_directories) so the KF6
        # libraries are linked by basename (-lKF6I18n ...) and the produced
        # artifact stays relocatable (ksanecore 26.04.0 precedent).
        kf6_dep_lib_dirs = []
        for dep_name in ("ki18n", "kwidgetsaddons", "ktextwidgets", "kwallet"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                kf6_dep_lib_dirs.append(os.path.join(dep.package_folder, "lib"))
        if kf6_dep_lib_dirs:
            tc.variables["KSANE_DEP_LIB_DIRS"] = ";".join(kf6_dep_lib_dirs)

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
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(KF6*) /
            # find_package(KSaneCore6) and their transitive find_dependency()
            # chains all resolve.
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

    def build(self):
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
            # ECM KDEInstallDirs runs the qtbase qtpaths host tool during
            # configure; the sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one; prepend
            # /system/lib64 so the loader resolves the compatible libc++
            # first (ksanecore 26.04.0 / kio 6.26.0 precedent).
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
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
        runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(self.build_folder, "bin"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        # Same /system/lib64 libc++ shadowing fix as _cmake_build_env
        # (ksanecore 26.04.0 / kio 6.26.0 precedent).
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
            self.run(
                'ctest --test-dir "{}" --output-on-failure'.format(
                    self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KSaneWidgets6Config.cmake with proper
        # dependency tracking (find_dependency on Qt6Widgets). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KSaneWidgets6"]
