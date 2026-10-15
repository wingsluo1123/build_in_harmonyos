import os
import shlex
import sys
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv

class LibuninumTest(ConanFile):
    settings = 'os', 'arch', 'compiler', 'build_type'
    test_type = 'explicit'
    exports_sources = 'CMakeLists.txt', 'test.c', 'test_cli.sh', 'harmony_consumer.py'

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        library = Path(dep.package_folder,'lib')
        cli = Path(dep.package_folder,'bin','numconv')
        if not library.is_dir() or not cli.is_file():
            raise ConanException('package artifacts missing')
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindirs[0], 'test_package')
            self.run(shlex.quote(exe), env='conanrun')
            self.run('sh ' + shlex.quote(os.path.join(self.source_folder,'test_cli.sh')) +
                     ' ' + shlex.quote(str(cli)), env='conanrun')
            if self.settings.os == 'OHOS':
                self.run(' '.join(map(shlex.quote, [sys.executable,
                    os.path.join(self.source_folder, 'harmony_consumer.py'),
                    str(cli), self.build_folder])), env='conanrun')
