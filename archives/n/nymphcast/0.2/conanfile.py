from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class NymphcastConan(ConanFile):
    name = "nymphcast"
    version = "0.2"
    description = "Audio/video casting and streaming receiver application"
    license = "BSD-3-Clause"
    homepage = "https://github.com/MayaPosch/NymphCast"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)
        # NymphCast extracts CMakeLists.txt next to conanfile.py (strip_root=True).
        # Pin the source folder to the recipe directory so cmake.configure() never
        # mistakes the build folder ("b") for the source dir on this toolchain.
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # Point CMake explicitly at the recipe folder (absolute) so the source
        # dir is never resolved to the build folder.
        cmake.configure(build_script_folder=self.recipe_folder)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
# OHOS-CI-trigger: re-run build (no functional change)
