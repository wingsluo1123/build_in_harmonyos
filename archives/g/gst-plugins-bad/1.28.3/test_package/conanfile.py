from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import Environment
import os


class TestGstPluginsBad(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        # Set LD_LIBRARY_PATH for shared libraries at runtime
        env = Environment()
        for dep in self.dependencies.values():
            lib_path = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_path):
                env.prepend_path("LD_LIBRARY_PATH", lib_path)
        env.vars(self, scope="run").save_script("conan_run_ld")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gst_plugins_bad")
        if can_run(self):
            # Set GST_PLUGIN_PATH so gstreamer can find plugins
            for dep in self.dependencies.values():
                plugin_path = os.path.join(dep.package_folder, "lib", "gstreamer-1.0")
                if os.path.isdir(plugin_path):
                    current = os.environ.get("GST_PLUGIN_PATH", "")
                    os.environ["GST_PLUGIN_PATH"] = plugin_path + (":" + current if current else "")
            self.run(f'"{bin_path}"', env="conanrun")
