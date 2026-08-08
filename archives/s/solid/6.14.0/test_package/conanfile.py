import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

class SolidTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase uses cmake_find_mode=none, so CMakeDeps doesn't add its
        # cmake directory to CMAKE_PREFIX_PATH. Create the file manually
        # so the test_package can find Qt6Config.cmake and KF6SolidConfig.cmake.
        lines = []
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        # Add the tested package's cmake directory (solid uses cmake_find_mode=none)
        solid = self.dependencies.get("solid")
        if solid:
            sd_pkg = solid.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{sd_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{sd_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{sd_pkg}/include")')
        lines.append(f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")')
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_solid"), env="conanrun")
