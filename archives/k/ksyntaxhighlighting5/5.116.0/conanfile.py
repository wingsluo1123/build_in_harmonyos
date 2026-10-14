#!/usr/bin/env python3
"""Conan recipe for ksyntaxhighlighting5 5.116.0 on HarmonyOS PC.

syntax-highlighting (KF5/Qt5) is the KDE Frameworks 5 syntax-highlighting
engine (libKF5SyntaxHighlighting.so), providing the reusable SyntaxHighlighting
framework (definitions, themes, highlighter, folding) that KTextEditor and
Kate consume. The KF5 branch targets Qt5.

OHOS-specific adaptations (modeled on kcodecs5/5.116.0, same KF5/Qt5
baseline; the KF5 5.116.0 chain was established by kcoreaddons5/kconfig5/
kwidgetsaddons5 precedents):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list).
  - CMAKE_SYSTEM_NAME=Linux: CMake 4.1 has no Platform/HarmonyOS module, so
    the `UNIX` variable is not set and KDE's KDECMakeSettings / install-dir
    logic behaves as a non-UNIX platform. OHOS is a POSIX system, so forcing
    the Linux platform is fully compatible (R32-safe: no __OHOS__ macros
    anywhere in this project).
  - KDE_INSTALL_USE_QT_SYS_PATHS=OFF: install into ksyntaxhighlighting5's own
    prefix, not Qt's.
  - ecm_install_po_files_as_qm(poqm) disabled via patches/0001 because
    Qt5LinguistTools is not published to ohpcd (kconfig5/kcodecs5 precedent).
  - find_package(Perl REQUIRED): the packaged OHOS Qt5 does not need Perl to
    build the QRC-bundled syntax data; Perl is only consulted to auto-generate
    the PHP syntax definition. The requirement is satisfied by the host Perl
    (/storage/Users/currentUser/usr/local/bin/perl), no change needed.
  - Qt5 component needs: Core + Network + Test (REQUIRED upstream) and Gui
    (when KSYNTAXHIGHLIGHTING_USE_GUI=ON, default). The packaged
    qt5-qtbase/5.15.2 ships the aggregate Qt5Config.cmake plus the per-module
    Qt5Core/Gui/Network/Test configs, so find_package(Qt5 COMPONENTS ...)
    resolves directly via the hand-written conan_cmakedeps_paths.cmake.
  - Dependencies: qt5-qtbase/5.15.2 (Qt5), ecm/6.20.0 (ECM) — this package
    is deliberately early in the KF5 chain: it depends only on Qt5 + ECM,
    no other KF5 component (kcodecs5 pattern).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project's CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
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


class Ksyntaxhighlighting5Conan(ConanFile):
    name = "ksyntaxhighlighting5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - Syntax highlighting engine (libKF5SyntaxHighlighting)"
    license = "MIT"  # syntax-highlighting is MIT-licensed
    homepage = "https://invent.kde.org/frameworks/syntax-highlighting"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        shared = bool(self.options.shared)
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        # SONAME emission on OHOS (E537 / CI L5 gate, kconfig5 precedent): the
        # OHOS (Generic) CMake platform defines no soname rule, so without
        # these flags libKF5SyntaxHighlighting.so ships without a DT_SONAME and
        # downstream consumers record the absolute conan-cache path in
        # DT_NEEDED.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # NOTE: do NOT force CMAKE_SYSTEM_NAME=Linux here. The host is
        # HarmonyOS (CMAKE_HOST_SYSTEM_NAME=HarmonyOS), so leaving the
        # toolchain's own mapping (os=OHOS → CMAKE_SYSTEM_NAME=HarmonyOS) in
        # place keeps CMAKE_CROSSCOMPILING=FALSE. syntax-highlighting's
        # src/indexer/CMakeLists.txt then builds katehighlightingindexer as a
        # native host tool; forcing Linux would flip CMAKE_CROSSCOMPILING=TRUE
        # and trigger its "Please provide ... KF5_HOST_TOOLING" fatal
        # (KF6 ksyntaxhighlighting 6.26.0 precedent).

        if str(self.settings.os) == "OHOS":
            targets = {
                "armv8": "aarch64-linux-ohos",
                "x86_64": "x86_64-linux-ohos",
            }
            target = targets.get(str(self.settings.arch))
            if target:
                tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
            qt_pkg = qtbase.package_folder.replace("\\", "/")
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder.replace("\\", "/")
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Qt5CoreConfigExtrasMkspecDir.cmake references
        # ${_qt5Core_install_prefix}/../b/mkspecs/linux-clang, which does not
        # exist in the qt5-qtbase conan package layout. Mirror the real
        # mkspecs dir to the expected location (kcodecs5 precedent).
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs"
        )
        if os.path.isdir(source) and not os.path.isdir(expected):
            parent, _ = os.path.split(expected)
            os.makedirs(parent, exist_ok=True)
            import shutil

            shutil.copytree(source, expected)

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        # The OHOS sandbox loader does not use LD_LIBRARY_PATH for user-path
        # binaries, but the indexer host tool (katehighlightingindexer) runs
        # during build via CMake custom commands and needs libQt5Core.so.5
        # resolvable. Provide the runtime env (dependency lib dirs + the real
        # system libc++) so configure/build can execute it (ktextwidgets5 /
        # kconfig5 precedent).
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Run the upstream autotests (rule4 / 1-b: BUILD_TESTING=ON compiles
        # them, they must actually execute). Modeled on kconfig5/5.116.0.
        if not can_run(self):
            self.output.info(
                "Skipping upstream CTest during cross-compilation; target execution is required on OHOS"
            )
            return
        test_env = self._cmake_build_env()
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
        # Qt5Gui offscreen tests need the platform plugin path; point it at
        # the qt5-qtbase package's plugins (same layout fix as generate()).
        for dep in self.dependencies.values():
            if dep and dep.package_folder and os.path.isdir(
                os.path.join(dep.package_folder, "plugins", "platforms")
            ):
                test_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        # The built KF5 lib has no DT_SONAME, so the test binaries record a
        # relative DT_NEEDED like "bin/libKF5SyntaxHighlighting.so"; the
        # build root (with the bin/ compat layout) must be on the lib path.
        test_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, os.pardir)
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _cmake_build_env(self):
        # Sandbox libc++_shared.so shadowing fix (kconfig5 precedent): the
        # SDK's aarch64-linux-ohos libc++.so is a linker script that shadows
        # the real system libc++_shared.so; prepend /system/lib64 and the SDK
        # llvm/lib dirs. Dependency libs (Qt5) are also prepended so the
        # build-time host tools (katehighlightingindexer) can execute under
        # make/ninja.
        env = Environment()
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
            )):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        for rel in ("bin", "lib"):
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5SyntaxHighlighting"]
        # KF5SyntaxHighlighting depends on Qt5Core; let the installed
        # KF5SyntaxHighlightingConfig.cmake drive the Qt5::Core find_dependency
        # automatically.
        self.cpp_info.requires = []
