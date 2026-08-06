import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain

class GstPluginsGoodTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("gstreamer/1.28.3")
        self.requires("glib2/2.88.0")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Set GST_PLUGIN_PATH to find the plugins
        plugin_path = self.dependencies["gst-plugins-good"].package_folder
        plugin_path = os.path.join(plugin_path, "lib", "gstreamer-1.0")
        os.environ["GST_PLUGIN_PATH"] = plugin_path
        # Also need gst-plugins-base plugins
        base_path = self.dependencies["gst-plugins-base"].package_folder
        base_plugin_path = os.path.join(base_path, "lib", "gstreamer-1.0")
        os.environ["GST_PLUGIN_PATH"] = plugin_path + ":" + base_plugin_path

        cmake = CMake(self)
        cmake.test()
