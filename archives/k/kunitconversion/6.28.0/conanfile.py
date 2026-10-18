#!/usr/bin/env python3
"""Conan recipe for kunitconversion 6.28.0 on HarmonyOS PC.

KUnitConversion is the KDE Frameworks 6 unit-conversion library
(libKF6UnitConversion.so): the Converter / Value / Unit / UnitCategory API
over the compiled unit tables (Length, Area, Volume, Temperature, Velocity,
Mass, Pressure, Energy, Currency, Power, Time, FuelEfficiency, Density,
WeightPerArea, Acceleration, Angle, Frequency, Force, ThermalConductivity,
ThermalFlux, ThermalGeneration, Voltage, ElectricalCurrent,
ElectricalResistance, Permeability, BinaryData) plus the downloadable ECB
exchange-rate table.

OHOS-specific adaptations (techniques proven by kcontacts 6.28.0 and the
j669539 kunitconversion5 5.116.0 port, PR !14840):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list).
  - KF_DEP_VERSION 6.28.0 -> 6.26.0 (patches/0001, "# ohpcd KF6 dep
    ceiling"): find_package(KF6I18n 6.28.0 ...) would otherwise reject the
    ki18n package published to ohpcd (6.26.0 is the highest registered
    version; KF6 frameworks keep API/ABI compatibility inside the 6.x
    major, kcontacts 6.28.0 precedent).
  - KF_SKIP_PO_PROCESSING=ON: the top-level ki18n_install(po) resolves
    against the ki18n package's KF6I18nMacros.cmake (loaded through
    KF6I18nConfig.cmake), whose KI18N_INSTALL() early-returns under this
    option, so no msgfmt / Qt6 LinguistTools is needed at configure time.
    The published ki18n/6.26.0 already ships the relaxed Gettext lookup
    (its own patch 0001), so the po layer needs no patch here
    (ki18n 6.28.0 precedent).
  - BUILD_PYTHON_BINDINGS=OFF: the upstream guard (ANDROID OR APPLE OR
    WIN32 OR HAIKU OR NOT BUILD_SHARED_LIBS) does not cover OHOS, and the
    bindings would require Shiboken6/PySide6, which are not published.
  - ki18n 6.26.0's libKF6I18n.so is published without DT_SONAME, so
    linking the imported KF6::I18n target would record its absolute
    conan-cache path in DT_NEEDED (E537). patches/0002 drops the target
    from the KF6UnitConversion link list and links the library by bare
    name (-L<package lib dir> -lKF6I18n) while keeping its include
    directories; the linker records a relocatable DT_NEEDED basename
    (kcontacts 6.28.0 precedent).
  - CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname, plus
    CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON: CMake has no Platform/HarmonyOS
    module, so the SONAME flags stay unset and libKF6UnitConversion.so
    would be linked without DT_SONAME. The target sets VERSION/SOVERSION
    (upstream SOVERSION 6), whose .so.6/.so.6.28.0 symlink chain cannot be
    created on the HMDFS user volume (symlink() -> EPERM), so the versioned
    names are disabled at the same time. One unversioned real
    libKF6UnitConversion.so keeps a bare, relocatable SONAME for downstream
    DT_NEEDED (E330; kpeople 6.28.0 / kcontacts 6.28.0 precedents).
  - extra-cmake-modules/6.28.0 tool_requires satisfies the project's
    find_package(ECM 6.28.0 NO_MODULE).
  - ECM_MODULE_PATH set manually: the project's CMakeLists.txt does
    set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH}) and the CMakeDeps-shaped
    ECMConfig does not propagate the variable (kcontacts 6.28.0 precedent).
  - conan_cmakedeps_paths.cmake created manually because qtbase, the KF6
    packages and this package use cmake_find_mode=none, which prevents
    CMakeDeps from adding their lib/cmake builddir to CMAKE_PREFIX_PATH.
  - CMAKE_CXX_STANDARD=20 + CMAKE_CXX_FLAGS=-std=c++20: the CMakeDeps
    toolchain defaults to C++17 which is too old for current KF6 code
    (kcontacts 6.28.0 precedent).
  - BUILD_TESTING=ON: the upstream autotests are compiled in build() and
    the 4-entry CTest suite runs with a staged runtime env:
      * LD_LIBRARY_PATH / QT_PLUGIN_PATH, QT_QPA_PLATFORM=offscreen
      * HOME/XDG_* redirected into the build folder (kcontacts 6.28.0
        precedent)
      * the QStandardPaths test-mode data dir
        ($HOME/.qttest/share/libkunitconversion/) is pre-created because
        currencytableinittest copies its embedded currency.xml snapshot
        there and QFile::copy does not create parent directories - with
        that table the test parses the snapshot offline (j669539
        kunitconversion5 !14840 precedent).
  - patches/0003 QSKIP-guards the two ECB exchange-rate download test
    functions (convertertest::testCurrency, categorytest::testCurrencyTableUpdate):
    the download needs an outbound HTTPS route and the OHOS CI sandbox has
    none, so those environment-bound cases are skipped in place (the
    assertions stay in the tree) while the conversion logic keeps running;
    the offline currency paths remain fully covered
    (valuetest::testCurrencyNotDownloaded, currencytableinittest).
    Precedent: j669539 kunitconversion5 5.116.0 (!14840), knowledge
    entry E731 (QSKIP network boundary guard).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KUnitConversionConan(ConanFile):
    name = "kunitconversion"
    version = "6.28.0"
    description = "KDE Frameworks 6 - Unit conversion library (Converter/Value/Unit tables)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kunitconversion"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # KF6 framework published to ohpcd, pinned to the highest registered
        # version (I18n tops out at 6.26.0). patches/0001 lowers the
        # upstream KF_DEP_VERSION ceiling to 6.26.0 to match.
        self.requires("ki18n/6.26.0")

    def build_requirements(self):
        # find_package(ECM 6.28.0 NO_MODULE): the extra-cmake-modules
        # package ships the 6.28.0 config (kcontacts 6.28.0 precedent; the
        # legacy "ecm" package stops at 6.26.0).
        self.tool_requires("extra-cmake-modules/6.28.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Enable the full upstream autotests (4 registered CTest entries).
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # ki18n_install(po) early-returns inside KI18N_INSTALL() when this
        # option is set, so no msgfmt/Qt6 LinguistTools is required
        # (ki18n 6.28.0 precedent; ki18n 6.26.0 already ships the relaxed
        # Gettext lookup).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # The upstream guard (ANDROID OR APPLE OR WIN32 OR HAIKU OR NOT
        # BUILD_SHARED_LIBS) does not cover OHOS; Shiboken6/PySide6 are not
        # published to ohpcd.
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"
        # Current KF6 sources require C++20; force it explicitly because
        # the CMakeDeps toolchain defaults to C++17 (kcontacts 6.28.0
        # precedent).
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        # CMake has no Platform/HarmonyOS module (the OHOS profile maps to
        # CMAKE_SYSTEM_NAME=HarmonyOS), so the SONAME flags stay unset and
        # libKF6UnitConversion.so would be linked without DT_SONAME.
        # Restore the flags so the library carries a real soname.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Disable the versioned .so.6/.so.6.28.0 names: the HMDFS user
        # volume rejects symlink() with EPERM, so CMake's
        # cmake_symlink_library post-link step would fail the build. The
        # unversioned real libKF6UnitConversion.so keeps a bare soname, so
        # downstream DT_NEEDED stays relocatable (E330; kpeople 6.28.0 /
        # kcontacts 6.28.0 precedents). Set through both channels: the
        # plain variable reaches conan_toolchain.cmake, the cache entry
        # covers configurations driven through CMakePresets.json.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not. The project's CMakeLists.txt
        # replaces CMAKE_MODULE_PATH with ECM_MODULE_PATH, so set the
        # variable directly (kcontacts 6.28.0 precedent).
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
            # qtbase and the KF6 packages use cmake_find_mode=none -> CMakeDeps
            # does not generate conan_cmakedeps_paths.cmake. Create it
            # manually so the toolchain adds their cmake dirs to
            # CMAKE_PREFIX_PATH (find_package(Qt6 ...) and the ECM FindKF6
            # module both resolve in CONFIG mode through these entries).
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Every dependency's lib/cmake dir: the KF6 component configs
            # (KF6I18nConfig.cmake etc.) live there and are located by the
            # ECM FindKF6 module, and KF6UnitConversionConfig.cmake does
            # find_dependency(Qt6Core).
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
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        build_env = Environment()
        if self.settings.os == "OHOS":
            # ECM runs the qtbase qtpaths host tool during configure
            # (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so
            # which shadows the compatible one; prepend /system/lib64
            # (kconfig 6.26.0 / kcontacts 6.28.0 precedent) and the SDK
            # llvm/lib directory (lld needs libxml2.so.16 from there on
            # hosts that do not export it; kcalendarcore E132 observation).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with build_env.vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _library_runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        if self.settings.os == "OHOS":
            # Same sandbox libc++ shadowing fix as the build env.
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        for llvm_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
            test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        # Isolated HOME/XDG dirs (kcontacts 6.28.0 precedent): the
        # QStandardPaths test mode used by the currency tests pins
        # GenericDataLocation to <HOME>/.qttest/share.
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
        # QStandardPaths::setTestModeEnabled(true) pins GenericDataLocation
        # to <HOME>/.qttest/share; currencytableinittest copies its embedded
        # ../currency.xml snapshot to <that>/libkunitconversion/currency.xml
        # and QFile::copy does not create parent directories, so pre-create
        # the cache directory and the test parses the snapshot offline
        # (j669539 kunitconversion5 !14840 precedent).
        os.makedirs(
            os.path.join(test_home, ".qttest", "share", "libkunitconversion"),
            exist_ok=True,
        )
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -j1'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        # CTest entries registered by autotests/CMakeLists.txt run with CWD
        # <build>/autotests, so a DT_NEEDED recorded as a build-tree
        # relative path ('../../bin/libKF6I18n.so') resolves against the
        # working directory. Names containing '/' bypass LD_LIBRARY_PATH,
        # so every non-Qt dependency library plus the build outputs are
        # materialized in both compatibility layouts (kcontacts 6.28.0 /
        # kpeople 6.28.0 precedent). Qt is left alone: its libraries carry
        # proper sonames and are found through the LD_LIBRARY_PATH entries.
        # HMDFS rejects symlink() with EPERM, so fall back to a plain copy
        # (qzxing precedent).
        compatibility_bins = [
            os.path.join(self.build_folder, "bin"),
            os.path.normpath(os.path.join(self.build_folder, os.pardir, "bin")),
        ]
        lib_sources = glob.glob(
            os.path.join(self.build_folder, "bin", "lib*.so*")
        )
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            if dep.ref.name == "qtbase":
                continue
            lib_sources.extend(
                glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
            )
        for src in lib_sources:
            for compatibility_bin in compatibility_bins:
                os.makedirs(compatibility_bin, exist_ok=True)
                dst = os.path.join(compatibility_bin, os.path.basename(src))
                if not os.path.exists(src):
                    continue
                target = os.path.realpath(src)
                if os.path.realpath(dst) == target:
                    continue
                if os.path.lexists(dst):
                    os.unlink(dst)
                try:
                    os.symlink(target, dst)
                except OSError:
                    shutil.copy2(target, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6UnitConversionConfig.cmake with
        # proper dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6UnitConversion"]
