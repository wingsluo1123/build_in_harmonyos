#!/usr/bin/env python3
"""Conan test_package for analitza 26.04.0.

Consumer-side verification (R34: real API usage, no stubs):

  * test_analitza drives the exported KF6::Analitza* targets end to end:
    the expression parser + Analyzer evaluation, the PlotsFactory 2D/3D
    pipeline (PlaneCurve sampling, Surface marching-cubes geometry), the
    Plotter3DES X3D exporter, the AnalitzaGui VariablesModel and the
    AnalitzaWidgets PlotsView2D/ExpressionEdit views.
  * test_ohos_soname parses the ELF dynamic section of the consumer and of
    the loaded libAnalitzaPlot.so: bare DT_SONAME, basename-only DT_NEEDED
    (E537) and a versioned-soname-free layout (E330: upstream
    VERSION/SOVERSION is emitted as a single unversioned .so because the
    HMDFS user volume rejects the symlink chain).

The package installs its own Analitza6Config.cmake (cmake_find_mode=none),
so the test recipe prepends every dependency prefix to CMAKE_PREFIX_PATH
instead of relying on CMakeDeps. test() really executes both binaries
through self.run() (L0d / R34).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class AnalitzaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Analitza6Config.cmake's find_dependency(Qt6Core/Qt6Xml); the
        # imported KF6::AnalitzaWidgets target also carries Qt::Widgets.
        self.requires("qtbase/6.11.1")
        # libAnalitzaWidgets.so links Qt6::Svg PRIVATE, so the runtime
        # loader needs qtsvg's lib directory as well.
        self.requires("qtsvg/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Same Linux platform force as the main recipe: the OHOS toolchain
        # maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS (no UNIX platform
        # module, treated as cross compiling).
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
            # Same 4K max-page-size pin as the main recipe: the OHOS loader
            # rejects the default lld 0x10000 segment layout.
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
        # The consumer resolves its dependencies through LD_LIBRARY_PATH at
        # run time; a baked build RPATH would point into the conan cache.
        tc.cache_variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.generate()

        # Every package here publishes cmake_find_mode=none (qtbase/qtsvg/
        # analitza), so CMakeDeps output is not what we consume: write the
        # explicit search paths instead (ki18n/kcolorscheme precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefix = dep.package_folder.replace("\\", "/")
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(prefix)
                )
                lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(prefix))
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(prefix)
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(prefix)
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK's llvm/lib directory; prepend it so CMake's TryCompile can
        # link. Do not clobber the conanbuild env on other hosts.
        env = Environment()
        for sdk_llvm_lib in sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
            )
        ):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _library_paths(self):
        paths = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                paths.append(os.path.join(dep.package_folder, "lib"))
                paths.append(os.path.join(dep.package_folder, "bin"))
        if os.path.isdir("/system/lib64"):
            paths.append("/system/lib64")
        return paths

    def test(self):
        # The consumer binaries run only when the target can execute on this
        # machine and tests were not opted out (standard Conan cross-build
        # contract; the OHPC profile builds natively on the device).
        if not can_run(self) or self.conf.get("tools.build:skip_test", default=False):
            return
        env = Environment()
        for path in self._library_paths():
            env.prepend_path("LD_LIBRARY_PATH", path)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
        # The consumer runs a QApplication (PlotsView2D/ExpressionEdit), so
        # the offscreen QPA plugin from the qtbase package is required.
        env.define("QT_QPA_PLATFORM", "offscreen")
        # Hermetic XDG roots: Qt and the models must not read or write the
        # worker's home directory.
        home = os.path.join(self.build_folder, "ohos-xdg")
        for sub in ("config", "data", "runtime", "cache"):
            os.makedirs(os.path.join(home, sub), exist_ok=True)
        env.define("HOME", home)
        env.define("XDG_CONFIG_HOME", os.path.join(home, "config"))
        env.define("XDG_DATA_HOME", os.path.join(home, "data"))
        env.define("XDG_RUNTIME_DIR", os.path.join(home, "runtime"))
        env.define("XDG_CACHE_HOME", os.path.join(home, "cache"))
        with env.vars(self).apply():
            executables = ["test_analitza"]
            # E330/E537 describe the OHOS loader and the HMDFS no-symlink
            # layout; a native Linux build keeps upstream's versioned SONAME
            # chain, so only the API test applies there.
            if str(self.settings.os) in ("OHOS", "HarmonyOS"):
                executables.append("test_ohos_soname")
            for executable in executables:
                self.run(
                    os.path.join(self.cpp.build.bindirs[0], executable),
                    env="conanrun",
                )
