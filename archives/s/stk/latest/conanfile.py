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
        # Only the Conan toolchain/presets here. All STK CMake *options* are
        # passed on the cmake command line in build() because tc.variables
        # (toolchain file) is NOT honoured by a direct `cmake` invocation,
        # which is how Conan drives configure().
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        shared = bool(self.options.shared)
        # Every STK option MUST be on the command line (-D):
        #  - CMAKE_POLICY_VERSION_MINIMUM=3.5: CMake >= 4.0 removed
        #    compatibility with cmake_minimum_required(<3.5); STK declares 3.1.
        #  - REALTIME=OFF: REQUIRED on OHOS. STK's realtime block ends with
        #    FATAL_ERROR "Unknown system type for realtime support." for any
        #    system that is not Linux/Darwin/Windows.
        #  - COMPILE_PROJECTS=OFF: skip the example/demo executables.
        #  - BUILD_SHARED/STATIC: match the Conan shared option.
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "BUILD_SHARED": "ON" if shared else "OFF",
            "BUILD_STATIC": "OFF" if shared else "ON",
            "REALTIME": "OFF",
            "COMPILE_PROJECTS": "OFF",
            "ENABLE_ALSA": "OFF",
            "ENABLE_JACK": "OFF",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["stk"]
        self.cpp_info.includedirs = ["include/stk"]
