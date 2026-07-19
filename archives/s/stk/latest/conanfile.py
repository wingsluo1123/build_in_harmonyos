from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class StkConan(ConanFile):
    name = "stk"
    version = "latest"
    description = "The Synthesis ToolKit in C++ - audio synthesis library"
    license = "MIT"
    homepage = "https://github.com/thestk/stk"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        shared = bool(self.options.shared)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED"] = shared
        tc.variables["BUILD_STATIC"] = not shared
        tc.variables["REALTIME"] = False
        tc.variables["COMPILE_PROJECTS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["stk"]
        self.cpp_info.includedirs = ["include/stk"]
