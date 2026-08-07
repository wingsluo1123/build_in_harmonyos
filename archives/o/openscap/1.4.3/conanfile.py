from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
import os


class OpenscapConan(ConanFile):
    name = "openscap"
    version = "1.4.3"
    description = "OpenSCAP - Security Compliance Library and Tools"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.open-scap.org"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pcre2/10.45.1")
        self.requires("libxslt/1.1.45.1")
        self.requires("xmlsec1/1.3.11")
        self.requires("bzip2/1.0.8")
        self.requires("libcurl/8.5.0")
        self.requires("libgcrypt/1.12.2")
        self.requires("libgpg-error/1.55")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_PROBES_LINUX"] = "ON"
        tc.variables["ENABLE_PROBES_UNIX"] = "ON"
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_OSCAP_UTIL_DOCKER"] = "OFF"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openscap"]
        self.cpp_info.set_property("cmake_file_name", "openscap")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
