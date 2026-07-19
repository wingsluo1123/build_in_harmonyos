from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get


class LibdjinteropConan(ConanFile):
    name = "libdjinterop"
    version = "0.24.3"
    description = "C++ library for accessing DJ database formats (Engine Prime, Rekordbox, Serato)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/xsco/libdjinterop"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def configure(self):
        self.options.shared = False

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("sqlite3", "cmake_file_name", "SQLite3")
        deps.set_property("sqlite3", "cmake_target_name", "SQLite::SQLite3")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["SYSTEM_SQLITE"] = True
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_DOC"] = False
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
        self.cpp_info.libs = ["djinterop"]
        self.cpp_info.set_property("cmake_file_name", "DjInterop")
        self.cpp_info.set_property("cmake_target_name", "DjInterop::DjInterop")
        self.cpp_info.requires = ["zlib::zlib", "sqlite3::sqlite3"]

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("sqlite3/3.49.1")
