#!/usr/bin/env python3
"""Conan test_package for krunner5 5.116.0 (L1 official test).

Consumer-side verification (R34): the C++ test links KF5::Runner and drives
the real public API — an AbstractRunner subclass constructed from a
KPluginMetaData, match()/RunnerContext::addMatch()/matches() end to end,
QueryMatch value semantics (isValid, copy, ordering by relevance), the
RunnerSyntax pair and RunnerContext::matchesChanged — asserting observable
behaviour, not just that the library links.

HarmonyOS-specific assertions (R53): test.cpp additionally asserts that
  * the loaded libKF5Runner.so carries the OHOS-required unversioned
    DT_SONAME and a DT_RUNPATH (E537: the installed ELF is linked with its
    final install RPATH and is never rewritten post-link, so OHOS keeps
    mmap'ing it PROT_EXEC);
  * the packaged ELF is re-signed with binary-sign-tool after install (the
    .codesign section is present on the packaged file).

test() really executes the built binary through self.run() (L0d / R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KRunner5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The KF5::Runner exported target's interface references KF5::I18n
        # and the KF5RunnerConfig find_dependency's KF5CoreAddons/KF5Config
        # (upstream's own KF5RunnerConfig does not pull KF5I18n, so the
        # consumer supplies it explicitly).  Explicit requirements keep the
        # consumer graph readable; .2 + force matches the main recipe
        # (kcoreaddons5 still pins qt5-qtbase/5.15.2).
        self.requires("qt5-qtbase/5.15.2.2", force=True)
        self.requires("kconfig5/5.116.0")
        self.requires("kcoreaddons5/5.116.0.1")
        self.requires("ki18n5/5.116.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        # The CMakeDeps-generated aggregate Qt5Config (file_name Qt5) is the
        # config the consumer's find_package(Qt5 ... COMPONENTS Core) and the
        # KF5RunnerConfig's find_dependency(Qt5 CONFIG REQUIRED Core Gui)
        # resolve against.  qt5-qtdeclarative ships no cmake config, so its
        # generated config is named Qt5Qml (needed by KF5I18n's own config
        # dependency chain), like in the main recipe.
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.set_property("qt5-qtdeclarative", "cmake_file_name", "Qt5Qml")
        deps.generate()

        tc = CMakeToolchain(self)
        # Same Linux platform force as the main recipe: the OHOS toolchain
        # maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS (no UNIX, flagged as a
        # cross build).
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if str(self.settings.arch) == "armv8":
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            else:
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # The test binary resolves its KF5/Qt5 dependencies through the
        # LD_LIBRARY_PATH wired in build()/test() below.
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qt5 = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(pkg.package_folder)
            )
        if qt5:
            qt_pkg = qt5.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
        # The KF5 packages publish cmake_find_mode=none (native KF5*Config
        # only), so wire their prefixes explicitly.
        for dep_name in ("kconfig5", "kcoreaddons5", "ki18n5"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(dep.package_folder))
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(dep.package_folder)
                )
        # The generators folder holds the CMakeDeps-generated configs.
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        qt5 = self.dependencies.get("qt5-qtbase")
        if qt5 and qt5.package_folder:
            env.prepend_path("PATH", os.path.join(qt5.package_folder, "bin"))
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            return
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_krunner5"),
                env="conanrun",
            )
