from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run

class CmatrixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.test()
        else:
            # 交叉编译：只验证编译链接，确认二进制存在
            self.output.info("Cross-compiling: skipping runtime test, build verified OK")
            pkg = self.dependencies["cmatrix"]
            self.run(f"test -x {pkg.cpp_info.bindirs[0]}/cmatrix")