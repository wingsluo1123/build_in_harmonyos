import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class OpenNurbsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        exe = os.path.join(self.cpp.build.bindirs[0], "opennurbs_consumer")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration(
                "consumer executable missing: %s" % exe
            )
        # 链接的是 SHARED 的 libOpenNURBS.so；这些 ELF 没有 RUNPATH，
        # 运行期只能靠 LD_LIBRARY_PATH（实测教训：conan 的 Environment().apply()
        # 在本平台不会传到 self.run 的子进程，故直接内联进命令）。
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    lib_dirs.append(lib_dir)
        if os.path.isdir(os.path.join(pkg, "lib")):
            lib_dirs.append(os.path.join(pkg, "lib"))
        self.run('LD_LIBRARY_PATH="%s" "%s"' % (os.pathsep.join(lib_dirs), exe))
