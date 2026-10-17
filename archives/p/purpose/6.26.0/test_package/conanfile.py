#!/usr/bin/env python3
"""Conan test_package for purpose 6.26.0 (HarmonyOS PC).

HarmonyOS-only consumer test: instead of a link-only smoke test it drives the
real share/export pipeline an application (koko) uses - Purpose::
AlternativesModel -> Purpose::Configuration -> Purpose::Job -> saveasplugin -
and checks that the exported file is really written to disk (R34).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class PurposeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # Mirror the purpose 6.26.0 dependency matrix: KF6PurposeConfig.cmake
        # chains find_dependency() through the KF6 components purpose links
        # against, so every one of them has to be in the graph.
        self.requires("kio/6.26.0")
        self.requires("kservice/6.26.0")
        self.requires("kirigami/6.26.0")
        self.requires("knotifications/6.26.0")
        self.requires("kitemmodels/6.26.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("openssl/3.5.6.1")
        self.requires("zstd/1.5.7")
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        # Locate the Qt packages by content rather than by recipe name:
        # Qt6Config comes from the qtbase package and Qt6Qml from the
        # qtdeclarative one, and Qt can only find the extra modules through its
        # official QT_ADDITIONAL_PACKAGES_PREFIX_PATH hook.
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            qt6 = os.path.join(dep.package_folder, "lib", "cmake", "Qt6", "Qt6Config.cmake")
            if os.path.isfile(qt6):
                tc.variables["Qt6_DIR"] = os.path.dirname(qt6)
            qt6qml = os.path.join(dep.package_folder, "lib", "cmake", "Qt6Qml", "Qt6QmlConfig.cmake")
            if os.path.isfile(qt6qml):
                tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = dep.package_folder
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                # Qt keeps plugins/ and qml/ at the prefix root, while the KF6
                # packages of this baseline install them below lib/.
                for sub in ("plugins", os.path.join("lib", "plugins")):
                    candidate = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(candidate):
                        env.prepend_path("QT_PLUGIN_PATH", candidate)
                for sub in ("qml", os.path.join("lib", "qml")):
                    candidate = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(candidate):
                        env.prepend_path("QML2_IMPORT_PATH", candidate)
        # The share plugins are loaded by plugin id at runtime, so the purpose
        # package's own plugin directory has to be reachable - its location
        # depends on KDE_INSTALL_PLUGINDIR (<libdir>/plugins/kf6/purpose).
        purpose = self.dependencies["purpose"]
        plugin_roots = glob.glob(
            os.path.join(purpose.package_folder, "**", "kf6", "purpose"), recursive=True
        )
        for plugin_dir in plugin_roots:
            env.prepend_path("QT_PLUGIN_PATH", os.path.dirname(os.path.dirname(plugin_dir)))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(purpose.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        # Run the share job in-process: the purposeprocess helper would need a
        # working process/DBus environment, which the OHOS test sandbox has not.
        env.define("KDE_PURPOSE_LOCAL_JOBS", "1")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                ),
                env="conanrun",
            )

    def _prepare_runtime_links(self):
        runtime_dirs = {self.cpp.build.bindirs[0], self.build_folder}
        lib_sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        for src in lib_sources:
            for runtime_dir in runtime_dirs:
                os.makedirs(runtime_dir, exist_ok=True)
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)
