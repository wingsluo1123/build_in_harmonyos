#!/usr/bin/env python3
"""Conan recipe for kholidays 6.18.0 on HarmonyOS PC.

kholidays is a KDE Frameworks 6 library (libKF6Holidays.so) that computes
holiday calendars (holiday region data + a plan-language parser) and
astronomical events: sunrise/sunset (SunRiseSet), solar events around the
closest solar noon (SunEvents, used by Plasma knighttime for the dark/light
schedule), lunar phases, zodiac signs and astro seasons.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list), same as kconfig/kxmlgui/ki18n 6.18.0
  - BUILD_TESTING=ON and ctest execution for the 6 upstream autotests
    (testlunar, testseasons, testsunriseset, testzodiac, testholidayregion,
    testsunevents)
  - No bison/flex tool_requires: unlike 6.28.0, the 6.18.0 release tarball
    ships the generated parser translation units
    (src/parsers/plan2/holidayparserplan.cpp + holidayscannerplan.cpp) and
    src/CMakeLists.txt compiles them directly, so no lexer/parser generator
    runs during the build
  - C++20: src/lunarphase.cpp uses std::numbers::pi (<numbers>, C++20) while
    the repository profile pins compiler.cppstd=17. The conan cppstd block is
    removed and CMAKE_CXX_STANDARD=20 is set, as for 6.28.0. This needs no
    source patch, because 6.18.0 does not use the C++20 ranges algorithm
    overloads that the OHOS SDK libc++ (clang 15) lacks
    (std::ranges::none_of is missing there, which is what 6.28.0 patches)
  - Dependencies: qtbase/6.11.1 (Qt6::Core, also Qt6::Test for the upstream
    autotests), qtdeclarative/6.11.1 (Qt6::Qml for the org.kde.kholidays QML
    plugin) and qt6linguisttools/6.11.1 (Qt6LinguistTools, needed by
    ecm_install_po_files_as_qm(poqm))
  - Build requirement: ecm/6.26.0. Upstream asks for ECM >= 6.18.0; the
    published ECM line on ohpcd starts at 6.20.0, so the KF6 6.18.0 baseline
    value (ecm/6.26.0, used by kconfig/kcoreaddons/ki18n/kxmlgui/kwidgetsaddons
    6.18.0) is reused
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KholidaysConan(ConanFile):
    name = "kholidays"
    version = "6.18.0"
    description = "KDE Frameworks 6 - Holiday calendars and astronomical events (sunrise/sunset, lunar phases, zodiac)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kholidays"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Core is the public link dependency of KF6Holidays; the same
        # package also provides Qt6::Test, used by the upstream autotests.
        self.requires("qtbase/6.11.1")
        # The org.kde.kholidays QML plugin links Qt6::Qml, provided by the
        # published qtdeclarative package.
        self.requires("qtdeclarative/6.11.1")

    def build_requirements(self):
        # ECM >= 6.18.0 is required upstream (find_package(ECM 6.18.0 NO_MODULE)).
        self.tool_requires("ecm/6.26.0")
        # Qt6LinguistTools (lrelease + Qt6::LinguistTools CMake module) is
        # required by ECMPoQmTools for ecm_install_po_files_as_qm(poqm).
        self.tool_requires("qt6linguisttools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The upstream sources use the C++20 <numbers> header (std::numbers::pi
        # in src/lunarphase.cpp) while the repository profile pins cppstd=17.
        # Remove the conan cppstd block so CMAKE_CXX_STANDARD=20 is honored
        # (kholidays 6.28.0 / baloo 6.28.0 precedent).
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so the
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ECMQmlModule,
        # ECMPoQmTools, ECMGenerateQDoc, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none, so CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if qtdeclarative:
                qml_pkg = qtdeclarative.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qml_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qml_pkg}/lib")')
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
                # ECMPoQmTools calls find_package(Qt6 COMPONENTS LinguistTools)
                # which resolves through qtbase's Qt6Config.cmake: register the
                # split Qt package roots as additional Qt prefixes so the Qml
                # and LinguistTools components are found.
                qml_prefixes = [qtdeclarative.package_folder] if qtdeclarative else []
                qt_prefixes = qml_prefixes + [ltt_pkg]
                tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                    qt_prefixes
                )
                lines.append(
                    'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH '
                    f'"{";".join(qt_prefixes)}" CACHE STRING '
                    '"Additional directories where find(Qt6 ...) components '
                    'are searched" FORCE)'
                )
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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # ECM KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 so the loader resolves the compatible
            # libc++ first (bluez-qt 6.28.0 / kconfig 6.18.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("TZ", "UTC")
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
            # Run the upstream ctest suite: 6 autotests are registered by
            # autotests/CMakeLists.txt (testlunar, testseasons,
            # testsunriseset, testzodiac, testholidayregion, testsunevents).
            # They are plain computation tests over the bundled holiday data
            # and astronomy code and need no display.
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error --timeout 300'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6HolidaysConfig.cmake with proper
        # dependency tracking (find_dependency(Qt6Core)). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Holidays"]
        self.cpp_info.resdirs = ["share"]
