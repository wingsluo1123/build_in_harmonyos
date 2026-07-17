from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class QtHttpServerConan(ConanFile):
    name = "qthttpserver"
    version = "6.11.1"
    description = "Qt framework for embedding an HTTP server"
    license = "GPL-3.0-only AND BSD-3-Clause"
    homepage = "https://www.qt.io/"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables.update(
            {
                "QT_BUILD_TESTS": False,
                "QT_BUILD_EXAMPLES": False,
                "QT_BUILD_BENCHMARKS": False,
                "QT_BUILD_DOCS": False,
                "BUILD_SHARED_LIBS": True,
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
        self.cpp_info.libs = ["Qt6HttpServer"]
        self.cpp_info.set_property("cmake_file_name", "qthttpserver")
        self.cpp_info.set_property("cmake_target_name", "Qt6::HttpServer")
