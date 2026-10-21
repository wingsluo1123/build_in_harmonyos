#!/usr/bin/env python3
"""Conan test_package for kcrash 6.28.0.

Consumer-level verification of the published package:
  - KF6::Crash resolves through the installed KF6CrashConfig.cmake (the
    shared build only find_dependency(Qt6Core));
  - the DrKonqi toggle surface reports the OHOS fallback (no drkonqi
    executable exists, so enabling falls back to disabled);
  - setEmergencySaveFunction installs the default crash handler and both
    getters report it;
  - E2E: a child consumer process crashes with SIGSEGV and the emergency
    save function installed through the public API runs inside the crash
    handler, its output durable in the log file;
  - E2E: a child consumer process is restarted by KCrash (AutoRestart |
    AlwaysDirectly) and the second instance runs to normal completion.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KcrashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        # libKF6Crash.so links KF6::CoreAddons and Qt6::Gui privately, so
        # both must be resolvable at runtime and in CMake.
        self.requires("kcoreaddons/6.26.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")'
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _sdk_llvm_libdir(self):
        # The OHOS SDK root is environment specific, so prefer the llvm/lib
        # directory implied by the profile's compiler and fall back to globbing
        # the installed SDK. The version stays unpinned: a CI image ships
        # whatever SDK release it was built with.
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx:
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            )
        )
        for candidate in dict.fromkeys(candidates):
            if os.path.isdir(candidate):
                return candidate
        return ""

    def _build_env(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory and may not find it via the ambient
        # LD_LIBRARY_PATH. The dependency lib dirs are needed by the runtime
        # of any helper executed during the build.
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        with self._build_env().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefix = dep.package_folder
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "bin"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(prefix, "lib", "plugins"))
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")

        # The OHOS sandbox is not writable for the test user, so isolate
        # HOME/XDG under the build folder (the crash-handling E2E writes its
        # log files and the Qt runtime wants XDG_RUNTIME_DIR to exist).
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(test_home, "runtime")
        for directory in (test_home, xdg_runtime):
            os.makedirs(directory, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, "cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, "config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, "data"))

        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_kcrash"), env="conanrun")
