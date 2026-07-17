from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class LibdiscidConan(ConanFile):
    name = "libdiscid"
    version = "0.6.5"
    description = "MusicBrainz compact disc identification library"
    license = "LGPL-2.1-or-later"
    homepage = "https://musicbrainz.org/doc/libdiscid"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["discid"]
        self.cpp_info.set_property("cmake_file_name", "libdiscid")
        self.cpp_info.set_property("cmake_target_name", "libdiscid::libdiscid")
        self.cpp_info.set_property("pkg_config_name", "libdiscid")
