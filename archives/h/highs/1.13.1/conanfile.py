from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, get, save, load
import os

class HiGHSConan(ConanFile):
    name = "highs"
    version = "1.13.1"
    license = "MIT"
    author = "ERGO-Code"
    url = "https://github.com/ERGO-Code/HiGHS"
    description = "Linear optimization library"
    topics = ("optimization", "solver", "linear-programming")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = "CMakeToolchain"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 直接修改 CMakeLists.txt，用字符串替换
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        if os.path.exists(cmake_file):
            content = load(self, cmake_file)
            # 用简单字符串替换
            content = content.replace('if(EXISTS "${LOC_PATH}")', 'if(FALSE)')
            save(self, cmake_file, content)
        
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        include_dir = os.path.join(self.source_folder, "src")
        if os.path.exists(include_dir):
            copy(self, "*.h", src=include_dir, dst=os.path.join(self.package_folder, "include"))
            copy(self, "*.hpp", src=include_dir, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["highs"]