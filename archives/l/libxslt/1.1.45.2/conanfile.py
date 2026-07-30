#!/usr/bin/env python3
"""Conan recipe — libxslt 1.1.45.2 standardized for HarmonyOS PC."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibxsltConan(ConanFile):
    name = "libxslt"
    version = "1.1.45.2"
    description = "libxslt with xsltproc enabled for build-time XSLT transforms"
    license = "MIT"
    homepage = "https://gitlab.gnome.org/GNOME/libxslt"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["LIBXSLT_WITH_PROGRAMS"] = "ON"
        tc.variables["LIBXSLT_WITH_CRYPTO"] = "OFF"
        tc.variables["LIBXSLT_WITH_PYTHON"] = "OFF"
        tc.variables["LIBXSLT_WITH_TESTS"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["exslt", "xslt"]
        self.cpp_info.requires = ["libxml2::libxml2"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "LibXslt")
        self.cpp_info.set_property("cmake_target_name", "LibXslt::LibXslt")
        self.cpp_info.set_property("pkg_config_name", "libxslt")
        bin_dir = self.package_folder + "/bin"
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
