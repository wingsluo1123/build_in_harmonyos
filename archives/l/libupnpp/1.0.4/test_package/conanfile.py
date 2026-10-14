import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibupnppTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # CMake has no HarmonyOS platform module, so the default consumer
            # link command omits RPATH even though it links shared dependencies.
            for language in ("C", "CXX"):
                toolchain.variables["CMAKE_SHARED_LIBRARY_RUNTIME_" + language + "_FLAG"] = "-Wl,-rpath,"
                toolchain.variables["CMAKE_SHARED_LIBRARY_RUNTIME_" + language + "_FLAG_SEP"] = ":"
                toolchain.variables["CMAKE_SHARED_LIBRARY_RPATH_LINK_" + language + "_FLAG"] = "-Wl,-rpath-link,"
            runtime = []
            for requirement, dependency in self.dependencies.items():
                if requirement.build or requirement.test or not dependency.package_folder:
                    continue
                for directory in dependency.cpp_info.libdirs:
                    path = os.path.abspath(os.path.join(dependency.package_folder, directory))
                    if os.path.isdir(path) and path not in runtime:
                        runtime.append(path)
            toolchain.variables["CMAKE_BUILD_RPATH"] = ";".join(runtime)
            # Native consumer-only RPATH; never exported into the library.
            toolchain.extra_exelinkflags.extend(["-Wl,--disable-new-dtags", "-Wl,-rpath," + ":".join(runtime)])
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindirs[0], "consumer")
            self.run('"{}"'.format(executable), env="conanrun")
