from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class PhysfsConan(ConanFile):
    name = "physfs"
    version = "3.2.0"
    description = "Portable virtual filesystem library for archives"
    license = "Zlib"
    homepage = "https://icculus.org/physfs/"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables.update(
            {
                "PHYSFS_BUILD_STATIC": True,
                "PHYSFS_BUILD_SHARED": False,
                "PHYSFS_BUILD_TEST": False,
                "PHYSFS_BUILD_DOCS": False,
                "PHYSFS_DISABLE_INSTALL": False,
                "CMAKE_POSITION_INDEPENDENT_CODE": True,
                "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            }
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["physfs"]
        self.cpp_info.set_property("cmake_file_name", "PhysFS")
        self.cpp_info.set_property("cmake_target_name", "PhysFS::PhysFS")
        self.cpp_info.set_property("pkg_config_name", "physfs")
