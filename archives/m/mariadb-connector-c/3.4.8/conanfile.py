from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, collect_libs, export_conandata_patches, get


class MariadbConnectorCConan(ConanFile):
    name = "mariadb-connector-c"
    version = "3.4.8"
    description = "MariaDB Connector/C is a C client library for MariaDB"
    license = "LGPL-2.1"
    homepage = "https://github.com/mariadb-corporation/mariadb-connector-c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_SSL"] = "OPENSSL"
        tc.variables["WITH_EXTERNAL_ZLIB"] = "OFF"
        tc.variables["WITH_UNIT_TESTS"] = "OFF"
        tc.variables["CMAKE_C_FLAGS"] = "-fPIC -O2"
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
        self.cpp_info.includedirs = ["include/mariadb"]
        self.cpp_info.libdirs = ["lib/mariadb"]
        self.cpp_info.libs = ["mariadb"]
        self.cpp_info.set_property("cmake_file_name", "mariadb-connector-c")
        self.cpp_info.set_property("cmake_target_name", "mariadb-connector-c::mariadb-connector-c")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
