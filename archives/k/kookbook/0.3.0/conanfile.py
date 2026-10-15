#!/usr/bin/env python3
"""Conan recipe for kookbook 0.3.0 (CMake + Qt6 + KDE ECM) on HarmonyOS PC (aarch64).

KookBook (Sune Vuorela, MIT) is a recipe manager for semi-structured
markdown recipes (``*.recipe.md``). One upstream tree delivers two
front-ends:

  - bin/kookbook       desktop Qt6 Widgets application
  - bin/kookbooktouch  Qt6 Qml/Quick touch application
  plus .desktop/appdata metadata, hicolor icons and the krecipes.py
  converter data file.

Upstream hard requirements (top-level CMakeLists.txt): CMake >= 3.16,
C++17, ECM >= 6.0.0 (find_package(ECM) + KDEInstallDirs, KDECMakeSettings,
KDECompilerSettings, ECMAddTests, ECMAddAppIcon, ECMInstallIcons) and
Qt6 >= 6.4.0 with COMPONENTS Widgets PrintSupport Qml.

OHOS adaptation — the published dependency topology drives every choice
(full evidence in notes.md):

  - qtbase/6.11.1 is pinned because it is the line every published Qt6
    module in the registry is built against. The published Qt6 base that
    carries Qt6::PrintSupport is qtbase/6.11.1.3, but no published
    qtdeclarative can coexist with it: qtdeclarative/6.11.1 and
    /6.11.1.1 declare ``qtbase/6.11.1`` exactly (conan version conflict),
    and qtdeclarative/6.11.1.2 (built on 6.11.1.3) resolves
    qtshadertools/6.11.1 to a package id that is not published.
  - KookBook needs both Qt6::Qml (kookbooktouch, required by the
    top-level find_package) and Qt6::PrintSupport. Only one can be
    satisfied today, so the Qt6::Qml front-end is kept and the print path
    is dropped (patches/0001-0005) — the same trade-off the published
    kgraphviewer 26.04.0 / kdiagram 3.0.1 / kapow 1.7.0 recipes make, since
    the qtbase/6.11.1 package ships neither libQt6PrintSupport.so nor
    Qt6PrintSupportConfig.cmake. Dropped: the two "Print current recipe" /
    "Print preview current recipe" toolbar actions and
    MainPane::print()/printPreview(). Everything else — collection scan,
    RecipeParser/IngredientsExtractor, markdown rendering, metadata/tags/
    ingredients panes, both front-ends — is upstream code, untouched.
  - The recipe does NOT trim Qt6::Test: the qtbase/6.11.1 package does ship
    libQt6Test.so and Qt6TestConfig.cmake (it simply declares no conan
    "test" component), so the upstream autotests suite can be built and
    run. BUILD_TESTING=ON and ctest runs inside build().
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class KookbookConan(ConanFile):
    name = "kookbook"
    version = "0.3.0"
    description = "KookBook 0.3.0 recipe manager for markdown recipes (Qt6, OHOS PC)"
    license = "MIT"
    homepage = "https://invent.kde.org/utilities/kookbook"
    url = "https://invent.kde.org/utilities/kookbook"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 base: Core / Gui / Widgets / Test (Test cmake config ships in
        # the package). This line has FEATURE_printsupport=OFF.
        self.requires("qtbase/6.11.1")
        # Qt6 Qml (Qt6QmlConfig.cmake) backing the kookbooktouch front-end,
        # required by the top-level find_package(Qt6 ... COMPONENTS Qml).
        self.requires("qtdeclarative/6.11.1")

    def build_requirements(self):
        # Upstream: find_package(ECM 6.0.0) then include(KDEInstallDirs),
        # KDECMakeSettings, KDECompilerSettings, ECMAddTests ...
        self.tool_requires("extra-cmake-modules/6.29.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream autotests/parsertest (2 QtTest targets registered through
        # ecm_add_test); ECMAddTests gates registration on BUILD_TESTING.
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"

        # Relocatable runtime lookup for the packaged applications: the
        # executables live in bin/, the Qt6 libraries in every dependency's
        # lib/. Upstream installs no private shared library, so no SONAME
        # flag override is needed (E537 does not apply here).
        rpath_dirs = ["$ORIGIN/../lib"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    rpath_dirs.append(lib_dir)
        tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(rpath_dirs)
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(rpath_dirs)

        # ECM's own installed ECMConfig.cmake exports ECM_MODULE_PATH, but it
        # is only reachable once find_package(ECM) has succeeded. Point the
        # module path at the tool_require directly so KDEInstallDirs,
        # KDECMakeSettings, KDECompilerSettings, ECMAddTests, ECMAddAppIcon
        # and ECMInstallIcons resolve (accessibility 26.04.3 precedent).
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # ECM's ECMQueryQt.cmake resolves TARGET Qt6::qtpaths through
        # Qt6CoreTools, which Qt6Config.cmake does not load in this qtbase
        # layout. Point QUERY_EXECUTABLE at qtpaths6 so KDEInstallDirs
        # resolves the install dirs (accessibility / mobipocket precedent).
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            if os.path.exists(qtpaths6):
                tc.variables["QUERY_EXECUTABLE"] = qtpaths6
                tc.variables["_cli_option"] = "--query"

        # Qt6Config.cmake resolves components (Qml -> qtdeclarative) relative
        # to QT_ADDITIONAL_PACKAGES_PREFIX_PATH.
        qt_extra = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                qt_cmake_dir = os.path.join(dep.package_folder, "lib", "cmake")
                if os.path.isdir(qt_cmake_dir) and any(
                        n.startswith("Qt6") for n in os.listdir(qt_cmake_dir)
                ):
                    qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = (
                ";".join(qt_extra)
            )

        tc.generate()

        # qtbase uses cmake_find_mode=none, so CMakeDeps does not emit
        # conan_cmakedeps_paths.cmake for it. Write the file with every
        # dependency's cmake/lib/include dirs plus ECM's module dirs
        # (accessibility 26.04.3 precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")'
                )
        if ecm:
            ecm_pkg = ecm.package_folder
            for sub in ("cmake", "find-modules", "modules", "kde-modules"):
                lines.append(
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_pkg}/share/ECM/{sub}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_pkg}/share/ECM/{sub}")'
                )
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        # Build-time helper tools (moc, rcc via Qt6::*Tools, ECM scripts) are
        # executed during build(); expose every dependency's lib dir or they
        # cannot load libQt6Core.so.6 (accessibility / calligra precedent).
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    self.buildenv.append_path("LD_LIBRARY_PATH", lib_dir)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the complete upstream autotests suite (ctest, must pass).

        Upstream registers both autotests/parsertest targets through
        ecm_add_test: ingredientsextractortest (16 data rows x 3 QCOMPARE)
        and recipeparsertest (9 data rows). Both use QTEST_APPLESS_MAIN, so
        no QApplication/display is needed; the offscreen QPA is still set
        defensively for any Qt platform initialization on the target.
        """
        test_env = Environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("TZ", "Asia/Shanghai")
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
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    test_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                plugins_dir = os.path.join(dep.package_folder, "plugins")
                if os.path.isdir(plugins_dir):
                    test_env.prepend_path("QT_PLUGIN_PATH", plugins_dir)
        with test_env.vars(self).apply():
            # No ignore_errors: the upstream suite must be green for the
            # package to be built. --no-tests=error prevents an empty
            # registration from being reported as success (R51).
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                ),
                env="conanrun",
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Application package: bin/kookbook and bin/kookbooktouch plus the
        # desktop/appdata metadata, hicolor icons and the krecipes.py
        # converter data under share/. No library is delivered, so declaring
        # cpp_info.libs would make CMakeDeps emit targets for missing files.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]
