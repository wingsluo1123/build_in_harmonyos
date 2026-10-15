import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KAccountsIntegrationTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        pkg_lib = os.path.join(
            self.dependencies["kaccounts-integration"].package_folder, "lib"
        )
        # The exported target is the bare "KAccounts6" (install(EXPORT) has no
        # NAMESPACE, EXPORT_NAME=KAccounts6).
        deps.set_property("kaccounts-integration", "cmake_file_name", "KAccounts6")
        # Map qtbase onto the real Qt6 config (see recipe generate()); the
        # global-target refs (qtbase::qtbase / qtbase-sql-dbus::...) are mapped
        # onto existing real targets.
        deps.set_property("qtbase", "cmake_file_name", "Qt6")
        deps.set_property("qtbase", "cmake_target_name", "Qt6::Core")
        deps.set_property("qtbase-sql-dbus", "cmake_file_name", "Qt6")
        deps.set_property("qtbase-sql-dbus", "cmake_target_name", "Qt6::DBus")
        deps.generate()
        tc = CMakeToolchain(self)
        qt_prefix = self.dependencies["qtbase"].package_folder.replace("\\", "/")
        tc.cache_variables["Qt6_DIR"] = f"{qt_prefix}/lib/cmake/Qt6"
        tc.cache_variables["CMAKE_PREFIX_PATH"] = f"{qt_prefix}/lib/cmake;{qt_prefix}"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindir, "test_kaccounts_integration")
        pkg_lib = os.path.join(
            self.dependencies["kaccounts-integration"].package_folder, "lib"
        )
        # conanrun.sh resets LD_LIBRARY_PATH to dependency lib dirs only and
        # drops the tested package's own lib dir; re-prepend it in the shell.
        self.run(
            f'LD_LIBRARY_PATH="{pkg_lib}:$LD_LIBRARY_PATH" {cmd}', env="conanrun"
        )
